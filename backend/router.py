import logging
import multiprocessing
import os
from queue import Empty

from backend.model import (
    BedrockInvocationError,
    CLAUDE_SONNET_MODEL_ID,
    NOVA_PRO_MODEL_ID,
    SONNET_46_BENCHMARK_DISPLAY_NAME,
    SONNET_46_BENCHMARK_MODEL_ID,
    call_model,
    call_qwen,
    get_model_display_name,
    get_practical_benchmark_model_id,
)
from backend.routing_pipeline import build_decision

logger = logging.getLogger(__name__)
MODEL_CALL_TIMEOUT_SECONDS = float(os.getenv("ROUTER_MODEL_CALL_TIMEOUT_SECONDS", "20"))
STRONG_MODEL_CALL_TIMEOUT_SECONDS = float(os.getenv("ROUTER_STRONG_MODEL_CALL_TIMEOUT_SECONDS", "30"))


def _get_timeout_seconds(model_id: str) -> float:
    if model_id == CLAUDE_SONNET_MODEL_ID:
        return max(MODEL_CALL_TIMEOUT_SECONDS, STRONG_MODEL_CALL_TIMEOUT_SECONDS)
    return MODEL_CALL_TIMEOUT_SECONDS


def _model_call_worker(result_queue, model_id: str, prompt: str, refinement: str) -> None:
    try:
        result_queue.put(
            {
                "ok": True,
                "result": call_model(model_id, prompt, refinement=refinement),
            }
        )
    except BedrockInvocationError as exc:
        result_queue.put(
            {
                "ok": False,
                "error": str(exc),
                "details": exc.details,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        result_queue.put(
            {
                "ok": False,
                "error": str(exc),
                "details": {
                    "model_id": model_id,
                    "error_type": type(exc).__name__,
                    "exception": str(exc),
                },
            }
        )


def _call_model_with_timeout(model_id: str, prompt: str, refinement: str) -> dict:
    timeout_seconds = _get_timeout_seconds(model_id)
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_model_call_worker,
        args=(result_queue, model_id, prompt, refinement),
    )
    process.start()
    try:
        message = result_queue.get(timeout=timeout_seconds)
    except Empty:
        process.terminate()
        process.join(timeout=2)
        raise BedrockInvocationError(
            "Bedrock request timed out",
            {
                "model_id": model_id,
                "invoked_model_id": model_id,
                "error_type": "TimeoutError",
                "exception": f"Model execution exceeded {timeout_seconds:.0f}s",
                "timeout_seconds": timeout_seconds,
            },
        )
    finally:
        if process.is_alive():
            process.join(timeout=1)

    if message.get("ok"):
        return message["result"]
    raise BedrockInvocationError(message.get("error", "Bedrock request failed"), message.get("details", {}))


def _build_debug_payload(decision, response_debug: dict | None = None) -> dict:
    response_debug = response_debug or {}
    model_cost = float(response_debug.get("estimated_cost", 0.0) or 0.0)
    model_latency_ms = int(response_debug.get("latency_ms", 0) or 0)
    selected_model_id = decision.selected_model_id
    served_model_id = response_debug.get("invoked_model_id") or response_debug.get("model_id") or selected_model_id
    request_cost = model_cost + decision.classifier_cost
    request_latency_ms = model_latency_ms + decision.classifier_latency_ms
    prompt_tokens = response_debug.get("prompt_token_count")
    output_tokens = response_debug.get("generation_token_count")
    fallback_baseline_model = get_practical_benchmark_model_id(
        response_debug.get("model_id") or decision.selected_model_id,
        prompt_tokens,
        output_tokens,
    )
    baseline_model = response_debug.get("baseline_model", fallback_baseline_model)
    baseline_model_display_name = response_debug.get(
        "baseline_model_display_name",
        get_model_display_name(baseline_model),
    )
    baseline_cost = float(
        response_debug.get("baseline_cost", response_debug.get("practical_baseline_cost", 0.0)) or 0.0
    )
    model_saved_amount = baseline_cost - model_cost
    request_saved_amount = baseline_cost - request_cost
    model_savings_pct = 0.0
    net_savings_pct = 0.0
    if baseline_cost:
        model_savings_pct = ((baseline_cost - model_cost) / baseline_cost) * 100
        net_savings_pct = ((baseline_cost - request_cost) / baseline_cost) * 100

    premium_baseline_model = response_debug.get("premium_baseline_model", SONNET_46_BENCHMARK_MODEL_ID)
    premium_baseline_model_display_name = response_debug.get(
        "premium_baseline_model_display_name",
        SONNET_46_BENCHMARK_DISPLAY_NAME,
    )
    premium_baseline_cost = float(response_debug.get("premium_baseline_cost", 0.0) or 0.0)
    premium_model_saved_amount = premium_baseline_cost - model_cost
    premium_request_saved_amount = premium_baseline_cost - request_cost
    premium_model_savings_pct = 0.0
    premium_net_savings_pct = 0.0
    if premium_baseline_cost:
        premium_model_savings_pct = ((premium_baseline_cost - model_cost) / premium_baseline_cost) * 100
        premium_net_savings_pct = ((premium_baseline_cost - request_cost) / premium_baseline_cost) * 100

    return {
        **response_debug,
        "prompt_word_count": decision.signals["word_count"],
        "task": decision.task,
        "complexity": decision.complexity,
        "uncertainty": decision.uncertainty,
        "uncertainty_label": decision.uncertainty_label,
        "prefilter": decision.prefilter,
        "route_path": decision.route_path,
        "decision_path": decision.decision_path,
        "task_source": decision.task_source,
        "complexity_source": decision.complexity_source,
        "recommended_tier": decision.recommended_tier,
        "analysis_backend": decision.analysis_backend,
        "used_qwen": decision.used_qwen,
        "refinement": decision.refinement,
        "qwen_confidence": decision.qwen_confidence,
        "reason": decision.reason,
        "routing_reason": decision.reason,
        "overrides": decision.overrides,
        "candidate_scores": decision.candidate_scores,
        "signal_snapshot": decision.signals,
        "uncertainty_reasons": decision.uncertainty_reasons,
        "qwen_result": decision.qwen_result,
        "classifier_cost": decision.classifier_cost,
        "classifier_latency_ms": decision.classifier_latency_ms,
        "classifier_token_usage": decision.classifier_token_usage,
        "model_latency_ms": model_latency_ms,
        "latency_ms": request_latency_ms,
        "model_estimated_cost": model_cost,
        "estimated_cost": request_cost,
        "actual_cost": request_cost,
        "selected_model_id": selected_model_id,
        "selected_model_display_name": get_model_display_name(selected_model_id),
        "served_model_id": served_model_id,
        "served_model_display_name": get_model_display_name(served_model_id),
        "model_saved_amount": model_saved_amount,
        "net_saved_amount": request_saved_amount,
        "model_savings_pct": model_savings_pct,
        "net_savings_pct": net_savings_pct,
        "baseline_model": baseline_model,
        "baseline_model_display_name": baseline_model_display_name,
        "baseline_cost": baseline_cost,
        "savings_pct": model_savings_pct,
        "practical_baseline_model": baseline_model,
        "practical_baseline_model_display_name": baseline_model_display_name,
        "practical_baseline_cost": baseline_cost,
        "practical_savings_pct": model_savings_pct,
        "practical_net_savings_pct": net_savings_pct,
        "premium_baseline_model": premium_baseline_model,
        "premium_baseline_model_display_name": premium_baseline_model_display_name,
        "premium_baseline_cost": premium_baseline_cost,
        "premium_model_saved_amount": premium_model_saved_amount,
        "premium_net_saved_amount": premium_request_saved_amount,
        "premium_model_savings_pct": premium_model_savings_pct,
        "premium_net_savings_pct": premium_net_savings_pct,
    }


def route_prompt(prompt: str, refinement: str = "brief") -> dict:
    decision = build_decision(prompt, refinement=refinement, classifier=call_qwen)
    model_id = decision.selected_model_id

    try:
        response = _call_model_with_timeout(model_id, prompt, refinement=refinement)
    except BedrockInvocationError as exc:
        fallback_used = False
        fallback_response = None
        fallback_error = None

        if model_id != NOVA_PRO_MODEL_ID:
            try:
                fallback_response = _call_model_with_timeout(NOVA_PRO_MODEL_ID, prompt, refinement=refinement)
                fallback_used = True
            except BedrockInvocationError as fallback_exc:
                fallback_error = fallback_exc

        if fallback_response:
            fallback_debug = {
                **fallback_response["debug"],
                "fallback_used": True,
                "fallback_from_model": model_id,
                "fallback_reason": "selected_model_failed_retrying_with_nova_pro",
                "primary_model_failure": exc.details,
            }
            debug = _build_debug_payload(decision, fallback_debug)
            logger.warning(
                "Route fallback succeeded from=%s to=%s refinement=%s estimated_cost=%.8f",
                model_id,
                fallback_response["debug"].get("invoked_model_id", NOVA_PRO_MODEL_ID),
                refinement,
                debug["estimated_cost"],
            )
            return {
                "ok": True,
                "prompt": prompt,
                "model_used": fallback_response["debug"].get("invoked_model_id", NOVA_PRO_MODEL_ID),
                "response": fallback_response["text"],
                "debug": debug,
            }

        debug = _build_debug_payload(decision, exc.details)
        if fallback_error:
            debug["fallback_used"] = False
            debug["fallback_from_model"] = model_id
            debug["fallback_model"] = NOVA_PRO_MODEL_ID
            debug["fallback_reason"] = "selected_model_failed_retrying_with_nova_pro"
            debug["fallback_error"] = fallback_error.details
        logger.warning(
            "Route failed model=%s refinement=%s estimated_cost=%.8f",
            model_id,
            refinement,
            debug["estimated_cost"],
        )
        return {
            "ok": False,
            "prompt": prompt,
            "model_used": exc.details.get("invoked_model_id", model_id),
            "response": None,
            "error": str(exc),
            "debug": debug,
        }

    debug = _build_debug_payload(decision, response["debug"])
    logger.info(
        "Route complete model=%s latency_ms=%s estimated_cost=%.8f baseline_cost=%.8f savings_pct=%.2f used_qwen=%s",
        response["debug"].get("invoked_model_id", model_id),
        debug["latency_ms"],
        debug["estimated_cost"],
        debug["baseline_cost"],
        debug["savings_pct"],
        decision.used_qwen,
    )
    return {
        "ok": True,
        "prompt": prompt,
        "model_used": response["debug"].get("invoked_model_id", model_id),
        "response": response["text"],
        "debug": debug,
    }
