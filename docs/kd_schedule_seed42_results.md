# Within-FL KD schedule controls: seed-42 results

Verified 28 October 2026 from kd_schedule_seed42_v1_reports.tar.gz, SHA256
d9e73c1416c416379ff1cea52d58063b1e77c98fe055d84ef046deeae76ca7ee.
Four new 12-round FL controls and two reused original full-KD references, all with
EAD enabled, sample-weighted FedAvg and the existing seed-42 matched contract.
The main development package remains 36 runs, with these four additional controls.

## Verification and limits of inspection

Archive checksum matches the user's terminal output. All six report hashes match
the bundle summary. The bundled runner, policy module and batch source match the
prepared source. The two original reference reports are byte-identical to their
previously uploaded archives. The manifest identifier, initial tensor hashes,
matched fingerprints, local orders and participation records agree across all six
reports. The full summary was independently recomputed exactly.

For every new control, round-1 pre-KD training and screening records match the
original same-arm reference. For both warm-start-only controls, all round-1–3
cluster records and recorded checkpoint file hashes match the original references;
the runtime additionally reports exact tensor replay. No checkpoint arrays are in
this upload, so the assistant has not independently reloaded them. Raw data,
poison-label arrays and per-example validation predictions are also absent.

Across 216 round/architecture records, detector voting/calibration, survivor sample
weights, attack row counts, teacher selection and KD commitment records are
consistent. Targeted errors use 801 clean Malware validation examples. The attack
logs record 1,497 local label changes each round, across the same nine compromised
clients, three per architecture. No final-test evaluation occurred.

## Security trajectories

Excess TMR is the committed Malware-to-Normal error rate minus the same-round,
same-architecture benign rate under the same KD policy. Entries below are the
largest positive excess over the 12 rounds, in percentage points. These are
descriptive peaks from one seed, not statistical worst-case guarantees.

| KD schedule | Small | Medium | Deep |
|---|---|---|---|
| Original master warm-start plus recurring adaptive KD | 0.00 | 0.00 | 0.00 |
| Master warm-start only, no KD after round 3 | 0.00 | 0.00 | 0.00 |
| Adaptive cluster KD from round 1, no master teaching | 0.12 | 13.11 | 52.81 |

The original and warm-start-only policies each match their own benign committed
TMR in all 36 architecture/round observations. Absolute errors remain, including
2/801 = 0.2497% in every final model under these two policies. Zero excess TMR
does not establish identical predictions, zero absolute error or absence of other
poisoning effects.

The key negative finding is that recurring KD after round 3 is not required to
reproduce the original policy's observed targeted-error protection in this
seed-42 configuration. Master warm-start, EAD, FedAvg and subsequent local
training remain present. This does not establish that the master alone is
sufficient or that later KD has no utility benefit.

The no-master-teaching control loses that trajectory-level protection. Its Deep
model is the selected teacher in all 12 attacked rounds, so it skips self-KD and
receives no distillation. Its recorded checkpoint hashes match the earlier EAD-only
Deep model at every round. Benign Deep checkpoint hashes also match the earlier
EAD-only trajectory. In attacked round 7, all three Deep attackers survive, with
424/801 targeted errors versus 1/801 in its benign counterpart, yielding 52.81 pp
excess. This also exposes the limitation of a teacher that is never itself a KD
recipient, rather than establishing that all models benefit from adaptive KD.

## Accepted KD can worsen targeted security

In adaptive-only round 3, Deep teaches Medium:

| Stage | Accuracy | Macro-F1 | Malware-to-Normal errors |
|---|---|---|---|
| Medium before KD | 81.78% | 78.52% | 0/801 |
| Medium KD candidate, accepted | 90.55% | 80.05% | 105/801 |

The teacher has 89/801 targeted errors before KD. Medium's accuracy rises 8.78 pp
and macro-F1 rises 1.53 pp, while targeted error increases 13.11 pp. The candidate
is accepted under the stated accuracy guard. The benign Medium post-KD value is
0/801 in the same round. This directly records security deterioration during an
accepted KD step, consistent with transfer from an unreliable teacher. Aggregate
counts do not prove which individual examples share the teacher's error pattern.

