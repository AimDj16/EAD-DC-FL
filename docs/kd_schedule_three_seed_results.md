# Within-FL KD schedule controls: three-seed development results

Verified 28 October 2026. The control programme is complete: two additional KD
schedules, each benign and label-flipping attacked, across seeds 42, 2026 and
31415. This comprises 12 new 12-round FL runs and six reused original full-KD
references. The verified programme now contains 48 completed FL runs: 36 main-study
runs plus these 12 controls. Six earlier server-only reference fits are separate.
Earlier pilots, component tests and diagnostic replays are excluded from that count.

## Evidence and audit

| Seed | Uploaded archive | SHA256 |
|---|---|---|
| 42 | kd_schedule_seed42_v1_reports.tar.gz | d9e73c1416c416379ff1cea52d58063b1e77c98fe055d84ef046deeae76ca7ee |
| 2026 | kd_schedule_seed2026_v1_reports.tar.gz | 1766790026bfb1fe10c3862735c92bf692d89c05dbc4eb21545bf57b35d943fa |
| 31415 | kd_schedule_seed31415_v1_reports.tar.gz | 6521d93804f7836bc65ce3b534f39aea1869b54c327ba1f96a4962ebc916c170 |

All three archives pass report/source hashes, manifest identity, initial tensor
hashes, within-seed common fingerprints, participation/orders and original-reference
identity checks. Original full-KD reference reports are byte-identical to the earlier
main-study uploads. Every new control reproduces original round-1 pre-KD training
and screening records. Both warm-start-only runs per seed reproduce all original
round-1–3 cluster records and recorded checkpoint file hashes, with exact tensor
checks additionally reported by the UWE runtime. All summary values recompute
exactly. Teacher selection, calibration, strict voting, survivor sample weights,
recorded poisoning and KD acceptance/commitment are consistent across 648
round/architecture records.

These uploads contain aggregate reports, not checkpoint tensors, raw data, poison
arrays or per-example predictions. The assistant has not independently reloaded
those arrays. Report-level verification and runtime-recorded tensor checks must
remain distinguishable. The latest seed-2026 matched identifier is
738eb04c2f29842b2f67f38881d311dec66152e306b8a0dbc38cf0c09d9c5886.

## Fixed design and comparison boundaries

EAD is enabled and sample-weighted FedAvg operates within the same three MLP
architecture groups. All 30 clients participate. Within each seed, initial tensors,
data allocations, local training/order, malicious identities, poison rows, attack
timing, EAD settings, proxy features and validation rows match the original full-KD
reference. The original policy uses unconditional master KD in rounds 1–3, then an
adaptive cluster teacher with a validation-accuracy guard. warm_start_only stops KD
after round 3; adaptive_only uses guarded adaptive cluster KD from round 1 without
master teaching. Both variants retain their identities and do not replace the main
method. The pre-run protocol remains unchanged.

KD exposure intentionally differs. adaptive_only retains labelled validation for
teacher selection and acceptance; it is not a label-free server procedure. Its
early teacher identity, acceptance policy and recipient count differ from the
original master warm-start. Thus it is not a pure, compute-matched estimate of the
benefit supplied by labelled master pre-training.

## Targeted security: replicated result and seed dependence

Excess TMR is committed Malware-to-Normal error minus the same-round,
same-architecture benign value under the same policy. Entries below show the
largest positive excess in percentage points across all architectures and rounds
within a seed. They are descriptive observed peaks, not worst-case guarantees.

| KD schedule | Seed 42 | Seed 2026 | Seed 31415 |
|---|---|---|---|
| Original full KD | 0.00 | 0.00 | 0.00 |
| Master warm-start only | 0.00 | 0.00 | 0.00 |
| Adaptive KD without master teaching | 52.81 | 0.50 | 0.37 |

Both original full KD and warm-start-only match their own benign committed TMR at
every one of the 108 seed/architecture/round observations per policy. The absolute
final error remains 2/801 = 0.2497% for both policies. This is three run replications
per condition, not 108 independent replications. Matching an aggregate target rate
does not establish identical predictions, zero absolute errors or absence of other
poisoning effects.

The bounded negative finding is replicated: recurring KD after round 3 is not
required to reproduce that specific targeted-error result in these three evaluated
configurations. Master warm-start, EAD, FedAvg and local training remain. It is not
evidence that the master alone is sufficient, nor that later KD has no utility value.

The adaptive-only result is seed-dependent. Its per-architecture positive peaks are
Small/Medium/Deep 0.12/13.11/52.81 pp in seed 42, 0.12/0.50/0.12 pp in seed 2026,
and 0.12/0.37/0.12 pp in seed 31415. The latter two Medium peaks correspond to four
and three extra errors out of 801 Malware examples. These observations prevent a
universal master-necessity claim. Seeds vary initialisation, training order and
detector randomness, conditional on the same data partition, trusted master and
compromised identities.

## Endpoint utility and paired differences

Round-12 attacked validation macro-F1, mean ± sample standard deviation across the
three runs, in percentages. Architectures are analysed separately and are not
treated as independent replicates.

| KD schedule | Small | Medium | Deep |
|---|---|---|---|
| Original full KD | 83.80 ± 2.03 | 86.19 ± 2.52 | 84.13 ± 1.42 |
| Master warm-start only | 82.86 ± 2.36 | 83.87 ± 4.53 | 83.70 ± 1.01 |
| Adaptive only | 76.84 ± 1.99 | 79.03 ± 3.43 | 80.44 ± 5.59 |

Original full KD has higher mean attacked endpoint macro-F1 than either alternative
in every architecture, but per-seed comparisons differ. The appropriate paired
differences for full minus warm-start-only are:

