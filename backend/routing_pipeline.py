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
    qwen_confidence: float | None
    qwen_result: dict[str, object]
    overrides: list[str]
    classifier_cost: float
    classifier_latency_ms: int
    classifier_token_usage: dict[str, int | None]
    uncertainty_reasons: list[str]
    signals: dict[str, object]


@dataclass(frozen=True)
class ResolvedRoute:
    model_id: str
    task: str
    complexity: str
    task_source: str
    complexity_source: str
    reason: str
    recommended_tier: str
    decision_steps: list[str]
    overrides: list[str]
    qwen_confidence: float | None
    analysis_backend: str


COMPLEXITY_LEVELS = {"low": 0, "medium": 1, "high": 2}
QWEN_CONFIDENCE_MAP = {"low": 0.35, "high": 0.85}
MODEL_TIER_MAP = {
    NOVA_MICRO_MODEL_ID: "cheap",
    MISTRAL_MODEL_ID: "general",
    CLAUDE_HAIKU_MODEL_ID: "safe_reasoning",
    NOVA_PRO_MODEL_ID: "code",
    CLAUDE_SONNET_MODEL_ID: "strong",
}
ROUTING_TABLE = {
    "code": {
        "low": MISTRAL_MODEL_ID,
        "medium": NOVA_PRO_MODEL_ID,
        "high": NOVA_PRO_MODEL_ID,
    },
    "math": {
        "low": NOVA_MICRO_MODEL_ID,
        "medium": CLAUDE_HAIKU_MODEL_ID,
        "high": CLAUDE_SONNET_MODEL_ID,
    },
    "reasoning": {
        "low": MISTRAL_MODEL_ID,
        "medium": CLAUDE_HAIKU_MODEL_ID,
        "high": CLAUDE_SONNET_MODEL_ID,
    },
    "general": {
        "low": NOVA_MICRO_MODEL_ID,
        "medium": CLAUDE_HAIKU_MODEL_ID,
        "high": CLAUDE_HAIKU_MODEL_ID,
    },
    "factual": {
        "low": NOVA_MICRO_MODEL_ID,
        "medium": CLAUDE_HAIKU_MODEL_ID,
        "high": CLAUDE_HAIKU_MODEL_ID,
    },
}


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
    if (
        prefilter.label == "ambiguous"
        and signals.has_reasoning_terms
        and contains_any(prompt, {"design", "build", "architecture", "distributed", "system", "strategy"})
    ):
        score += 0.2
        reasons.append("Ambiguous prompt includes system-design reasoning cues.")

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


def should_use_qwen(prefilter: PrefilterState, uncertainty: UncertaintyState) -> bool:
    return prefilter.label == "ambiguous" and uncertainty.score >= QWEN_UNCERTAINTY_THRESHOLD


def normalize_complexity(complexity: str | None) -> str:
    if complexity in COMPLEXITY_LEVELS:
        return complexity
    return "medium"


def normalize_task(task: str | None) -> str:
    if task in ROUTING_TABLE:
        return str(task)
    return "general"


def max_complexity(left: str, right: str) -> str:
    normalized_left = normalize_complexity(left)
    normalized_right = normalize_complexity(right)
    if COMPLEXITY_LEVELS[normalized_left] >= COMPLEXITY_LEVELS[normalized_right]:
        return normalized_left
    return normalized_right


def qwen_confidence_value(qwen_output: dict[str, object] | None) -> float | None:
    if not qwen_output:
        return None
    raw_confidence = qwen_output.get("confidence")
    if isinstance(raw_confidence, (int, float)):
        return max(0.0, min(1.0, float(raw_confidence)))
    if isinstance(raw_confidence, str):
        return QWEN_CONFIDENCE_MAP.get(raw_confidence.strip().lower(), 0.0)
    return 0.0


def recommended_tier_for_model(model_id: str) -> str:
    return MODEL_TIER_MAP.get(model_id, "general")


def direct_prefilter_override(prefilter: PrefilterState) -> tuple[str | None, str | None]:
    if prefilter.complexity == "low" and prefilter.label in {"greeting_direct", "math_direct", "factual_direct"}:
        return NOVA_MICRO_MODEL_ID, "prefilter_direct_cheap"
    if prefilter.complexity == "high" and prefilter.label in {"reasoning_direct", "math_direct"}:
        return CLAUDE_SONNET_MODEL_ID, "prefilter_direct_strong"
    return None, None


