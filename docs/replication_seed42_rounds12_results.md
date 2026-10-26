# Twelve-round matched Gaussian development results, seed 42

Inspected on 26 October 2026. Evidence: uploaded archive `replication_seed42_rounds12_reports.tar.gz`, containing one manifest and eight report.json files. Experiment ID: `33fc67b96cead72110ff9613e42c2c9e9f127f56fec055555bc03f6a902fd9dd`.

## Scope and implementation

This is a completed development comparison, not final protocol freezing or final-test evaluation. The four component conditions are crossed with matched benign and Gaussian attack arms. All use sample-weighted FedAvg within architecture groups, 30 clients with ten per architecture, full participation and seed 42. Nine clients are compromised in attack runs, three per group. Gaussian noise at exploratory sigma 0.5 is added to locally trained submitted model tensors each round. This is one fixed threat and training seed, conditional on fixed data allocations, master checkpoint and compromised-client identities.

The working EAD configuration uses LOF, Isolation Forest and KNN, strict unanimous voting, predict/decision_function on the fitted cohort, and count-disagreement calibration reset each round from 0.20 to 0.30 on a trigger. This must remain distinguishable from historical fitted-label pilots and legacy notebook variants. Original KD unconditionally commits master warm-start candidates in rounds 1–3 and uses adaptive cluster teachers with an accuracy acceptance guard thereafter. Guarded warm-start is a separate variant, absent from this batch.

All metrics below are server-validation metrics, on data also used for teacher selection and acceptance. They do not establish independent-test performance.

## Verification performed

- All eight reports have status completed and ordered rounds 1–12; all eight EAD/KD/arm combinations are present.
- Recomputed the canonical manifest identifier. Compared the existing matched-report fingerprint across all eight runs: initial tensor hashes, data/master/model hashes, training settings, execution environment, actual participation and local training-order hashes match.
- Initial tensor hashes agree with the manifest; all report runner hashes agree with the manifest's registered runner hash.
- Accepted IDs, sample counts and survivor-renormalised FedAvg coefficients are consistent with the manifest. Upload poisoning flags and screening audit sets are internally consistent.
- First four rounds in all eight runs match their corresponding earlier four-round reports for teacher choices, participation, local order/loss records, screening records, rejected IDs, pre/post KD metrics, KD records and recorded checkpoint file hashes.
- The attack EAD-on/KD-off report also records four successful runtime exact-prefix checks. The uploaded archive contains JSON, not checkpoint arrays; checkpoint tensors were not independently reloaded here.
- All reports record test_evaluated=false, final_protocol_frozen=false and preprocessing_provenance_verified=false.

## Round-12 outcomes

Entries are accuracy / macro-F1, percentages. Columns identify architecture groups, not independent replications.

| Arm | Condition | Small | Medium | Deep |
|---|---|---|---|---|
| benign | FedAvg | 96.64 / 88.91 | 86.01 / 83.79 | 95.50 / 87.83 |
| benign | EAD + FedAvg | 96.64 / 88.67 | 83.76 / 75.68 | 94.75 / 87.08 |
| benign | KD + FedAvg | 86.43 / 85.43 | 86.12 / 85.39 | 85.99 / 85.11 |
| benign | EAD + KD + FedAvg | 86.37 / 85.52 | 86.13 / 85.28 | 86.01 / 85.18 |
| attack | FedAvg | 77.61 / 48.84 | 68.42 / 41.70 | 35.18 / 27.25 |
| attack | EAD + FedAvg | 96.68 / 88.93 | 83.62 / 78.95 | 90.68 / 79.00 |
| attack | KD + FedAvg | 92.03 / 82.89 | 88.62 / 70.97 | 87.08 / 68.13 |
| attack | EAD + KD + FedAvg | 86.28 / 85.27 | 86.08 / 85.24 | 86.68 / 85.65 |

## Screening and calibration

Each screened attack run contains 108 malicious and 252 benign client-round submissions. EAD without KD: TP108, FN0, FP0, TN252. EAD with KD: TP108, FN0, FP0, TN252. Calibration triggers in all 36 architecture-rounds in each attack run. Thus every poisoned submission is excluded from the aggregation inputs in these checked runs. These are repeated observations from one trajectory, not 108 independent experimental replications. This does not validate performance at other strengths, malicious ratios, heterogeneous data partitions or held-out threats.

In the clean controls:
- EAD without KD rejects 42/360 benign submissions (11.67%), with 318 accepted; calibration triggers 22/36 architecture-rounds.
- EAD with KD rejects 37/360 benign submissions (10.28%), with 323 accepted; calibration triggers 25/36 architecture-rounds.

