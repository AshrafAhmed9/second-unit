# Eval results

Regenerate with `python eval/harness.py --n 30`. Do not hand-edit —
this file is generated so the numbers stay honest.

| Metric | Value |
|---|---|
| Seeded conditions | 30 |
| Agent detection rate | 100% |
| Agent false positive rate | 0% |
| Baseline (threshold-alerting) detection rate | 100% |
| **Defects the baseline missed that vision caught** | **10** |

The last row is the whole thesis: a job can finish with every metric green and
still produce a visibly broken frame. `vision_only_catches` counts exactly
those cases, seeded and reproduced by a real render (see backlot/conditions/),
not asserted.
