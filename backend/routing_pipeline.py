from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass

from backend.model import (
    CLAUDE_HAIKU_MODEL_ID,
    CLAUDE_SONNET_MODEL_ID,
    MISTRAL_MODEL_ID,
    NOVA_MICRO_MODEL_ID,
    NOVA_PRO_MODEL_ID,
)

logger = logging.getLogger(__name__)

GREETING_TERMS = {"hi", "hello", "hey", "yo", "ok", "okay", "good morning", "good evening"}
CODE_TERMS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "fastapi",
    "sql",
    "code",
    "function",
    "class",
    "refactor",
    "debug",
    "bug",
    "implement",
    "hook",
    "api",
    "endpoint",
}
CODE_DIAGNOSTIC_TERMS = {
    "error",
    "slow",
    "algorithm",
    "loop",
    "fix",
    "optimize",
    "convert",
    "working",
}
MATH_TERMS = {
    "integrate",
    "prove",
    "derive",
    "solve",
    "simplify",
    "equation",
    "theorem",
    "gradient",
    "integration",
}
REASONING_TERMS = {
    "explain",
    "why",
    "compare",
    "design",
    "build",
    "strategy",
    "system",
    "distributed",
    "consistency",
    "consensus",
    "transformers",
    "internet",
    "architecture",
}
FACTUAL_PREFIXES = (
    "what is",
    "what does",
    "difference between",
    "who wrote",
    "who invented",
    "when was",
    "capital of",
    "define ",
)
HIGH_COMPLEXITY_TERMS = {
    "scalable",
    "distributed",
    "consensus",
    "prove",
    "integrate",
    "derive",
    "refactor",
    "debug",
    "bug",
    "rate limiting",
    "high-traffic",
    "large input",
}
MEDIUM_COMPLEXITY_TERMS = {
    "explain",
    "compare",
    "summarize",
    "implement",
    "function",
    "article",
    "plan",
    "trip",
    "simplify",
    "idempotency",
    "recursion",
    "endpoint",
}
REFERENTIAL_TERMS = {"this", "it", "here", "that"}
FOLLOW_UP_TERMS = {
    "faster",
    "shorter",
    "more",
    "example",
    "optimize",
    "improve",
    "convert",
    "working",
    "happening",
}
QWEN_UNCERTAINTY_THRESHOLD = 0.5
HAIKU_FALLBACK_THRESHOLD = 0.65
SIMPLE_MATH_RE = re.compile(r"^\s*[\d\s\+\-\*\/\(\)]+\s*$")
ADVANCED_MATH_RE = re.compile(
    r"(∫|∑|√|π|∞|∂|∇|dx\b|dy\b|dz\b|sin\b|cos\b|tan\b|log\b|ln\b|[a-z]\^[a-z0-9]|\([a-z0-9\+\-\*/\s]+\)\^[a-z0-9])"
)


@dataclass(frozen=True)
class SignalProfile:
    prompt: str
    normalized: str
    word_count: int
    char_count: int
    contains_greeting: bool
    has_code_terms: bool
    has_math_terms: bool
    has_reasoning_terms: bool
    starts_factual: bool
    is_symbolic_math: bool
    has_advanced_math_notation: bool


@dataclass(frozen=True)
class PrefilterState:
    label: str
    task: str | None
    complexity: str | None
    reason: str


@dataclass(frozen=True)
class UncertaintyState:
    score: float
    label: str
    reasons: list[str]


@dataclass(frozen=True)
class DecisionState:
    task: str
    complexity: str
    uncertainty: float
    uncertainty_label: str
    prefilter: str
    route_path: str
    decision_path: str
    task_source: str
    complexity_source: str
    reason: str
    recommended_tier: str
    selected_model_id: str
    candidate_scores: dict[str, int]
    analysis_backend: str
    used_qwen: bool
    refinement: str
    qwen_result: dict[str, object]
    classifier_cost: float
    classifier_latency_ms: int
    classifier_token_usage: dict[str, int | None]
    uncertainty_reasons: list[str]
    signals: dict[str, object]


def contains_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9\- ]+", term):
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in term.split()) + r"\b"
        return bool(re.search(pattern, text))
    return term in text


def contains_any(text: str, terms: set[str]) -> bool:
    return any(contains_term(text, term) for term in terms)