def apply_refinement_bias(
    model_id: str,
    task: str,
    complexity: str,
    refinement: str,
) -> tuple[str, str | None]:
    complexity = normalize_complexity(complexity)

    if refinement == "brief":
        if complexity == "high":
            return model_id, None
        if model_id == CLAUDE_SONNET_MODEL_ID and task == "reasoning" and complexity == "medium":
            return CLAUDE_HAIKU_MODEL_ID, "brief_bias_downgrade"
        if model_id == CLAUDE_HAIKU_MODEL_ID and task in {"general", "factual"}:
            return MISTRAL_MODEL_ID, "brief_bias_downgrade"
        if model_id == MISTRAL_MODEL_ID and task in {"general", "factual"} and complexity == "low":
            return NOVA_MICRO_MODEL_ID, "brief_bias_downgrade"
        return model_id, None

    if refinement == "bullet":
        if task == "code" and model_id != NOVA_PRO_MODEL_ID:
            return NOVA_PRO_MODEL_ID, "bullet_bias_structured_code"
        if task in {"general", "factual", "reasoning"} and model_id in {NOVA_MICRO_MODEL_ID, MISTRAL_MODEL_ID}:
            return CLAUDE_HAIKU_MODEL_ID, "bullet_bias_structured_answer"
        return model_id, None

    if refinement == "detailed":
        if task == "code" and model_id == MISTRAL_MODEL_ID:
            return NOVA_PRO_MODEL_ID, "detailed_bias_upgrade"
        if task in {"general", "factual", "reasoning"} and model_id == NOVA_MICRO_MODEL_ID:
            return MISTRAL_MODEL_ID, "detailed_bias_upgrade"
        if task in {"general", "factual", "reasoning"} and model_id == MISTRAL_MODEL_ID:
            return CLAUDE_HAIKU_MODEL_ID, "detailed_bias_upgrade"
        if task in {"reasoning", "math"} and model_id == CLAUDE_HAIKU_MODEL_ID and complexity in {"medium", "high"}:
            return CLAUDE_SONNET_MODEL_ID, "detailed_bias_upgrade"
        return model_id, None

    return model_id, None


def build_candidate_scores(
    final_model_id: str,
    task: str,
    complexity: str,
) -> dict[str, int]:
    scores = {
        NOVA_MICRO_MODEL_ID: 0,
        MISTRAL_MODEL_ID: 0,
        CLAUDE_HAIKU_MODEL_ID: 0,
        NOVA_PRO_MODEL_ID: 0,
        CLAUDE_SONNET_MODEL_ID: 0,
    }
    normalized_task = normalize_task(task)
    normalized_complexity = normalize_complexity(complexity)
    base_model_id = ROUTING_TABLE[normalized_task][normalized_complexity]
    scores[base_model_id] = 90
    scores[final_model_id] = 100

    if normalized_task == "code":
        scores[MISTRAL_MODEL_ID] = max(scores[MISTRAL_MODEL_ID], 40)
        scores[NOVA_PRO_MODEL_ID] = max(scores[NOVA_PRO_MODEL_ID], 70)
    elif normalized_task in {"general", "factual"}:
        scores[NOVA_MICRO_MODEL_ID] = max(scores[NOVA_MICRO_MODEL_ID], 60)
        scores[CLAUDE_HAIKU_MODEL_ID] = max(scores[CLAUDE_HAIKU_MODEL_ID], 30)
    elif normalized_task == "math":
        scores[CLAUDE_HAIKU_MODEL_ID] = max(scores[CLAUDE_HAIKU_MODEL_ID], 40)
        scores[CLAUDE_SONNET_MODEL_ID] = max(scores[CLAUDE_SONNET_MODEL_ID], 60)
    elif normalized_task == "reasoning":
        scores[MISTRAL_MODEL_ID] = max(scores[MISTRAL_MODEL_ID], 30)
        scores[CLAUDE_HAIKU_MODEL_ID] = max(scores[CLAUDE_HAIKU_MODEL_ID], 60)
        scores[CLAUDE_SONNET_MODEL_ID] = max(scores[CLAUDE_SONNET_MODEL_ID], 80)

    return scores


