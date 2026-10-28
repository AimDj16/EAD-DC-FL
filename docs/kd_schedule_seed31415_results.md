# Within-FL KD schedule controls: seed-31415 replication

Verified 28 October 2026 from kd_schedule_seed31415_v1_reports.tar.gz, SHA256
6521d93804f7836bc65ce3b534f39aea1869b54c327ba1f96a4962ebc916c170.
Four additional 12-round FL controls, with two existing original full-KD references
reused. EAD is enabled and aggregation is sample-weighted FedAvg throughout.
The matched experiment identifier is
681c3b44d178754c04d1fc20581b80782caf3ec15e9769fc5fa0481e8ca3983d.

## Audit and evidence boundary

All six report hashes and the three bundled code hashes match the prepared sources
and bundle summary. Original benign/targeted references are byte-identical to the
earlier uploaded main-study archives. The manifest identifier, initial tensor hashes,
matched fingerprints, local orders and participation records are consistent.
Every new control reproduces original round-1 pre-KD training/screening records.
Both warm-start-only controls reproduce the original round-1–3 cluster records and
recorded checkpoint hashes, with runtime exact-tensor checks reported. The complete
summary was independently recomputed exactly.

Detector voting/calibration, FedAvg survivor weights, poisoning counts, teacher
selection and KD decisions were checked over all 216 round/architecture records.
Each targeted round records the same 1,497 label changes across the fixed nine
compromised clients. Raw data, poison arrays, checkpoint tensors and per-example
predictions are not in this aggregate archive; they have not been independently
reloaded here. Final-test evaluation and protocol freezing are both false.

## What replicates and what changes

Entries below are the maximum positive excess committed Malware-to-Normal error
over 12 rounds, relative to each policy's own same-seed benign run, in percentage
points. The largest observed values are descriptive, not robustness guarantees.

| Seed | KD schedule | Small | Medium | Deep |
|---|---|---|---|---|
| 42 | Original full KD | 0.00 | 0.00 | 0.00 |
| 42 | Master warm-start only | 0.00 | 0.00 | 0.00 |
| 42 | Adaptive KD, no master teaching | 0.12 | 13.11 | 52.81 |
| 31415 | Original full KD | 0.00 | 0.00 | 0.00 |
| 31415 | Master warm-start only | 0.00 | 0.00 | 0.00 |
| 31415 | Adaptive KD, no master teaching | 0.12 | 0.37 | 0.12 |

Original full KD and warm-start-only each match their policy-matched benign
committed TMR at all 72 architecture/round observations across these two seeds.
Absolute errors remain, including 2/801 = 0.2497% in every final model under those
policies. There are two run replications per condition, not 72 independent runs.

Thus, removing recurring KD after round 3 preserves that specific measured
protection in both evaluated seeds. EAD, FedAvg, master warm-start and client
training remain. This does not show that the master alone provides protection,
that other attack effects are absent or that later KD provides no utility benefit.

The no-master control has only small positive excess committed error in seed
31415, unlike the large transient failures in seed 42. The maximum 0.3745 pp is
three additional targeted errors out of 801 Malware examples. Do not generalise
the seed-42 failure into universal necessity of master teaching. Initialisation,
training order, detector randomness and ensuing teacher/acceptance trajectories
vary across seeds, with the data partition, master and compromised identities fixed.

## A successful security recovery during adaptive KD

In seed 31415, attacked adaptive-only teachers are:

deep, medium, small, deep, deep, deep, medium, deep, medium, medium, medium, medium.

Unlike seed 42, Deep is not the teacher in every round. It receives seven KD
phases, six accepted. In round 2, Medium teaches Deep:

| Stage | Accuracy | Macro-F1 | Malware-to-Normal errors |
|---|---|---|---|
| Deep before KD | 75.51% | 67.67% | 101/801 |
| Deep KD candidate, accepted | 77.34% | 70.03% | 1/801 |

This accepted KD step reduces targeted error by 100/801, or 12.48 percentage
points. Two Deep malicious uploads had survived screening. The Medium teacher has
3/801 targeted errors at that point. This is direct pre/candidate/committed evidence
of a security improvement during KD on the fixed current models. It does not prove
why all seed differences arise, since their whole trajectories also differ.

