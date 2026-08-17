from eval.scoring import DetectionResult, SeededCondition, score


def test_perfect_agent_scores_100pct_detection_and_zero_false_positive():
    conditions = [
        SeededCondition("a", "low_samples", has_visual_defect=True, metrics_would_alert=False),
        SeededCondition("b", "clean", has_visual_defect=False, metrics_would_alert=False),
    ]
    results = [
        DetectionResult("a", agent_flagged=True, baseline_flagged=False),
        DetectionResult("b", agent_flagged=False, baseline_flagged=False),
    ]
    sc = score(conditions, results)
    assert sc.detection_rate == 1.0
    assert sc.false_positive_rate == 0.0
    assert sc.vision_only_catches == 1


def test_vision_only_catches_counts_defects_baseline_would_miss():
    conditions = [
        SeededCondition("a", "low_samples", has_visual_defect=True, metrics_would_alert=False),
        SeededCondition("b", "kill_worker", has_visual_defect=False, metrics_would_alert=True),
    ]
    results = [
        DetectionResult("a", agent_flagged=True, baseline_flagged=False),
        DetectionResult("b", agent_flagged=False, baseline_flagged=True),
    ]
    sc = score(conditions, results)
    assert sc.vision_only_catches == 1
    assert sc.baseline_detection_rate == 1.0
    assert sc.agent_false_negatives == 0  # b has no visual defect, agent correctly didn't flag it


def test_false_positive_reduces_precision_not_recall():
    conditions = [
        SeededCondition("a", "clean", has_visual_defect=False, metrics_would_alert=False),
    ]
    results = [DetectionResult("a", agent_flagged=True, baseline_flagged=False)]
    sc = score(conditions, results)
    assert sc.agent_false_positives == 1
    assert sc.false_positive_rate == 1.0


def test_empty_conditions_do_not_divide_by_zero():
    sc = score([], [])
    assert sc.detection_rate == 0.0
    assert sc.false_positive_rate == 0.0