def resolve_model(
    prefilter: PrefilterState,
    qwen_output: dict[str, object] | None,
    heuristic_result: tuple[str, str, str] | None,
    signals: SignalProfile,
    refinement: str,
) -> ResolvedRoute:
    normalized_refinement = refinement if refinement in {"brief", "bullet", "detailed"} else "brief"
    overrides: list[str] = []
    decision_steps: list[str] = []
    hard_override_model, hard_override_reason = direct_prefilter_override(prefilter)
    if hard_override_model:
        decision_steps.extend(
            [
                "classification=prefilter_override",
                "qwen_used=false",
                f"task={normalize_task(prefilter.task)}",
                f"complexity={normalize_complexity(prefilter.complexity)}",
                f"final_model={hard_override_model}",
            ]
        )
        return ResolvedRoute(
            model_id=hard_override_model,
            task=normalize_task(prefilter.task),
            complexity=normalize_complexity(prefilter.complexity),
            task_source="prefilter_hard_override",
            complexity_source="prefilter_hard_override",
            reason=f"{hard_override_reason}: Deterministic prefilter override selected the final model.",
            recommended_tier=recommended_tier_for_model(hard_override_model),
            decision_steps=decision_steps,
            overrides=overrides,
            qwen_confidence=None,
            analysis_backend="deterministic_prefilter_override",
        )

    qwen_used = qwen_output is not None
    confidence = qwen_confidence_value(qwen_output)
    if prefilter.task and prefilter.complexity and prefilter.label != "ambiguous":
        task = normalize_task(prefilter.task)
        complexity = normalize_complexity(prefilter.complexity)
        task_source = "prefilter"
        complexity_source = "prefilter"
        reason = f"prefilter_direct_match: {prefilter.reason}"
        analysis_backend = "deterministic_prefilter_policy"
        decision_steps.append("classification=prefilter")
        decision_steps.append("qwen_used=false")
    elif qwen_used:
        task = normalize_task(str(qwen_output.get("task") or "general"))
        complexity = normalize_complexity(str(qwen_output.get("complexity") or "medium"))
        task_source = "qwen"
        complexity_source = "qwen"
        reason = "qwen_triggered_by_uncertainty: High-uncertainty ambiguous prompt triggered Qwen classification."
        analysis_backend = "deterministic_qwen_policy"
        decision_steps.extend(
            [
                "classification=qwen",
                "qwen_used=true",
                f"confidence={(confidence or 0.0):.2f}",
            ]
        )
        if (confidence or 0.0) < 0.6:
            overrides.append("low_qwen_confidence_fallback")
            complexity = max_complexity(complexity, "medium")
            decision_steps.extend(
                [
                    f"task={task}",
                    f"complexity={complexity}",
                    f"final_model={CLAUDE_HAIKU_MODEL_ID}",
                ]
            )
            return ResolvedRoute(
                model_id=CLAUDE_HAIKU_MODEL_ID,
                task=task,
                complexity=complexity,
                task_source=task_source,
                complexity_source=complexity_source,
                reason=(
                    "qwen_triggered_by_uncertainty: "
                    "Low-confidence Qwen output triggered the safe Kimi K2.5 fallback."
                ),
                recommended_tier=recommended_tier_for_model(CLAUDE_HAIKU_MODEL_ID),
                decision_steps=decision_steps,
                overrides=overrides,
                qwen_confidence=confidence,
                analysis_backend="deterministic_qwen_fallback",
            )
    else:
        heuristic_task, heuristic_complexity, heuristic_reason = heuristic_result or heuristic_analyse(signals)
        task = normalize_task(heuristic_task)
        complexity = normalize_complexity(heuristic_complexity)
        task_source = "heuristic_analysis"
        complexity_source = "heuristic_analysis"
        reason = f"heuristic_used_low_uncertainty: {heuristic_reason}"
        analysis_backend = "deterministic_heuristic_policy"
        decision_steps.extend(
            [
                "classification=heuristic",
                "qwen_used=false",
            ]
        )

    if prefilter.task in {"code", "math"} and task != prefilter.task:
        task = prefilter.task
        task_source = "prefilter_signal_override"
        complexity = max_complexity(complexity, normalize_complexity(prefilter.complexity))
        complexity_source = "prefilter_signal_override"
        overrides.append(f"prefilter_override_{prefilter.task}")
    elif signals.has_code_terms and task != "code":
        task = "code"
        task_source = "signal_override"
        complexity = max_complexity(complexity, "medium")
        complexity_source = "signal_override"
        overrides.append("signal_override_code")
    elif (signals.has_math_terms or signals.has_advanced_math_notation) and task != "math":
        task = "math"
        task_source = "signal_override"
        complexity = max_complexity(complexity, "medium")
        complexity_source = "signal_override"
        overrides.append("signal_override_math")
    elif (
        prefilter.label == "ambiguous"
        and signals.has_reasoning_terms
        and not signals.has_code_terms
        and not signals.has_math_terms
        and task != "reasoning"
        and contains_any(signals.normalized, {"design", "build", "architecture", "distributed", "system", "strategy"})
    ):
        task = "reasoning"
        task_source = "signal_override"
        target_complexity = "high" if contains_any(signals.normalized, {"design", "distributed", "architecture", "system"}) else "medium"
        complexity = max_complexity(complexity, target_complexity)
        complexity_source = "signal_override"
        overrides.append("signal_override_reasoning")

    if prefilter.label == "ambiguous" and looks_like_context_missing(signals) and signals.word_count <= 4:
        overrides.append("ambiguous_context_fallback")
        decision_steps.extend(
            [
                f"task={task}",
                f"complexity={max_complexity(complexity, 'medium')}",
                f"final_model={CLAUDE_HAIKU_MODEL_ID}",
            ]
        )
        return ResolvedRoute(
            model_id=CLAUDE_HAIKU_MODEL_ID,
            task=task,
            complexity=max_complexity(complexity, "medium"),
            task_source=task_source,
            complexity_source=complexity_source,
            reason=(
                "qwen_triggered_by_uncertainty: Ambiguous follow-up style prompt fell back to Kimi K2.5 "
                "for a safer recovery path."
                if qwen_used
                else "heuristic_used_low_uncertainty: Ambiguous follow-up style prompt fell back to "
                "Kimi K2.5 for a safer recovery path."
            ),
            recommended_tier=recommended_tier_for_model(CLAUDE_HAIKU_MODEL_ID),
            decision_steps=decision_steps,
            overrides=overrides,
            qwen_confidence=confidence,
            analysis_backend="deterministic_ambiguous_fallback",
        )

    base_model_id = ROUTING_TABLE[task][complexity]
    final_model_id, refinement_override = apply_refinement_bias(base_model_id, task, complexity, normalized_refinement)
    if refinement_override:
        overrides.append(refinement_override)

    decision_steps.extend(
        [
            f"task={task}",
            f"complexity={complexity}",
            f"final_model={final_model_id}",
        ]
    )
    return ResolvedRoute(
        model_id=final_model_id,
        task=task,
        complexity=complexity,
        task_source=task_source,
        complexity_source=complexity_source,
        reason=reason,
        recommended_tier=recommended_tier_for_model(final_model_id),
        decision_steps=decision_steps,
        overrides=overrides,
        qwen_confidence=confidence,
        analysis_backend=analysis_backend,
    )


