import os
import asyncio
import numpy as np
from typing import Callable, Awaitable
from huggingface_hub import login as hf_login
import nnsight
from nnsight import LanguageModel

_model: LanguageModel | None = None


def get_model() -> LanguageModel:
    global _model
    if _model is None:
        hf_login(token=os.environ["HF_TOKEN"], add_to_git_credential=False)
        nnsight.CONFIG.set_default_api_key(os.environ["NDIF_API_KEY"])
        _model = LanguageModel("meta-llama/Meta-Llama-3.1-8B")
    return _model


async def extract_activations(
    prompts: list[str],
    layer: int,
    on_progress: Callable[[int, int], Awaitable[None]],
) -> np.ndarray:
    model = get_model()
    all_acts: list[np.ndarray] = []

    for i, prompt in enumerate(prompts):
        for attempt in range(3):
            try:
                with model.trace(prompt, remote=True):
                    hidden = model.model.layers[layer].output[:, -1, :].save()
                act = hidden.squeeze(0).cpu().float().numpy()
                all_acts.append(act)
                break
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"Prompt {i} failed after 3 attempts: {e}") from e
                await asyncio.sleep(5)

        await on_progress(i + 1, len(prompts))
        await asyncio.sleep(0.25)

    return np.stack(all_acts)