| Architecture | Seed 42 | Seed 2026 | Seed 31415 | Mean ± sample SD |
|---|---|---|---|---|
| Small | +0.72 | −2.60 | +4.69 | +0.94 ± 3.65 pp |
| Medium | +3.48 | 0.00 | +3.49 | +2.32 ± 2.01 pp |
| Deep | −0.19 | −0.48 | +1.96 | +0.43 ± 1.33 pp |

These are descriptive paired effects from three seeds, not evidence of statistical
significance or universal improvements. Full KD improves attacked macro-F1 in five
of nine architecture/seed comparisons, decreases it in three, and ties in one.
Do not pool the nine comparisons into nine independent runs. Benign Deep mean
macro-F1 is 83.90% with full KD versus 84.41% with warm-start-only, another limit on
a universal utility claim.

In seed 2026, the attacked Medium model is selected as teacher in every adaptive
round and receives no KD after its three master phases. Its checkpoint hashes
match warm-start-only Medium in all 12 rounds; benign hashes also match, despite
one later rejected candidate when Deep is teacher. The zero paired endpoint
difference therefore reflects no committed KD change to that model. Scheduled
recurring KD must not be equated with a treatment received by every architecture.

## Security mechanisms and counterexamples

The three-seed record contains contrasting stage-specific KD outcomes:

- Seed 42, adaptive-only round 3: Deep teaches Medium; the accepted candidate
  increases accuracy 81.78% to 90.55% and macro-F1 78.52% to 80.05%, while targeted
  errors increase from 0 to 105/801. Accuracy protection is not security protection.
- Seed 31415, adaptive-only round 2: Medium teaches Deep; accepted KD reduces
  targeted errors from 101 to 1/801, while accuracy rises 75.51% to 77.34% and
  macro-F1 rises 67.67% to 70.03%. KD can improve the measured security outcome.
- Seed 42, adaptive-only round 7: Deep, the teacher in all 12 attacked rounds,
  skips self-KD and retains 424/801 targeted errors. Small and Medium candidates
  have 428 and 425 errors, but are rejected. Committed security alone would hide
  those harmful candidate models.
- Seed 2026, adaptive-only rounds 10 and 11: accepted Medium and Deep candidates
  each increase targeted errors from 1 to 2/801 while accuracy and macro-F1 improve.
  These are small additional counterexamples, not large attack-success claims.

Teacher and student counts are consistent with transfer effects, but do not identify
which examples share errors or prove the sole source of cross-seed differences.
The evidence supports examining screening, teacher choice, recipient eligibility,
KD outcomes and metric alignment together. It does not establish novelty merely
from combining EAD-FL and DC-FL.

## Screening and costs

Counts pool repeated client-round submissions across the three runs. Each attacked
policy has 324 malicious and 756 benign submissions; each clean policy has 1,080
benign submissions.

| KD schedule | Attack TP/FN/FP/TN | Clean FP/TN | Attack calibration triggers |
|---|---|---|---|
| Original full KD | 287/37/3/753 | 120/960 | 105/108 |
| Warm-start only | 287/37/3/753 | 131/949 | 105/108 |
| Adaptive only | 289/35/0/756 | 125/955 | 108/108 |

Equal pooled counts do not establish identical rejected-client identities. EAD
precedes current-round KD; later differences arise on different trajectories.
Clean false rejection remains about 11–12%. Higher calibration frequency is not
itself evidence of better security or valid thresholds under benign heterogeneity.

The 12 additional controls record 27,653.91 seconds, approximately 7.68 hours.
This excludes the six reused main references and inherited master pre-training.
Training candidate models incurs cost even when they are rejected. Different KD
exposure and aggregated run times do not provide a compute-matched efficiency or
memory/communication benchmark.

## Decision and permissible thesis argument

Close this control programme without adding more schedule variants or repeating
completed runs. Preserve the original full-KD implementation as the main method
and the two alternatives as ablations. No final-test-based variant selection has
occurred. The completed package strengthens the following argument:

> Poisoning resilience in the tested heterogeneous FL pipeline depends on the
> interaction of screening, trusted supervision and knowledge transfer. Recurring
> KD was unnecessary to reproduce the measured targeted-error protection after
> master warm-start, but changed utility and training trajectories. Adaptive KD
> without master teaching had seed-dependent security outcomes. Accepted general
> metric improvements did not guarantee protection of targeted behaviour.

Chapter 4 should report the controlled design, source/variant identity, replicated
targeted result, paired utility trade-offs and stage-specific failures/recoveries.
Chapter 5 should distinguish master supervision, recurring transfer, teacher
self-skipping and the mismatch between acceptance and security metrics. These
are useful empirical and negative findings, not universal robustness guarantees.

The next step is to consolidate these results and predeclare the remaining final
evaluation, including independent held-out reporting under an explicitly qualified
processed-data protocol. Do not use final-test outcomes for attack tuning, policy
selection or checkpoint selection. Upstream preprocessing provenance remains
unverified. Statistical heterogeneity, partial participation, held-out/adaptive
threats, proxy dependence and fuller costs remain limitations or separately
prioritised thesis work. This completed development/control block does not establish
that the full PhD evaluation is finished. Final test untouched; final protocol unfrozen.

## Files

Pre-run protocol: [kd_schedule_controls.md](kd_schedule_controls.md).
Earlier detailed reports: [seed 42](kd_schedule_seed42_results.md) and
[seed 31415](kd_schedule_seed31415_results.md).
Combined checks and descriptive summaries:
[audit.json](evidence/kd_schedule_three_seed_20261028/audit.json) and
[mean_sample_sd.csv](evidence/kd_schedule_three_seed_20261028/mean_sample_sd.csv).
Seed-2026 round-level records:
[round_metrics.csv](evidence/kd_schedule_seed2026_20261028/round_metrics.csv).