def build_decision(prompt: str, refinement: str = "brief", classifier=None) -> DecisionState:
    normalized_refinement = refinement if refinement in {"brief", "bullet", "detailed"} else "brief"
    signals = extract_signals(prompt)
    prefilter = classify_prefilter(signals)
    uncertainty_state = evaluate_uncertainty(signals, prefilter)
    qwen_result: dict[str, object] = {}
    heuristic_result: tuple[str, str, str] | None = None
    used_qwen = False

    if should_use_qwen(prefilter, uncertainty_state) and classifier:
        used_qwen = True
        qwen_result = classifier(prompt)
    elif prefilter.label == "ambiguous":
        heuristic_result = heuristic_analyse(signals)

    resolved = resolve_model(
        prefilter=prefilter,
        qwen_output=qwen_result if used_qwen else None,
        heuristic_result=heuristic_result,
        signals=signals,
        refinement=normalized_refinement,
    )
    route_steps = [
        "signal_extraction",
        f"prefilter={prefilter.label}",
        f"uncertainty_check={uncertainty_state.score:.2f}",
        *resolved.decision_steps,
    ]
    candidate_scores = build_candidate_scores(
        final_model_id=resolved.model_id,
        task=resolved.task,
        complexity=resolved.complexity,
    )
    reason = resolved.reason
    if uncertainty_state.reasons:
        reason = f"{reason} Uncertainty triggers: {'; '.join(uncertainty_state.reasons)}"

    decision = DecisionState(
        task=resolved.task,
        complexity=resolved.complexity,
        uncertainty=uncertainty_state.score,
        uncertainty_label=uncertainty_state.label,
        prefilter=prefilter.label,
        route_path=" -> ".join(route_steps),
        decision_path=" -> ".join(route_steps),
        task_source=resolved.task_source,
        complexity_source=resolved.complexity_source,
        reason=reason,
        recommended_tier=resolved.recommended_tier,
        selected_model_id=resolved.model_id,
        candidate_scores=candidate_scores,
        analysis_backend=resolved.analysis_backend,
        used_qwen=used_qwen,
        refinement=normalized_refinement,
        qwen_confidence=resolved.qwen_confidence,
        qwen_result=qwen_result,
        overrides=resolved.overrides,
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
