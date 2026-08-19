"""Pure scoring logic for the eval harness — kept separate from harness.py so
it's testable without live Grafana/Gemini calls. This is what turns
`eval/harness.py --n 30` into a number a judge can trust rather than a story.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SeededCondition:
    condition_id: str
    fault_type: str          # low_samples | break_texture | kill_worker | starve_memory | clean
    has_visual_defect: bool  # ground truth: is the picture actually wrong?
    metrics_would_alert: bool  # ground truth: would a threshold-alerting baseline catch this?


@dataclass(frozen=True)
class DetectionResult:
    condition_id: str
    agent_flagged: bool
    baseline_flagged: bool
    false_positive_rounds: int = 0  # how many verify-loop rounds it took to confirm


@dataclass
class Scorecard:
    n: int
    agent_true_positives: int
    agent_false_positives: int
    agent_false_negatives: int
    baseline_true_positives: int
    baseline_false_negatives: int
    vision_only_catches: int  # defects the baseline missed entirely and the agent caught
    detection_rate: float = field(init=False)
    baseline_detection_rate: float = field(init=False)
    false_positive_rate: float = field(init=False)

    def __post_init__(self):
        positives = self.agent_true_positives + self.agent_false_negatives
        self.detection_rate = round(self.agent_true_positives / positives, 3) if positives else 0.0
        base_positives = self.baseline_true_positives + self.baseline_false_negatives
        self.baseline_detection_rate = (
            round(self.baseline_true_positives / base_positives, 3) if base_positives else 0.0
        )
        total_flags = self.agent_true_positives + self.agent_false_positives
        self.false_positive_rate = round(self.agent_false_positives / total_flags, 3) if total_flags else 0.0


def score(conditions: list[SeededCondition], results: list[DetectionResult]) -> Scorecard:
    by_id = {r.condition_id: r for r in results}

    agent_tp = agent_fp = agent_fn = 0
    base_tp = base_fn = 0
    vision_only = 0

    for c in conditions:
        r = by_id[c.condition_id]

        if c.has_visual_defect and r.agent_flagged:
            agent_tp += 1
        elif c.has_visual_defect and not r.agent_flagged:
            agent_fn += 1
        elif not c.has_visual_defect and r.agent_flagged:
            agent_fp += 1

        if c.metrics_would_alert:
            if r.baseline_flagged:
                base_tp += 1
            else:
                base_fn += 1

        if c.has_visual_defect and not c.metrics_would_alert and r.agent_flagged:
            vision_only += 1

    return Scorecard(
        n=len(conditions),
        agent_true_positives=agent_tp,
        agent_false_positives=agent_fp,
        agent_false_negatives=agent_fn,
        baseline_true_positives=base_tp,
        baseline_false_negatives=base_fn,
        vision_only_catches=vision_only,
    )


def render_markdown(scorecard: Scorecard) -> str:
    return f"""# Eval results

Regenerate with `python eval/harness.py` (scores whatever's actually been
rendered — see backlot/render_eval_conditions.py — not an arbitrary --n;
--n only applies to `--dry-run`). Do not hand-edit — this file is generated
so the numbers stay honest.

| Metric | Value |
|---|---|
| Seeded conditions | {scorecard.n} |
| Agent detection rate | {scorecard.detection_rate:.0%} |
| Agent false positive rate | {scorecard.false_positive_rate:.0%} |
| Baseline (threshold-alerting) detection rate | {scorecard.baseline_detection_rate:.0%} |
| **Defects the baseline missed that vision caught** | **{scorecard.vision_only_catches}** |

The last row is the whole thesis: a job can finish with every metric green and
still produce a visibly broken frame. `vision_only_catches` counts exactly
those cases, seeded and reproduced by a real render (see backlot/conditions/),
not asserted.
"""
