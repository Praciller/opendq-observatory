"""Explicit rule registry; no dynamic plugin loading."""

from collections.abc import Callable

from opendq.quality.models import QualityContext, QualityResult, QualityRuleDefinition
from opendq.quality.rules.completeness import evaluate_completeness
from opendq.quality.rules.freshness import evaluate_freshness
from opendq.quality.rules.gap import evaluate_timestamp_gap
from opendq.quality.rules.range import evaluate_range
from opendq.quality.rules.uniqueness import evaluate_uniqueness
from opendq.quality.rules.volume import evaluate_volume

RuleEvaluator = Callable[[QualityContext, QualityRuleDefinition], QualityResult]

RULE_EVALUATORS: dict[str, RuleEvaluator] = {
    "freshness": evaluate_freshness,
    "completeness": evaluate_completeness,
    "uniqueness": evaluate_uniqueness,
    "range": evaluate_range,
    "timestamp_gap": evaluate_timestamp_gap,
    "volume": evaluate_volume,
}
