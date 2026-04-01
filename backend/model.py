from __future__ import annotations

import json
import logging
import os
from collections import deque
from dataclasses import dataclass
from time import perf_counter

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

NOVA_MICRO_MODEL_ID = os.getenv("BEDROCK_NOVA_MICRO_MODEL_ID", "amazon.nova-micro-v1:0")
MISTRAL_MODEL_ID = os.getenv(
    "BEDROCK_MISTRAL_MODEL_ID",
    "mistral.ministral-3-8b-instruct",
)
CLAUDE_HAIKU_MODEL_ID = os.getenv(
    "BEDROCK_CLAUDE_HAIKU_MODEL_ID",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
)
NOVA_PRO_MODEL_ID = os.getenv("BEDROCK_NOVA_PRO_MODEL_ID", "amazon.nova-pro-v1:0")
CLAUDE_SONNET_MODEL_ID = os.getenv(
    "BEDROCK_CLAUDE_SONNET_MODEL_ID",
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
)
QWEN_MODEL_ID = os.getenv("BEDROCK_QWEN_MODEL_ID", "qwen.qwen3-next-80b-a3b")

CLAUDE_HAIKU_INFERENCE_PROFILE_ID = os.getenv(
    "BEDROCK_CLAUDE_HAIKU_INFERENCE_PROFILE_ID",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
)
CLAUDE_SONNET_INFERENCE_PROFILE_ID = os.getenv(
    "BEDROCK_CLAUDE_SONNET_INFERENCE_PROFILE_ID",
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
)

QWEN_CLASSIFIER_SYSTEM_PROMPT = """Return ONLY JSON:
{
  "task": "code|math|reasoning|factual|general",
  "complexity": "low|medium|high",
  "confidence": "low|high"
}
No explanation. No markdown. No extra text."""

SUPPORTED_TASKS = {"code", "math", "reasoning", "factual", "general"}
SUPPORTED_COMPLEXITIES = {"low", "medium", "high"}
SUPPORTED_CONFIDENCE = {"low", "high"}

MODEL_REQUEST_LOGS = deque(maxlen=int(os.getenv("BEDROCK_REQUEST_LOG_LIMIT", "250")))


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    display_name: str
    provider: str
    role: str
    input_price_per_million: float
    output_price_per_million: float
    default_max_tokens: int
    temperature: float = 0.2
    top_p: float = 0.9
    request_format: str = "bedrock_converse_messages"
    inference_profile_id: str | None = None


MODEL_PROFILES = {
    NOVA_MICRO_MODEL_ID: ModelProfile(
        model_id=NOVA_MICRO_MODEL_ID,
        display_name="Amazon Nova Micro",
        provider="amazon",
        role="cheap_factual",
        input_price_per_million=float(os.getenv("BEDROCK_PRICE_NOVA_MICRO_INPUT", "0.035")),
        output_price_per_million=float(os.getenv("BEDROCK_PRICE_NOVA_MICRO_OUTPUT", "0.14")),
        default_max_tokens=180,
    ),
    MISTRAL_MODEL_ID: ModelProfile(
        model_id=MISTRAL_MODEL_ID,
        display_name="Mistral",
        provider="mistral",
        role="cheap_general",
        input_price_per_million=float(os.getenv("BEDROCK_PRICE_MISTRAL_INPUT", "0.1")),
        output_price_per_million=float(os.getenv("BEDROCK_PRICE_MISTRAL_OUTPUT", "0.3")),
        default_max_tokens=220,
        temperature=0.25,
    ),
    CLAUDE_HAIKU_MODEL_ID: ModelProfile(
        model_id=CLAUDE_HAIKU_MODEL_ID,
        display_name="Claude Haiku 4.5",
        provider="anthropic",
        role="mid_reasoning",
        input_price_per_million=float(os.getenv("BEDROCK_PRICE_CLAUDE_HAIKU_INPUT", "1.0")),
        output_price_per_million=float(os.getenv("BEDROCK_PRICE_CLAUDE_HAIKU_OUTPUT", "5.0")),
        default_max_tokens=260,
        inference_profile_id=CLAUDE_HAIKU_INFERENCE_PROFILE_ID,
    ),
    NOVA_PRO_MODEL_ID: ModelProfile(
        model_id=NOVA_PRO_MODEL_ID,
        display_name="Amazon Nova Pro",
        provider="amazon",
        role="code",
        input_price_per_million=float(os.getenv("BEDROCK_PRICE_NOVA_PRO_INPUT", "0.8")),
        output_price_per_million=float(os.getenv("BEDROCK_PRICE_NOVA_PRO_OUTPUT", "3.2")),
        default_max_tokens=300,
    ),
    CLAUDE_SONNET_MODEL_ID: ModelProfile(
        model_id=CLAUDE_SONNET_MODEL_ID,
        display_name="Claude Sonnet 4.5",
        provider="anthropic",
        role="strong_reasoning",
        input_price_per_million=float(os.getenv("BEDROCK_PRICE_CLAUDE_SONNET_INPUT", "3.0")),
        output_price_per_million=float(os.getenv("BEDROCK_PRICE_CLAUDE_SONNET_OUTPUT", "15.0")),
        default_max_tokens=380,
        inference_profile_id=CLAUDE_SONNET_INFERENCE_PROFILE_ID,
    ),
    QWEN_MODEL_ID: ModelProfile(
        model_id=QWEN_MODEL_ID,
        display_name="Qwen3 Next 80B A3B",
        provider="qwen",
        role="classifier",
        input_price_per_million=float(os.getenv("BEDROCK_PRICE_QWEN_INPUT", "0.12")),
        output_price_per_million=float(os.getenv("BEDROCK_PRICE_QWEN_OUTPUT", "0.6")),
        default_max_tokens=30,
        temperature=0.0,
        top_p=0.1,
    ),
}