def extract_signals(prompt: str) -> SignalProfile:
    normalized = " ".join(prompt.lower().strip().split())
    words = re.findall(r"[a-zA-Z0-9\-\+\*\/\^_]+", normalized)
    return SignalProfile(
        prompt=prompt,
        normalized=normalized,
        word_count=len(words),
        char_count=len(normalized),
        contains_greeting=normalized in GREETING_TERMS or normalized.startswith("hello "),
        has_code_terms=contains_any(normalized, CODE_TERMS | CODE_DIAGNOSTIC_TERMS),
        has_math_terms=bool(SIMPLE_MATH_RE.match(normalized)) or contains_any(normalized, MATH_TERMS),
        has_reasoning_terms=contains_any(normalized, REASONING_TERMS),
        starts_factual=normalized.startswith(FACTUAL_PREFIXES),
        is_symbolic_math=bool(SIMPLE_MATH_RE.match(normalized)),
        has_advanced_math_notation=bool(ADVANCED_MATH_RE.search(normalized)),
    )


def looks_like_context_missing(signals: SignalProfile) -> bool:
    prompt = signals.normalized
    has_reference = contains_any(prompt, REFERENTIAL_TERMS)
    has_follow_up = contains_any(prompt, FOLLOW_UP_TERMS)
    short_follow_up = (
        signals.word_count <= 3
        and not signals.has_code_terms
        and not signals.has_math_terms
        and contains_any(prompt, {"add", "example", "optimize", "improve", "shorter", "faster"})
    )
    return (has_reference and has_follow_up) or short_follow_up or prompt in {"??", "and?", "this?", "hmm"}


def classify_prefilter(signals: SignalProfile) -> PrefilterState:
    prompt = signals.normalized

    if signals.contains_greeting:
        return PrefilterState(
            label="greeting_direct",
            task="general",
            complexity="low",
            reason="Greeting or casual opener matched the low-cost general rule.",
        )

    if looks_like_context_missing(signals):
        return PrefilterState(
            label="ambiguous",
            task="general",
            complexity="medium",
            reason="The prompt looks context-dependent, so it should be treated as ambiguous.",
        )

    if signals.is_symbolic_math:
        return PrefilterState(
            label="math_direct",
            task="math",
            complexity="low",
            reason="Plain symbolic arithmetic matched the direct math rule.",
        )

    if signals.has_advanced_math_notation:
        complexity = "high" if any(contains_term(prompt, term) for term in {"dx", "dy", "dz", "∫", "derive"}) else "medium"
        return PrefilterState(
            label="math_direct",
            task="math",
            complexity=complexity,
            reason="Advanced notation triggered the math rule.",
        )

    if signals.has_math_terms:
        complexity = "high"
        if contains_term(prompt, "solve") and any(char.isdigit() for char in prompt):
            complexity = "low"
        elif contains_term(prompt, "simplify"):
            complexity = "medium"
        return PrefilterState(
            label="math_direct",
            task="math",
            complexity=complexity,
            reason="Math keywords matched the direct math rule.",
        )

    if signals.starts_factual:
        complexity = "medium" if contains_any(prompt, {"idempotency", "api", "binary search"}) else "low"
        return PrefilterState(
            label="factual_direct",
            task="factual",
            complexity=complexity,
            reason="Question phrasing matched the factual lookup rule.",
        )

    if signals.has_code_terms:
        complexity = "high" if contains_any(prompt, {"bug", "debug", "refactor", "rate limiting", "error", "slow"}) else "medium"
        return PrefilterState(
            label="code_direct",
            task="code",
            complexity=complexity,
            reason="Code keywords triggered direct code routing.",
        )

    if prompt.startswith("why ") or prompt.startswith("how ") or prompt.startswith("explain ") or prompt.startswith("compare "):
        complexity = "high" if contains_any(prompt, {"distributed", "consensus", "architecture", "scalable"}) else "medium"
        return PrefilterState(
            label="reasoning_direct",
            task="reasoning",
            complexity=complexity,
            reason="Reasoning phrasing matched the direct reasoning rule.",
        )

    return PrefilterState(
        label="ambiguous",
        task=None,
        complexity=None,
        reason="No direct prefilter rule matched.",
    )


