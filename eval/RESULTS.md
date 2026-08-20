# Eval results

Regenerate with `python eval/harness.py` (scores whatever's actually been
rendered — see backlot/render_eval_conditions.py — not an arbitrary --n;
--n only applies to `--dry-run`). Do not hand-edit — this file is generated
so the numbers stay honest.

| Metric | Value |
|---|---|
| Seeded conditions | 11 |
| Agent detection rate | 100% |
| Agent false positive rate | 25% |
| Baseline (threshold-alerting) detection rate | 100% |
| **Defects the baseline missed that vision caught** | **6** |

The last row is the whole thesis: a job can finish with every metric green and
still produce a visibly broken frame. `vision_only_catches` counts exactly
those cases, seeded and reproduced by a real render (see backlot/conditions/),
not asserted.

**On the false positive rate.** Both false positives in this run (`eval-clean-001`,
`eval-kill_worker-010`) are the verify loop's re-examination step over-interpreting
subtle, entirely normal fur/eye detail as a defect ("a faint horizontal seam,"
"blocky low-resolution artifacts") on frames that are genuinely clean — visually
confirmed by inspecting the actual PNGs, not assumed. This is real vision-model
behavior at n=11, reported as-is rather than re-prompted until it disappears:
narrowing a small eval sample to hit a round number would be exactly the kind of
unearned confidence this project argues against. The fix worth pursuing next is
tightening SkepticAgent's "be genuinely skeptical" instruction so it doesn't push
ReexamineAgent to manufacture a finding on an already-clean frame — not visible
in this scorecard yet.
