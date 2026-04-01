import logging

from backend.model import CLAUDE_SONNET_MODEL_ID, BedrockInvocationError, call_model, call_qwen
from backend.routing_pipeline import build_decision

logger = logging.getLogger(__name__)


def _build_debug_payload(decision, response_debug: dict | None = None) -> dict:
    response_debug = response_debug or {}
    model_cost = float(response_debug.get("estimated_cost", 0.0) or 0.0)
    model_latency_ms = int(response_debug.get("latency_ms", 0) or 0)
    request_cost = model_cost + decision.classifier_cost
    request_latency_ms = model_latency_ms + decision.classifier_latency_ms
    baseline_cost = float(response_debug.get("baseline_cost", 0.0) or 0.0)
    savings_pct = 0.0
    if baseline_cost:
        savings_pct = ((baseline_cost - request_cost) / baseline_cost) * 100

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
        "baseline_model": CLAUDE_SONNET_MODEL_ID,
        "baseline_cost": baseline_cost,
        "savings_pct": savings_pct,
    }


def route_prompt(prompt: str, refinement: str = "brief") -> dict:
    decision = build_decision(prompt, refinement=refinement, classifier=call_qwen)
    model_id = decision.selected_model_id

    try:
        response = call_model(model_id, prompt, refinement=refinement)
    except BedrockInvocationError as exc:
        debug = _build_debug_payload(decision, exc.details)
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