In round 7, the same attacked teacher produces candidates with 428 Small and 425
Medium targeted errors, but both are rejected because accuracy falls. Small and
Medium committed target counts remain zero while Deep retains 424. Gate protection
is therefore conditional on the accompanying accuracy change, not guaranteed by
the acceptance mechanism.

## Endpoint utility and trade-offs

Round-12 attacked validation accuracy / macro-F1, percentages:

| KD schedule | Small | Medium | Deep |
|---|---|---|---|
| Original full KD | 86.38 / 85.11 | 86.01 / 84.66 | 86.01 / 84.66 |
| Warm-start only | 85.22 / 84.39 | 83.76 / 81.19 | 85.87 / 84.86 |
| Adaptive only | 83.53 / 75.89 | 84.95 / 82.31 | 94.05 / 86.41 |

Original full KD has higher final accuracy than warm-start-only in all three
architectures, with higher Small/Medium macro-F1 and slightly lower Deep macro-F1.
Adaptive-only Deep has the highest final accuracy/macro-F1 despite its large
earlier targeted failure. Final utility and trajectory security support different
rankings. These data do not justify universal superiority or choosing the best
schedule retrospectively.

Warm-start-only Medium final macro-F1 is 81.19% under attack versus 84.82% benign,
despite identical TMR. Protection of one target transition is not protection of
all classes or utility metrics.

## Screening and costs

Counts pool repeated submissions, not independent replications. Each attacked
condition has 108 malicious and 252 benign submissions; each clean condition has
360 benign submissions.

| KD schedule | Attack TP/FN/FP/TN | Clean FP/TN |
|---|---|---|
| Original full KD | 100/8/0/252 | 37/323 |
| Warm-start only | 101/7/0/252 | 40/320 |
| Adaptive only | 95/13/0/252 | 42/318 |

All 36 attacked architecture/rounds trigger calibration in each policy. Differing
screening outcomes occur on later model trajectories, since EAD precedes KD.
Calibration activation is not proof that all malicious uploads are excluded.

The four new runs record 8,998.01 seconds, approximately 2.50 hours in total.
Warm-start-only performs three KD phases per model, or 270,432 feature
presentations. Adaptive-only attacked Small and Medium each perform 12 phases,
1,081,728 presentations, while Deep performs none. Rejected candidate training
still incurs cost. These are different KD exposures, not compute-matched controls
or an isolated component efficiency benchmark. Original master-pretraining cost
is inherited and excluded from these run times.

## Claims and next decision

The tested master warm-start schedule is a plausible contributor to the original
configuration's targeted-error protection. Later adaptive KD is unnecessary for
reproducing that specific security result in this one seed, while some endpoint
utility comparisons favour retaining it. Removing master teaching changes early
teacher identities, acceptance rules and KD exposure; it does not isolate a pure
labelled-data effect. Adaptive-only still uses labelled server validation.

Retain the original policy as the main registered development method. Treat the
alternatives as ablations, not a new defence or a retrospective replacement.
Replicate the same four controls with existing seed-2026 and seed-31415 contracts
before claiming a stable effect. This is eight additional runs, without a new
factorial sweep or new tuning. Use each policy's own benign reference. If the
result does not replicate, report the seed dependence rather than selecting the
favourable configuration.

Chapter 4 should report this source of protection and the accepted-KD failure.
Chapter 5 should distinguish master supervision, recurring transfer, teacher
self-skipping and utility/security trade-offs. This strengthens the thesis
through a bounded mechanism study and a useful negative finding. Statistical
heterogeneity, partial participation, held-out threats, validation reuse and
unverified upstream preprocessing remain separate limitations. The final
protocol is not frozen and the final test remains untouched.

Protocol: [kd_schedule_controls.md](kd_schedule_controls.md).
Machine-readable checks and trajectories:
[audit.json](evidence/kd_schedule_seed42_20261028/audit.json) and
[round_metrics.csv](evidence/kd_schedule_seed42_20261028/round_metrics.csv).
