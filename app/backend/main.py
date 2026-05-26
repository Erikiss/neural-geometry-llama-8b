from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from cache import delete_cached, find_cached, get_recent, save_to_cache
from extraction import extract_activations
from models import QueryRequest, QueryResult
from pipeline import run_pipeline
from prompt_gen import embed_query, generate_prompts

app = FastAPI(title="Neural Geometry API")

CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _progress(msg: str, pct: int) -> dict:
    return {"event": "progress", "data": json.dumps({"message": msg, "pct": pct})}


def _done(data: dict) -> dict:
    return {"event": "done", "data": json.dumps(data)}


def _error(msg: str) -> dict:
    return {"event": "error", "data": json.dumps({"message": msg})}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/recent")
def recent():
    return get_recent(10)


@app.delete("/api/cache")
def clear_cache(q: str | None = Query(default=None, description="Delete only entries whose query contains this substring. Omit to delete all.")):
    deleted = delete_cached(q)
    return {"deleted": deleted, "filter": q}


@app.post("/api/query")
async def query_stream(req: QueryRequest):
    if not (0 <= req.layer <= 31):
        raise HTTPException(400, "Layer must be between 0 and 31.")

    async def generate():
        try:
            # 1. Check cache
            yield _progress("Checking cache...", 5)
            embedding = await embed_query(req.concept)
            cached = find_cached(embedding, req.layer)
            if cached:
                yield _done(cached.model_dump())
                return

            # 2. Generate prompts
            yield _progress("Generating prompts with GPT-4o-mini...", 15)
            spec = await generate_prompts(req.concept)
            n = len(spec.prompts)
            yield _progress(f"Generated {n} prompts for {len(spec.values)} concept values.", 20)

            # 3. Extract activations
            acts_list: list = []

            async def on_progress(i: int, total: int):
                pct = 20 + int(55 * i / total)
                yield _progress(f"Extracting activations... ({i}/{total})", pct)

            # Collect SSE events from on_progress via a queue
            import asyncio
            progress_queue: asyncio.Queue = asyncio.Queue()

            async def queued_progress(i: int, total: int):
                pct = 20 + int(55 * i / total)
                await progress_queue.put(_progress(f"Extracting activations... ({i}/{total})", pct))

            async def run_extraction():
                from extraction import extract_activations as _extract
                result = await _extract(
                    [p.prompt for p in spec.prompts],
                    req.layer,
                    queued_progress,
                )
                await progress_queue.put(None)  # sentinel
                return result

            extraction_task = asyncio.create_task(run_extraction())

            while True:
                msg = await progress_queue.get()
                if msg is None:
                    break
                yield msg

            all_acts = await extraction_task

            # 4. Pipeline
            yield _progress("Running PCA + spline pipeline...", 80)
            figure, var = run_pipeline(spec, all_acts)

            # 5. Cache + return
            yield _progress("Saving to cache...", 95)
            result = QueryResult(
                cache_hit=False,
                concept_name=spec.concept_name,
                layer=req.layer,
                is_cyclic=spec.is_cyclic,
                values=spec.values,
                prompts=spec.prompts,
                figure=figure,
                pca_variance=var,
                n_prompts=len(spec.prompts),
            )
            save_to_cache(embedding, req.concept, req.layer, result)
            yield _done(result.model_dump())

        except Exception as e:
            yield _error(str(e))

    return EventSourceResponse(generate())
