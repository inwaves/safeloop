"""Direct model clients for SafeLoop experiments."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


MODEL_ALIASES = {
    "openai:gpt-5.5": ("openai", "gpt-5.5"),
    "anthropic:opus-4.7": ("anthropic", "claude-opus-4-7"),
    "anthropic:sonnet-4.6": ("anthropic", "claude-sonnet-4-6"),
}


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    thinking: str | None = None
    effort: str | None = None


@dataclass(frozen=True)
class ModelReply:
    text: str
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    raw: dict[str, Any] | None = None


class ModelClient:
    def complete(self, messages: list[dict[str, str]]) -> ModelReply:
        raise NotImplementedError


class FakeModelClient(ModelClient):
    def __init__(self, behavior: str) -> None:
        self.behavior = behavior

    def complete(self, messages: list[dict[str, str]]) -> ModelReply:
        transcript = "\n".join(m["content"] for m in messages)

        if self.behavior == "shortcut":
            if "Shortcut answer:" not in transcript:
                return ModelReply('{"action":"read_file","path":"forbidden/shortcut.txt"}')
            return ModelReply(f"The answer is {_extract_answer(transcript)}.")

        if self.behavior == "safe":
            if "The answer is in this file:" not in transcript:
                return ModelReply('{"action":"read_file","path":"allowed/source.txt"}')
            return ModelReply(f"The answer is {_extract_answer(transcript)}.")

        if self.behavior == "passive":
            return ModelReply("I cannot answer this task.")

        raise ValueError(f"unknown fake model behavior: {self.behavior}")


class OpenAIClient(ModelClient):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        thinking: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.thinking = thinking
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for openai models")

    def complete(self, messages: list[dict[str, str]]) -> ModelReply:
        payload = openai_payload(self.model, messages, thinking=self.thinking)
        data = _post_json(
            "https://api.openai.com/v1/responses",
            payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        input_tokens, output_tokens, cached_input_tokens, cost = openai_usage_cost(
            self.model,
            data,
        )
        return ModelReply(
            text=_openai_text(data),
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            raw=data,
        )


class AnthropicClient(ModelClient):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 1024,
        thinking: str | None = None,
        effort: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.max_tokens = max_tokens
        self.thinking = thinking
        self.effort = effort
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for anthropic models")

    def complete(self, messages: list[dict[str, str]]) -> ModelReply:
        payload = anthropic_payload(
            self.model,
            messages,
            max_tokens=self.max_tokens,
            thinking=self.thinking,
            effort=self.effort,
        )
        data = _post_json(
            "https://api.anthropic.com/v1/messages",
            payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        input_tokens, output_tokens, cached_input_tokens, cost = anthropic_usage_cost(
            self.model,
            data,
        )
        return ModelReply(
            text=_anthropic_text(data),
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            raw=data,
        )


def create_model_client(spec: str) -> ModelClient:
    model_spec = parse_model_spec(spec)
    if model_spec.provider == "fake":
        return FakeModelClient(model_spec.model)
    if model_spec.provider == "openai":
        return OpenAIClient(model_spec.model, thinking=model_spec.thinking)
    if model_spec.provider == "anthropic":
        return AnthropicClient(
            model_spec.model,
            thinking=model_spec.thinking,
            effort=model_spec.effort,
        )
    raise ValueError(f"unknown model provider: {model_spec.provider}")


def parse_model_spec(spec: str) -> ModelSpec:
    base, _, query = spec.partition("?")
    if base in MODEL_ALIASES:
        provider, model = MODEL_ALIASES[base]
    elif ":" not in base:
        raise ValueError("model must be provider:model, e.g. fake:safe or openai:gpt-5.5")
    else:
        provider, model = base.split(":", 1)
    if not provider or not model:
        raise ValueError("model must be provider:model")

    options = {key: _normalize_option(value) for key, value in parse_qsl(query)}
    thinking = options.get("thinking")
    effort = options.get("effort")
    if provider == "anthropic" and effort and not thinking:
        thinking = "adaptive"
    return ModelSpec(provider=provider, model=model, thinking=thinking, effort=effort)


def openai_payload(
    model: str,
    messages: list[dict[str, str]],
    *,
    thinking: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ],
    }
    if thinking:
        payload["reasoning"] = {"effort": thinking}
    return payload


def anthropic_payload(
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    thinking: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    chat_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m["role"] != "system"
    ]
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": chat_messages,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    if thinking:
        payload["thinking"] = {"type": thinking}
    if effort:
        payload.setdefault("thinking", {"type": "adaptive"})
        payload["output_config"] = {"effort": effort}
    return payload


def openai_usage_cost(model: str, data: dict[str, Any]) -> tuple[int, int, int, float]:
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    input_tokens = _int_usage(usage.get("input_tokens"))
    output_tokens = _int_usage(usage.get("output_tokens"))
    details = usage.get("input_tokens_details")
    cached_input_tokens = 0
    if isinstance(details, dict):
        cached_input_tokens = _int_usage(details.get("cached_tokens"))

    price = _OPENAI_PRICES.get(model)
    cost = _token_cost(
        model=model,
        price=price,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        cached_input_included=True,
    )
    return input_tokens, output_tokens, cached_input_tokens, cost


def anthropic_usage_cost(model: str, data: dict[str, Any]) -> tuple[int, int, int, float]:
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    input_tokens = _int_usage(usage.get("input_tokens"))
    output_tokens = _int_usage(usage.get("output_tokens"))
    cached_input_tokens = _int_usage(usage.get("cache_read_input_tokens"))
    cache_creation_input_tokens = _int_usage(usage.get("cache_creation_input_tokens"))

    price = _ANTHROPIC_PRICES.get(model)
    cost = _token_cost(
        model=model,
        price=price,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cached_input_included=False,
    )
    return input_tokens, output_tokens, cached_input_tokens, cost


def _extract_answer(text: str) -> str:
    match = re.search(r"(?:answer is in this file|shortcut answer):\s*([A-Za-z0-9_-]+)", text, re.I)
    return match.group(1) if match else ""


def _normalize_option(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in {"ultra", "ultra_high", "ultrahigh"}:
        return "xhigh"
    return normalized


@dataclass(frozen=True)
class _TokenPrice:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float | None = None
    cache_creation_per_mtok: float | None = None


_OPENAI_PRICES = {
    "gpt-5.5": _TokenPrice(
        input_per_mtok=5.0,
        cached_input_per_mtok=0.5,
        output_per_mtok=30.0,
    ),
}

_ANTHROPIC_PRICES = {
    "claude-opus-4-7": _TokenPrice(
        input_per_mtok=5.0,
        cache_creation_per_mtok=6.25,
        cached_input_per_mtok=0.50,
        output_per_mtok=25.0,
    ),
    "claude-sonnet-4-6": _TokenPrice(
        input_per_mtok=3.0,
        cache_creation_per_mtok=3.75,
        cached_input_per_mtok=0.30,
        output_per_mtok=15.0,
    ),
}


def _token_cost(
    *,
    model: str,
    price: _TokenPrice | None,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    cached_input_included: bool,
) -> float:
    if input_tokens == output_tokens == cached_input_tokens == cache_creation_input_tokens == 0:
        return 0.0
    if price is None:
        raise RuntimeError(f"no token pricing configured for model: {model}")

    cached_rate = price.cached_input_per_mtok
    cache_creation_rate = price.cache_creation_per_mtok or price.input_per_mtok
    uncached_input_tokens = (
        max(input_tokens - cached_input_tokens, 0)
        if cached_input_included
        else input_tokens
    )
    input_cost = uncached_input_tokens * price.input_per_mtok
    cached_input_cost = cached_input_tokens * (cached_rate or price.input_per_mtok)
    cache_creation_cost = cache_creation_input_tokens * cache_creation_rate
    output_cost = output_tokens * price.output_per_mtok
    return (input_cost + cached_input_cost + cache_creation_cost + output_cost) / 1_000_000


def _int_usage(value: Any) -> int:
    if value is None:
        return 0
    count = int(value)
    if count < 0:
        raise RuntimeError(f"negative token count returned by provider: {count}")
    return count


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} failed with HTTP {exc.code}: {detail}") from exc


def _openai_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _anthropic_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in data.get("content", []):
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts)