MODEL_ALIASES = {
    CLAUDE_HAIKU_INFERENCE_PROFILE_ID: CLAUDE_HAIKU_MODEL_ID,
    CLAUDE_SONNET_INFERENCE_PROFILE_ID: CLAUDE_SONNET_MODEL_ID,
}

DEFAULT_SYSTEM_PROMPT = (
    "You are a precise assistant helping power a production routing demo. "
    "Answer directly, stay grounded in the user's request, and avoid unnecessary filler."
)

REFINEMENT_INSTRUCTIONS = {
    "brief": "Keep the answer concise and high-signal.",
    "bullet": "Prefer a structured bullet-style answer with short, scannable points.",
    "detailed": "Provide a fuller explanation with enough detail to be useful.",
}


@dataclass
class BedrockInvocationError(Exception):
    message: str
    details: dict

    def __str__(self) -> str:
        return self.message


def _resolve_region() -> str:
    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or boto3.Session().region_name
        or "us-east-1"
    )


def _get_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=_resolve_region(),
        config=Config(
            connect_timeout=5,
            read_timeout=120,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _get_profile(model_id: str) -> ModelProfile:
    canonical_id = MODEL_ALIASES.get(model_id, model_id)
    profile = MODEL_PROFILES.get(canonical_id)
    if not profile:
        raise BedrockInvocationError(
            "Unsupported Bedrock model",
            {
                "model_id": model_id,
                "supported_models": sorted(MODEL_PROFILES),
            },
        )
    return profile


def _resolve_max_tokens(profile: ModelProfile, refinement: str, explicit_max_tokens: int | None) -> int:
    if explicit_max_tokens is not None:
        return explicit_max_tokens

    if refinement == "brief":
        return min(profile.default_max_tokens, 140)
    if refinement == "bullet":
        return min(profile.default_max_tokens + 20, 260)
    if refinement == "detailed":
        return min(profile.default_max_tokens + 120, 420)
    return profile.default_max_tokens


def _compose_system_prompt(system_prompt: str | None, refinement: str, include_refinement: bool) -> str | None:
    prompt_parts = [system_prompt.strip() if system_prompt else DEFAULT_SYSTEM_PROMPT]
    if include_refinement:
        prompt_parts.append(REFINEMENT_INSTRUCTIONS.get(refinement, REFINEMENT_INSTRUCTIONS["brief"]))
    joined = " ".join(part for part in prompt_parts if part)
    return joined or None


def _build_converse_request(
    prompt: str,
    profile: ModelProfile,
    *,
    system_prompt: str | None = None,
    refinement: str = "brief",
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    include_refinement: bool = True,
) -> dict:
    composed_system_prompt = _compose_system_prompt(system_prompt, refinement, include_refinement)
    request = {
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        "inferenceConfig": {
            "maxTokens": _resolve_max_tokens(profile, refinement, max_tokens),
            "temperature": profile.temperature if temperature is None else temperature,
            "topP": profile.top_p if top_p is None else top_p,
        },
    }
    if composed_system_prompt:
        request["system"] = [{"text": composed_system_prompt}]
    return request


def _extract_text_from_content(content: list[dict]) -> str:
    parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("text")]
    return "\n".join(parts).strip()