def evaluate_uncertainty(
    signals: SignalProfile,
    prefilter: PrefilterState,
) -> UncertaintyState:
    reasons: list[str] = []
    score = 0.0
    prompt = signals.normalized

    if prefilter.label == "ambiguous":
        score += 0.35
        reasons.append("Prefilter marked the prompt ambiguous.")
    if looks_like_context_missing(signals):
        score += 0.35
        reasons.append("Prompt appears context-dependent or follow-up-like.")
    if signals.word_count <= 2 and not signals.contains_greeting and not signals.is_symbolic_math:
        score += 0.2
        reasons.append("Prompt is extremely short.")
    if sum([signals.has_code_terms, signals.has_math_terms, signals.has_reasoning_terms]) >= 2:
        score += 0.2
        reasons.append("Prompt mixes multiple intent signals.")
    if contains_any(prompt, {"help", "something"}) and signals.word_count <= 7:
        score += 0.15
        reasons.append("Prompt asks for help without enough topical detail.")

    score = min(1.0, round(score, 2))
    if score >= HAIKU_FALLBACK_THRESHOLD:
        label = "high"
    elif score >= 0.35:
        label = "medium"
    else:
        label = "low"
    return UncertaintyState(score=score, label=label, reasons=reasons)


def heuristic_analyse(signals: SignalProfile) -> tuple[str, str, str]:
    prompt = signals.normalized

    if signals.has_code_terms and signals.has_reasoning_terms:
        if contains_any(prompt, {"write", "convert", "code"}):
            return "code", "medium", "Heuristic analysis favored code because implementation was explicitly requested."
        return "reasoning", "medium", "Heuristic analysis favored reasoning because explanation dominated."

    if signals.has_code_terms:
        if contains_any(prompt, {"error", "slow", "optimize", "algorithm"}):
            return "code", "high", "Heuristic analysis escalated to code due to debugging or optimization cues."
        return "code", "medium", "Heuristic analysis mapped the prompt to code."

    if signals.has_math_terms or signals.has_advanced_math_notation:
        if contains_any(prompt, {"integrate", "prove", "derive", "gradient"}):
            return "math", "high", "Heuristic analysis detected advanced math intent."
        return "math", "medium", "Heuristic analysis detected math intent."

    if contains_any(prompt, {"design", "build", "transformers", "internet", "recursion", "binary search"}):
        if contains_any(prompt, {"design", "build", "scalable", "distributed"}):
            return "reasoning", "high", "Heuristic analysis detected system-design style reasoning."
        return "reasoning", "medium", "Heuristic analysis detected explanatory reasoning."

    if signals.starts_factual or prompt.startswith("capital of") or prompt.startswith("define "):
        return "factual", "low", "Heuristic analysis detected a short factual lookup."

    if prompt.startswith("is ") and any(char.isdigit() for char in prompt):
        return "math", "medium", "Heuristic analysis treated the numeric comparison as math."

    if prompt.startswith("summarize") or prompt.startswith("plan ") or "email" in prompt:
        return "general", "medium", "Heuristic analysis treated the prompt as general writing assistance."

    return "general", "medium", "Heuristic analysis fell back to a medium-complexity general request."


def should_use_qwen(prefilter: PrefilterState, uncertainty: UncertaintyState, signals: SignalProfile) -> bool:
    return (
        prefilter.label == "ambiguous"
        and uncertainty.score > QWEN_UNCERTAINTY_THRESHOLD
        and signals.word_count > 6
    )


def select_model_tier(task: str, complexity: str, uncertainty_score: float, refinement: str) -> str:
    if uncertainty_score >= HAIKU_FALLBACK_THRESHOLD:
        return "safe_reasoning"
    if task == "code":
        return "code"
    if task == "reasoning":
        return "strong" if complexity == "high" or refinement == "detailed" else "reasoning"
    if task == "math":
        return "cheap" if complexity == "low" else "reasoning"
    if task == "factual":
        return "cheap" if complexity == "low" else "reasoning"
    return "cheap" if complexity == "low" and refinement == "brief" else "general"