These rates remain material under IID data. No claim that benign diversity is preserved is justified. For example, clean Medium EAD-only final macro-F1 is 75.67%, versus 83.79% with FedAvg alone; Medium MITM recall is 62.22%, versus 100%. Different retained contributors and later models form part of the treatment, so the attack/benign difference is not an estimate of residual poisoned uploads alone.

## Horizon dependence and KD

Combined EAD/KD attack Small accuracy/macro-F1 at rounds 4, 8 and 12 is 69.88/61.70%, 93.66/88.19% and 86.28/85.27%. The severe four-round deficit is not a stable estimate of its later performance. Round 9 accuracy falls to 83.03%, after 93.66% at round 8. Do not select the best round retrospectively or claim convergence from 12 rounds.

At round 12 under attack, EAD-only is stronger than the combined method on Small accuracy and macro-F1. Adding KD to EAD improves Medium and Deep macro-F1, but Deep accuracy falls from 90.68% to 86.68%. KD-only has higher Medium accuracy than the combined method, but lower macro-F1. No configuration uniformly dominates across architectures and metrics.

An accepted KD candidate can lower macro-F1 while raising the guarded validation accuracy. In the combined attack run, round-4 Small accuracy rises by 1.20 percentage points while macro-F1 falls by 7.03 points; Deep accuracy rises by 2.74 points while macro-F1 falls by 10.78 points. The latter rounds use the accuracy guard, so this is a direct limitation of its protected metric. Original warm-start also commits accuracy losses in rounds 1–3 by design. Security protection cannot be inferred from the accuracy acceptance rule.

Perfect screening means the combined trajectory cannot be explained by poisoned tensors surviving aggregation in these Gaussian runs. The earlier four-round clean reference-mask diagnostic supplies a narrower attribution control; it has not been extended to all 12 rounds. Do not claim a new 12-round counterfactual replay was performed.

## Measured execution time

Reported elapsed time totals 169.9 minutes, approximately 2 hours 50 minutes, across eight sequential runs. Individual runs:
- benign, FedAvg: 3.9 minutes.
- benign, EAD + FedAvg: 32.0 minutes.
- benign, KD + FedAvg: 6.6 minutes.
- benign, EAD + KD + FedAvg: 36.6 minutes.
- attack, FedAvg: 4.0 minutes.
- attack, EAD + FedAvg: 39.0 minutes.
- attack, KD + FedAvg: 6.6 minutes.
- attack, EAD + KD + FedAvg: 41.1 minutes.

Screening runs take about 32–41 minutes, versus 4–7 minutes without screening in this environment. This is an implementation-level elapsed-time observation, including logging/checkpoint overhead, not an optimised detector benchmark. No peak-memory or communication measurement is provided in this archive.

## Permissible thesis interpretation

The longer matched development comparison supports the conditional claim that revised EAD screening can exclude this strong Gaussian attack while introducing benign rejection, and that cross-architecture KD changes the resulting utility trajectory in an architecture- and metric-dependent manner. Detector fidelity, benign costs, trusted server supervision and KD acceptance must be evaluated separately. It does not support universal robustness, combined-method superiority, generalisation, formal privacy or novelty by combination.

This evidence belongs in Chapter 4's integration evaluation, with Chapter 5 synthesis discussing security/utility misalignment. It does not replace Chapter 3's frozen heterogeneity-impact questions. Integration H_S variation and H_P are still absent.

## Next bounded decision

Preserve this horizon, sigma and original KD policy for the next two training/noise seeds, 2026 and 31415. Run the same eight benign/Gaussian cells for each. This adds 16 runs, approximately 5 hours 40 minutes at the observed batch runtime, subject to workload and hardware variability. Treat runs as independent stochastic replications conditional on the same split, master and compromised IDs; clients and rounds are not replication units. Report individual seed outcomes and paired component/attack contrasts. Three seeds provide an initial repeatability check, not strong population-level uncertainty estimates.

Do not change the method to favour seed-42 outcomes. Keep targeted label-flipping findings separate, since the new 12-round archive contains no targeted runs. After these replications, decide whether repeated utility trade-offs justify a targeted extension or the guarded-policy comparison. Broader attacks, independent evaluation, proxy/master controls, H_S/H_P and data provenance remain outstanding.

Commands, from the repository root in the activated GPU environment:

```bash
python scripts/prepare_matched_replication.py --seed 2026 --rounds 12 --output data/experiments/idsiot2024/replication_seed2026_rounds12_v1
python -u scripts/run_replication_batch.py --matched-experiment data/experiments/idsiot2024/replication_seed2026_rounds12_v1 --scenarios benign gaussian
python scripts/prepare_matched_replication.py --seed 31415 --rounds 12 --output data/experiments/idsiot2024/replication_seed31415_rounds12_v1
python -u scripts/run_replication_batch.py --matched-experiment data/experiments/idsiot2024/replication_seed31415_rounds12_v1 --scenarios benign gaussian
```