Deep checkpoint hashes agree with the earlier EAD-only trajectory only in round 1,
then differ in both benign and attacked runs, consistent with the changed KD
trajectory. In seed 42, attacked Deep was always teacher, received no KD, and its
hashes matched EAD-only throughout. Teacher self-skipping and recipient eligibility
therefore matter when interpreting protection attributed to adaptive KD.

An accuracy-only guard remains insufficient as a security guarantee. For example,
seed-31415 adaptive-only Small round 6 accepts a candidate increasing targeted
errors from 0 to 1 while accuracy rises 78.46% to 78.78%. This is a small event,
additional to the much larger accepted-KD security failures already documented.

## Endpoint utility

Seed-31415 round-12 attacked validation accuracy / macro-F1, percentages:

| KD schedule | Small | Medium | Deep |
|---|---|---|---|
| Original full KD | 85.86 / 84.83 | 86.09 / 84.81 | 86.13 / 85.21 |
| Warm-start only | 83.05 / 80.14 | 83.83 / 81.32 | 86.03 / 83.25 |
| Adaptive only | 82.55 / 79.12 | 82.75 / 79.31 | 83.12 / 79.58 |

Here, original full KD has higher final accuracy and macro-F1 than both alternatives
in all three architectures. This is not universal dominance: seed-42 Deep had higher
final utility under adaptive-only, despite its earlier large security failure.
Full KD and warm-start-only match targeted-error protection across both seeds, but
their endpoint utility differs. The two effects must be reported separately.

Warm-start-only Medium macro-F1 remains lower under attack, 81.32%, than benign,
84.59%, despite matching TMR. Zero excess for one targeted class transition does
not establish protection of macro-F1 or all class-specific outcomes.

## Screening and cost

Each attacked run has 108 malicious and 252 benign submissions. Each clean run has
360 benign submissions. Counts pool repeated observations, not replications.

| KD schedule | Attack TP/FN/FP/TN | Clean FP/TN | Attack calibration triggers |
|---|---|---|---|
| Original full KD | 96/12/1/251 | 34/326 | 35/36 |
| Warm-start only | 96/12/1/251 | 44/316 | 35/36 |
| Adaptive only | 99/9/0/252 | 37/323 | 36/36 |

Equal aggregate counts do not imply identical rejected identities or model
trajectories. EAD precedes current-round KD; later differences reflect trajectories.
The four new runs record 9,443.19 seconds, approximately 2.62 hours. Costs are not
compute-matched because KD exposure differs, and master pre-training is inherited.

## Thesis implications and next step

The two-seed evidence strengthens the bounded negative finding that recurring KD
after the master warm-start is not required to reproduce zero excess committed
targeted error in these evaluated configurations. The no-master results are
seed-dependent, preventing a universal necessity claim. KD can both repair targeted
behaviour and worsen it under accepted general-metric improvements. Chapter 4 should
present the controls and stage-specific results; Chapter 5 should synthesise teacher
selection, recipient eligibility, metric alignment and the role of trusted supervision.

Retain all policies as identifiable ablations without selecting a replacement on
the final test. Inspect the already requested seed-2026 archive before making a
three-seed summary. It has not been received in this workspace. If it already exists
on UWE, upload it without rerunning completed conditions. Four additional verified
controls here bring the current count to 44 verified completed 12-round FL runs:
36 main-study runs plus eight KD schedule controls. Six central-only fits remain
separate. Earlier pilots and replays are excluded from this count.

Upstream preprocessing provenance, validation reuse, fixed data/master/attacker
identities, limited heterogeneity coverage and held-out-threat evaluation remain
limitations. Final test untouched; final protocol unfrozen.

Earlier seed: [kd_schedule_seed42_results.md](kd_schedule_seed42_results.md).
Protocol: [kd_schedule_controls.md](kd_schedule_controls.md).
Machine-readable audit and 216 trajectory records:
[audit.json](evidence/kd_schedule_seed31415_20261028/audit.json) and
[round_metrics.csv](evidence/kd_schedule_seed31415_20261028/round_metrics.csv).