def score_models(
    signals: SignalProfile,
    task: str,
    complexity: str,
    uncertainty_score: float,
    refinement: str,
) -> dict[str, int]:
    scores = {
        NOVA_MICRO_MODEL_ID: 0,
        MISTRAL_MODEL_ID: 0,
        CLAUDE_HAIKU_MODEL_ID: 0,
        NOVA_PRO_MODEL_ID: 0,
        CLAUDE_SONNET_MODEL_ID: 0,
    }

    if task == "factual":
        scores[NOVA_MICRO_MODEL_ID] += 5
        scores[MISTRAL_MODEL_ID] += 2
        scores[CLAUDE_HAIKU_MODEL_ID] += 1
    elif task == "general":
        scores[MISTRAL_MODEL_ID] += 5
        scores[NOVA_MICRO_MODEL_ID] += 1
        scores[CLAUDE_HAIKU_MODEL_ID] += 1
    elif task == "reasoning":
        scores[CLAUDE_HAIKU_MODEL_ID] += 3
        scores[CLAUDE_SONNET_MODEL_ID] += 4
    elif task == "code":
        scores[NOVA_PRO_MODEL_ID] += 6
        scores[CLAUDE_HAIKU_MODEL_ID] += 1
        scores[CLAUDE_SONNET_MODEL_ID] += 1
    elif task == "math":
        scores[NOVA_MICRO_MODEL_ID] += 2
        scores[MISTRAL_MODEL_ID] += 1
        scores[CLAUDE_HAIKU_MODEL_ID] += 2
        scores[CLAUDE_SONNET_MODEL_ID] += 2

    if complexity == "low":
        scores[NOVA_MICRO_MODEL_ID] += 2
        scores[MISTRAL_MODEL_ID] += 2
    elif complexity == "medium":
        scores[MISTRAL_MODEL_ID] += 1
        scores[CLAUDE_HAIKU_MODEL_ID] += 2
        if task == "code":
            scores[NOVA_PRO_MODEL_ID] += 2
    elif complexity == "high":
        scores[CLAUDE_HAIKU_MODEL_ID] += 2
        scores[CLAUDE_SONNET_MODEL_ID] += 4
        if task == "code":
            scores[NOVA_PRO_MODEL_ID] += 2

    if uncertainty_score > QWEN_UNCERTAINTY_THRESHOLD:
        scores[CLAUDE_HAIKU_MODEL_ID] += 3
        scores[CLAUDE_SONNET_MODEL_ID] += 1
    else:
        scores[NOVA_MICRO_MODEL_ID] += 1
        scores[MISTRAL_MODEL_ID] += 1

    if signals.starts_factual and complexity == "low":
        scores[NOVA_MICRO_MODEL_ID] += 1
    if signals.word_count >= 14:
        scores[CLAUDE_HAIKU_MODEL_ID] += 1
        scores[CLAUDE_SONNET_MODEL_ID] += 1

    if refinement == "brief":
        scores[NOVA_MICRO_MODEL_ID] += 2
        scores[MISTRAL_MODEL_ID] += 2
        scores[CLAUDE_SONNET_MODEL_ID] -= 1
    elif refinement == "bullet":
        scores[CLAUDE_HAIKU_MODEL_ID] += 2
        scores[NOVA_PRO_MODEL_ID] += 2
    elif refinement == "detailed":
        scores[CLAUDE_SONNET_MODEL_ID] += 2
        scores[CLAUDE_HAIKU_MODEL_ID] += 1

    return scores


def apply_safety_rules(
    candidate_scores: dict[str, int],
    task: str,
    complexity: str,
    uncertainty_score: float,
) -> tuple[dict[str, int], list[str], str | None]:
    scores = dict(candidate_scores)
    safety_reasons: list[str] = []
    forced_model_id: str | None = None

    if complexity == "high":
        scores[NOVA_MICRO_MODEL_ID] = -999
        scores[MISTRAL_MODEL_ID] = -999
        safety_reasons.append("High complexity blocked the cheap models.")

    if task == "code":
        scores[NOVA_MICRO_MODEL_ID] = -999
        scores[NOVA_PRO_MODEL_ID] += 2
        safety_reasons.append("Code tasks never use Nova Micro.")

    if uncertainty_score >= HAIKU_FALLBACK_THRESHOLD:
        forced_model_id = CLAUDE_HAIKU_MODEL_ID
        safety_reasons.append("High uncertainty triggered the Claude Haiku fallback.")

    return scores, safety_reasons, forced_model_id


def choose_model_id(candidate_scores: dict[str, int], forced_model_id: str | None = None) -> str:
    if forced_model_id:
        return forced_model_id
    return max(candidate_scores.items(), key=lambda item: item[1])[0]


