import asyncio
import os
from functools import partial
from typing import Literal

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.config import settings

_tokenizer = None
_model = None


def load_model() -> None:
    global _tokenizer, _model
    os.environ["HF_HOME"] = settings.hf_home
    dtype = torch.float16 if settings.torch_dtype == "float16" else torch.float32

    print(
        f"[ml_engine] Loading {settings.hf_model_id} → device={settings.device} dtype={dtype}"
    )
    _tokenizer = AutoTokenizer.from_pretrained(settings.hf_model_id)
    _model = AutoModelForCausalLM.from_pretrained(
        settings.hf_model_id,
        torch_dtype=dtype,
    ).to(settings.device)
    _model.eval()
    print("[ml_engine] Model ready ✓")


def _infer_sync(html: str, output_format: Literal["markdown", "json"]) -> str:
    """Blocking — always execute in run_in_executor."""
    if output_format == "json":
        prompt = (
            "Extract the main content of the following HTML and return a JSON object "
            "with keys: title, description, content (markdown string).\n\n" + html
        )
    else:
        prompt = html  # HTML→Markdown: no instruction, just the HTML

    messages = [{"role": "user", "content": prompt}]
    input_text = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _tokenizer.encode(input_text, return_tensors="pt").to(settings.device)

    with torch.no_grad():
        outputs = _model.generate(
            inputs,
            max_new_tokens=settings.max_new_tokens,
            temperature=0,
            do_sample=False,
            repetition_penalty=1.08,
        )

    new_tokens = outputs[0][inputs.shape[1] :]
    return _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


async def html_to_markdown(html: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_infer_sync, html, "markdown"))


async def html_to_json_str(html: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_infer_sync, html, "json"))
