from __future__ import annotations

import os
import asyncio
import numpy as np
from typing import Callable, Awaitable
from huggingface_hub import login as hf_login
import nnsight
from nnsight import LanguageModel

NDIF_TIMEOUT = 90  # seconds per prompt before giving up
PRIMARY_MODEL = "meta-llama/Meta-Llama-3.1-8B"
FALLBACK_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

_models: dict[str, LanguageModel] = {}
_ndif_initialized = False


def _init_ndif() -> None:
    global _ndif_initialized
    if not _ndif_initialized:
        hf_login(token=os.environ["HF_TOKEN"], add_to_git_credential=False)
        nnsight.CONFIG.set_default_api_key(os.environ["NDIF_API_KEY"])
        _ndif_initialized = True


def _get_model(name: str) -> LanguageModel:
    if name not in _models:
        _init_ndif()
        _models[name] = LanguageModel(name)
    return _models[name]


def _trace_sync(model: LanguageModel, prompt: str, layer: int) -> np.ndarray:
    with model.trace(prompt, remote=True):
        hidden = model.model.layers[layer].output[:, -1, :].save()
    return hidden.squeeze(0).cpu().float().numpy()


async def _trace_with_timeout(model: LanguageModel, prompt: str, layer: int) -> np.ndarray:
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(None, _trace_sync, model, prompt, layer),
        timeout=NDIF_TIMEOUT,
    )


async def _extract_single(prompt: str, layer: int) -> np.ndarray:
    last_err: Exception | None = None
    for model_name in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            model = _get_model(model_name)
            return await _trace_with_timeout(model, prompt, layer)
        except asyncio.TimeoutError:
            last_err = TimeoutError(
                f"{model_name} timed out after {NDIF_TIMEOUT}s (NDIF may be overloaded)"
            )
        except Exception as e:
            last_err = e

    raise RuntimeError(
        f"NDIF unavailable — both models failed. Last error: {last_err}"
    )


async def extract_activations(
    prompts: list[str],
    layer: int,
    on_progress: Callable[[int, int], Awaitable[None]],
) -> np.ndarray:
    all_acts: list[np.ndarray] = []

    for i, prompt in enumerate(prompts):
        act = await _extract_single(prompt, layer)
        all_acts.append(act)
        await on_progress(i + 1, len(prompts))

    return np.stack(all_acts)