def build_decision(prompt: str, refinement: str = "brief", classifier=None) -> DecisionState:
    normalized_refinement = refinement if refinement in {"brief", "bullet", "detailed"} else "brief"
    signals = extract_signals(prompt)
    prefilter = classify_prefilter(signals)
    uncertainty_state = evaluate_uncertainty(signals, prefilter)

    route_steps: list[str] = ["signal_extraction", prefilter.label]
    task_source = "prefilter"
    complexity_source = "prefilter"
    analysis_backend = "prefilter_only"

    if prefilter.task and prefilter.complexity and prefilter.label != "ambiguous" and uncertainty_state.score <= QWEN_UNCERTAINTY_THRESHOLD:
        task = prefilter.task
        complexity = prefilter.complexity
        reason = prefilter.reason
        route_steps.append("direct_prefilter")
    else:
        task, complexity, heuristic_reason = heuristic_analyse(signals)
        task_source = "heuristic_analysis"
        complexity_source = "heuristic_analysis"
        analysis_backend = "heuristic_analysis"
        reason = heuristic_reason
        route_steps.append("heuristic_analysis")
        if uncertainty_state.reasons:
            reason = f"{heuristic_reason} Uncertainty triggers: {'; '.join(uncertainty_state.reasons)}"

    qwen_result: dict[str, object] = {}
    used_qwen = False
    effective_uncertainty = uncertainty_state.score
    effective_uncertainty_label = uncertainty_state.label

    if should_use_qwen(prefilter, uncertainty_state, signals) and classifier:
        used_qwen = True
        analysis_backend = "heuristic_plus_qwen"
        route_steps.append("qwen_classifier")
        qwen_result = classifier(prompt)
        if qwen_result.get("confidence") == "high":
            task = str(qwen_result.get("task") or task)
            complexity = str(qwen_result.get("complexity") or complexity)
            task_source = "qwen_override"
            complexity_source = "qwen_override"
            effective_uncertainty = min(effective_uncertainty, 0.45)
            effective_uncertainty_label = "medium" if effective_uncertainty >= 0.35 else "low"
            reason = (
                f"{reason} Qwen returned a high-confidence override to {task}/{complexity}, "
                "so the router accepted it and lowered effective uncertainty."
            )
        else:
            reason = f"{reason} Qwen returned low confidence, so the router kept the heuristic classification."

    recommended_tier = select_model_tier(task, complexity, effective_uncertainty, normalized_refinement)
    candidate_scores = score_models(
        signals,
        task,
        complexity,
        effective_uncertainty,
        normalized_refinement,
    )
    candidate_scores, safety_reasons, forced_model_id = apply_safety_rules(
        candidate_scores,
        task,
        complexity,
        effective_uncertainty,
    )
    if safety_reasons:
        route_steps.append("safety_rules")
        reason = f"{reason} {' '.join(safety_reasons)}"

    selected_model_id = choose_model_id(candidate_scores, forced_model_id)

    decision = DecisionState(
        task=task,
        complexity=complexity,
        uncertainty=effective_uncertainty,
        uncertainty_label=effective_uncertainty_label,
        prefilter=prefilter.label,
        route_path=" -> ".join(route_steps),
        decision_path=" -> ".join(route_steps),
        task_source=task_source,
        complexity_source=complexity_source,
        reason=reason,
        recommended_tier=recommended_tier,
        selected_model_id=selected_model_id,
        candidate_scores=candidate_scores,
        analysis_backend=analysis_backend,
        used_qwen=used_qwen,
        refinement=normalized_refinement,
        qwen_result=qwen_result,
        classifier_cost=float(qwen_result.get("estimated_cost", 0.0) or 0.0),
        classifier_latency_ms=int(qwen_result.get("latency_ms", 0) or 0),
        classifier_token_usage=qwen_result.get("token_usage", {}) or {},
        uncertainty_reasons=uncertainty_state.reasons,
        signals=asdict(signals),
    )
    logger.info(
        "Routing decision path=%s task=%s complexity=%s uncertainty=%.2f model=%s used_qwen=%s",
        decision.decision_path,
        decision.task,
        decision.complexity,
        decision.uncertainty,
        decision.selected_model_id,
        decision.used_qwen,
    )
    return decision