def _normalize_model_id(model_id: str) -> str:
    return MODEL_ALIASES.get(model_id, model_id)


def estimate_cost(model_id: str, input_tokens: int | None, output_tokens: int | None) -> float:
    profile = _get_profile(model_id)
    input_count = input_tokens or 0
    output_count = output_tokens or 0
    return (
        (input_count / 1_000_000.0) * profile.input_price_per_million
        + (output_count / 1_000_000.0) * profile.output_price_per_million
    )


def _record_request_metric(metric: dict) -> None:
    MODEL_REQUEST_LOGS.append(metric)
    logger.info(
        "Bedrock call model=%s invoked=%s latency_ms=%s estimated_cost=%.8f baseline_cost=%.8f savings_pct=%.2f request_id=%s",
        metric.get("model_id"),
        metric.get("invoked_model_id"),
        metric.get("latency_ms"),
        metric.get("estimated_cost", 0.0),
        metric.get("baseline_cost", 0.0),
        metric.get("savings_pct", 0.0),
        metric.get("request_id"),
    )


def _should_retry_with_profile(exc: ClientError, profile: ModelProfile, model_id: str) -> bool:
    if not profile.inference_profile_id:
        return False
    if model_id == profile.inference_profile_id:
        return False
    error = exc.response.get("Error", {})
    message = error.get("Message", "").lower()
    return error.get("Code") == "ValidationException" and (
        "inference profile" in message or "on-demand throughput" in message
    )


def _converse(
    model_id: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    refinement: str = "brief",
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    include_refinement: bool = True,
) -> dict:
    profile = _get_profile(model_id)
    client = _get_client()
    request_body = _build_converse_request(
        prompt,
        profile,
        system_prompt=system_prompt,
        refinement=refinement,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        include_refinement=include_refinement,
    )
    invoked_model_id = model_id
    profile_fallback_used = False
    started_at = perf_counter()

    try:
        response = client.converse(modelId=invoked_model_id, **request_body)
    except ClientError as exc:
        if _should_retry_with_profile(exc, profile, model_id):
            invoked_model_id = profile.inference_profile_id or model_id
            profile_fallback_used = True
            try:
                response = client.converse(modelId=invoked_model_id, **request_body)
            except (ClientError, BotoCoreError) as retry_exc:
                details = {
                    "region": _resolve_region(),
                    "model_id": model_id,
                    "invoked_model_id": invoked_model_id,
                    "request_body": request_body,
                    "error_type": type(retry_exc).__name__,
                    "exception": str(retry_exc),
                    "profile_fallback_used": profile_fallback_used,
                }
                if isinstance(retry_exc, ClientError):
                    details["aws_error"] = retry_exc.response.get("Error", {})
                    details["request_id"] = retry_exc.response.get("ResponseMetadata", {}).get("RequestId")
                raise BedrockInvocationError("Bedrock request failed", details) from retry_exc
        else:
            details = {
                "region": _resolve_region(),
                "model_id": model_id,
                "invoked_model_id": invoked_model_id,
                "request_body": request_body,
                "error_type": type(exc).__name__,
                "exception": str(exc),
                "profile_fallback_used": profile_fallback_used,
                "aws_error": exc.response.get("Error", {}),
                "request_id": exc.response.get("ResponseMetadata", {}).get("RequestId"),
            }
            raise BedrockInvocationError("Bedrock request failed", details) from exc
    except BotoCoreError as exc:
        details = {
            "region": _resolve_region(),
            "model_id": model_id,
            "invoked_model_id": invoked_model_id,
            "request_body": request_body,
            "error_type": type(exc).__name__,
            "exception": str(exc),
            "profile_fallback_used": profile_fallback_used,
        }
        raise BedrockInvocationError("Bedrock request failed", details) from exc

    latency_ms = response.get("metrics", {}).get("latencyMs")
    if latency_ms is None:
        latency_ms = round((perf_counter() - started_at) * 1000)

    content = response.get("output", {}).get("message", {}).get("content") or []
    text = _extract_text_from_content(content)
    if not text:
        raise BedrockInvocationError(
            "Bedrock response missing text content",
            {
                "region": _resolve_region(),
                "model_id": model_id,
                "invoked_model_id": invoked_model_id,
                "request_body": request_body,
                "raw_response": response,
                "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
            },
        )

    usage = response.get("usage", {})
    input_tokens = usage.get("inputTokens")
    output_tokens = usage.get("outputTokens")
    total_tokens = usage.get("totalTokens")
    estimated_cost = estimate_cost(model_id, input_tokens, output_tokens)
    baseline_cost = estimate_cost(CLAUDE_SONNET_MODEL_ID, input_tokens, output_tokens)
    savings_pct = 0.0
    if baseline_cost:
        savings_pct = ((baseline_cost - estimated_cost) / baseline_cost) * 100

    debug = {
        "region": _resolve_region(),
        "model_id": _normalize_model_id(model_id),
        "invoked_model_id": invoked_model_id,
        "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
        "profile_fallback_used": profile_fallback_used,
        "request_format": profile.request_format,
        "model_display_name": profile.display_name,
        "stop_reason": response.get("stopReason"),
        "prompt_token_count": input_tokens,
        "generation_token_count": output_tokens,
        "total_token_count": total_tokens,
        "latency_ms": latency_ms,
        "estimated_cost": estimated_cost,
        "baseline_cost": baseline_cost,
        "savings_pct": savings_pct,
    }
    _record_request_metric(debug)

    return {
        "text": text,
        "latency_ms": latency_ms,
        "token_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
        "debug": debug,
    }


def call_model(
    model_id: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    refinement: str = "brief",
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
) -> dict:
    return _converse(
        model_id,
        prompt,
        system_prompt=system_prompt,
        refinement=refinement,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        include_refinement=True,
    )


def _extract_json_object(raw_text: str) -> dict | None:
    text = raw_text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def _sanitize_qwen_result(parsed: dict | None) -> dict:
    fallback = {"task": "general", "complexity": "medium", "confidence": "low"}
    if not isinstance(parsed, dict):
        return fallback

    task = str(parsed.get("task", "")).strip().lower()
    complexity = str(parsed.get("complexity", "")).strip().lower()
    confidence = str(parsed.get("confidence", "")).strip().lower()

    if task not in SUPPORTED_TASKS:
        task = fallback["task"]
    if complexity not in SUPPORTED_COMPLEXITIES:
        complexity = fallback["complexity"]
    if confidence not in SUPPORTED_CONFIDENCE:
        confidence = fallback["confidence"]

    return {"task": task, "complexity": complexity, "confidence": confidence}


def call_qwen(prompt: str) -> dict:
    fallback = {
        "task": "general",
        "complexity": "medium",
        "confidence": "low",
        "used_model_id": QWEN_MODEL_ID,
        "raw_text": "",
        "parse_success": False,
        "latency_ms": 0,
        "token_usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "estimated_cost": 0.0,
        "debug": {},
    }
    try:
        response = _converse(
            QWEN_MODEL_ID,
            prompt,
            system_prompt=QWEN_CLASSIFIER_SYSTEM_PROMPT,
            refinement="brief",
            max_tokens=30,
            temperature=0.0,
            top_p=0.1,
            include_refinement=False,
        )
    except BedrockInvocationError as exc:
        logger.warning("Qwen classifier failed; falling back to heuristic routing: %s", exc)
        fallback["debug"] = {"error": str(exc), **exc.details}
        return fallback

    parsed = _extract_json_object(response["text"])
    sanitized = _sanitize_qwen_result(parsed)
    return {
        **sanitized,
        "used_model_id": response["debug"]["invoked_model_id"],
        "raw_text": response["text"],
        "parse_success": parsed is not None,
        "latency_ms": response["latency_ms"],
        "token_usage": response["token_usage"],
        "estimated_cost": response["debug"]["estimated_cost"],
        "debug": response["debug"],
    }
