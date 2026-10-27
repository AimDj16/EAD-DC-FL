# Three-seed twelve-round matched Gaussian development evaluation

Inspected 27 October 2026. This record extends the seed-42 analysis without replacing its historical interpretation.

## Evidence and scope

Sources:
- `replication_seed42_rounds12_reports.tar.gz`, SHA256 `47631930a587d62a3a6abc7eca8895e143605e25e396af0c3ad07b081fd0ec97`.
- `replication_additional_seeds_rounds12_reports.tar.gz`, SHA256 `3e3502db6d4102ff389ba64e7338c8056265c91c1d48a9ed04ae2966998c0e37`.

The archives contain three experiment manifests and 24 completed reports: seeds 42, 2026 and 31415, each with four EAD/KD component conditions crossed with benign/Gaussian attack arms. Each run has 12 global rounds. Recorded experiment IDs:
- Seed 42: `33fc67b96cead72110ff9613e42c2c9e9f127f56fec055555bc03f6a902fd9dd`.
- Seed 2026: `738eb04c2f29842b2f67f38881d311dec66152e306b8a0dbc38cf0c09d9c5886`.
- Seed 31415: `681c3b44d178754c04d1fc20581b80782caf3ec15e9769fc5fa0481e8ca3983d`.

This is conditional stochastic replication: initialisation, local training and Gaussian-noise seeds vary; the data partition, client allocations, pre-trained master, compromised identities, architecture registry, training budgets and participation schedule remain fixed. EAD's seeded components also follow the training seed. This does not replicate datasets, data partitions, server pre-training or malicious-set selection.

Methods remain unchanged: sample-weighted FedAvg within Small/Medium/Deep groups; ten clients per group; full participation; three compromised clients per group in attack runs; Gaussian full-model additive noise at exploratory sigma 0.5 every round. Working EAD uses LOF/Isolation Forest/KNN, strict unanimous voting, predict/decision_function on the fitted cohort and count-disagreement calibration from0.20 to0.30, reset per group/round. Original KD unconditionally commits master warm-start in rounds1–3, then selects a cluster teacher and applies the validation-accuracy acceptance guard. The guarded warm-start variant is not included.

## Verification

The analysis used the existing matched-report fingerprint, recomputed canonical manifest IDs and additional direct consistency checks:
- All24 reports completed ordered rounds1–12. All eight component/arm cells are present for each seed.
- Within each seed, initial tensor hashes, data/master/model hashes, budgets, execution environment, actual participants and local training-order hashes match. Initial hashes agree with their manifest.
- Across seeds, registered input hashes, client counts, full participation, training budgets, runtime environment, fixed master/data/compromised-selection metadata, EAD configuration and runner source hash match. Noise seeds equal training seed+200.
- Actual active compromised cohorts contain3/10 clients per architecture each attack round. Gaussian sigma is0.5 in every attack report.
- Accepted IDs/sample counts and survivor-renormalised FedAvg coefficients are internally consistent.
- Upload poisoning flags and TP/FN/FP/TN audit sets agree. Recomputed strict votes from the three final detector flag arrays reproduce the rejected IDs.
- Calibration triggers agree with unequal initial detector flagged counts; recorded final contamination is0.30 when triggered and0.20 otherwise.
- KD committed metrics equal candidate metrics on acceptance and pre-KD metrics on rejection. All adaptive decisions agree with candidate accuracy>=pre-KD accuracy; performed warm-start candidates are unconditionally accepted.
- All reports retain test_evaluated=false and final_protocol_frozen=false. Preprocessing provenance remains unresolved.
- These are checks of uploaded JSON and inspected source. Checkpoint arrays and original data files were not uploaded in these result archives, so they were not independently reloaded here.

The seed-42 first-four-round comparisons and runtime prefix checks are documented separately. No claim of exact repeats across different training seeds is made or expected.

## Round-12 validation outcomes

Mean ± sample standard deviation across three runs, expressed in percent/percentage points. These are descriptive run-to-run summaries, not confidence intervals. The server validation data are also used for teacher selection and acceptance. No independent-test inference follows.

### Gaussian attack, macro-F1

| Method | Small | Medium | Deep |
|---|---|---|---|
| FedAvg | 53.73 ± 5.09 | 43.32 ± 12.06 | 40.38 ± 11.83 |
| EAD + FedAvg | 79.36 ± 8.28 | 76.32 ± 2.62 | 77.98 ± 1.25 |
| KD + FedAvg | 78.70 ± 3.98 | 64.81 ± 7.29 | 65.70 ± 4.77 |
| EAD + KD + FedAvg | 84.88 ± 0.45 | 85.19 ± 0.18 | 85.15 ± 1.17 |

### Gaussian attack, accuracy

| Method | Small | Medium | Deep |
|---|---|---|---|
| FedAvg | 76.50 ± 6.51 | 59.27 ± 10.59 | 55.50 ± 17.78 |
| EAD + FedAvg | 86.46 ± 8.86 | 82.10 ± 1.55 | 84.69 ± 5.20 |
| KD + FedAvg | 90.48 ± 1.52 | 83.60 ± 6.46 | 85.69 ± 1.70 |
| EAD + KD + FedAvg | 86.10 ± 0.26 | 86.08 ± 0.03 | 86.58 ± 0.46 |

### Benign controls, macro-F1

| Method | Small | Medium | Deep |
|---|---|---|---|
| FedAvg | 80.81 ± 7.30 | 78.85 ± 4.67 | 80.90 ± 6.04 |
| EAD + FedAvg | 79.41 ± 8.02 | 76.28 ± 1.37 | 80.66 ± 5.66 |
| KD + FedAvg | 84.56 ± 1.27 | 85.29 ± 0.15 | 84.96 ± 1.13 |
| EAD + KD + FedAvg | 83.90 ± 2.29 | 86.51 ± 2.33 | 83.90 ± 1.24 |

### Individual outcomes

Entries are accuracy / macro-F1, percentages. Preserve these values alongside means because n=3 is small.

| Seed | Arm | Method | Small | Medium | Deep |
|---|---|---|---|---|---|
| 42 | benign | FedAvg | 96.64 / 88.91 | 86.01 / 83.79 | 95.50 / 87.83 |
| 42 | benign | EAD + FedAvg | 96.64 / 88.67 | 83.76 / 75.68 | 94.75 / 87.08 |
| 42 | benign | KD + FedAvg | 86.43 / 85.43 | 86.12 / 85.39 | 85.99 / 85.11 |
| 42 | benign | EAD + KD + FedAvg | 86.37 / 85.52 | 86.13 / 85.28 | 86.01 / 85.18 |
| 42 | attack | FedAvg | 77.61 / 48.84 | 68.42 / 41.70 | 35.18 / 27.25 |
| 42 | attack | EAD + FedAvg | 96.68 / 88.93 | 83.62 / 78.95 | 90.68 / 79.00 |
| 42 | attack | KD + FedAvg | 92.03 / 82.89 | 88.62 / 70.97 | 87.08 / 68.13 |
| 42 | attack | EAD + KD + FedAvg | 86.28 / 85.27 | 86.08 / 85.24 | 86.68 / 85.65 |
| 2026 | benign | FedAvg | 81.39 / 74.74 | 83.42 / 78.25 | 81.70 / 78.13 |
| 2026 | benign | EAD + FedAvg | 81.34 / 74.70 | 83.29 / 77.85 | 81.76 / 78.48 |
| 2026 | benign | KD + FedAvg | 86.34 / 85.14 | 86.18 / 85.36 | 86.91 / 86.01 |
| 2026 | benign | EAD + KD + FedAvg | 83.49 / 81.28 | 94.80 / 89.20 | 85.22 / 82.71 |
| 2026 | attack | FedAvg | 69.51 / 53.36 | 47.67 / 32.14 | 63.11 / 50.21 |
| 2026 | attack | EAD + FedAvg | 81.42 / 74.75 | 82.14 / 76.30 | 82.01 / 78.36 |
| 2026 | attack | KD + FedAvg | 88.99 / 78.25 | 85.87 / 66.70 | 86.21 / 68.78 |
| 2026 | attack | EAD + KD + FedAvg | 86.22 / 84.99 | 86.12 / 85.34 | 86.97 / 85.99 |
| 31415 | benign | FedAvg | 83.49 / 78.76 | 81.61 / 74.52 | 81.32 / 76.75 |
| 31415 | benign | EAD + FedAvg | 81.71 / 74.87 | 81.55 / 75.33 | 81.20 / 76.41 |
| 31415 | benign | KD + FedAvg | 83.96 / 83.11 | 86.07 / 85.12 | 86.09 / 83.76 |
| 31415 | benign | EAD + KD + FedAvg | 86.05 / 84.91 | 86.11 / 85.05 | 86.21 / 83.81 |
| 31415 | attack | FedAvg | 82.38 / 59.00 | 61.71 / 56.11 | 68.22 / 43.67 |
| 31415 | attack | EAD + FedAvg | 81.26 / 74.41 | 80.53 / 73.72 | 81.38 / 76.59 |
| 31415 | attack | KD + FedAvg | 90.42 / 74.97 | 76.32 / 56.76 | 83.79 / 60.20 |
| 31415 | attack | EAD + KD + FedAvg | 85.80 / 84.39 | 86.05 / 84.99 | 86.08 / 83.81 |

## Screening counts and benign costs

| Seed | Condition | Attack TP / FN / FP / TN | Clean FP / benign submissions | Clean calibration triggers |
|---|---|---|---|---|
| 42 | EAD, KD off | 108 / 0 / 0 / 252 | 42 / 360 | 22 / 36 |
| 42 | EAD, KD on | 108 / 0 / 0 / 252 | 37 / 360 | 25 / 36 |
| 2026 | EAD, KD off | 108 / 0 / 0 / 252 | 48 / 360 | 18 / 36 |
| 2026 | EAD, KD on | 108 / 0 / 0 / 252 | 49 / 360 | 24 / 36 |
| 31415 | EAD, KD off | 108 / 0 / 0 / 252 | 46 / 360 | 21 / 36 |
| 31415 | EAD, KD on | 108 / 0 / 0 / 252 | 34 / 360 | 31 / 36 |

For each screened condition, pooled attack counts are TP324/FN0/FP0/TN756, with calibration108/108 architecture-rounds. These are repeated client-round submissions from three runs. They are not324 independent security replications, and pooling does not increase the replication count beyond three runs per condition.

Clean EAD-only rejects136/1080 benign submissions (12.59%); clean EAD/KD rejects120/1080 (11.11%). These are malicious-client detector false positives, not IDS false alarm rates. Benign calibration triggers61/108 without KD and80/108 with KD. Thus a count-disagreement trigger is not specific to attack presence or a known malicious fraction.

The Gaussian perturbations are large. In the screened runs, recorded noise-to-model L2 ratios span approximately2.86–7.29, varying by architecture, seed and training state. This is a strong, conspicuous perturbation regime; complete screening here is not evidence of stealthy/adaptive robustness. Equal per-coordinate sigma does not equalise total or model-relative perturbation severity across differently sized architectures.

## Paired component contrasts

For each architecture, seed order is42,2026,31415. Positive values mean adding KD to EAD improves the round12 metric. Units are percentage points.

| Architecture | Accuracy change, three seeds | Macro-F1 change, three seeds |
|---|---|---|
| small | -10.41, 4.80, 4.54 | -3.66, 10.23, 9.97 |
| medium | 2.46, 3.97, 5.53 | 6.29, 9.04, 11.27 |
| deep | -4.00, 4.96, 4.70 | 6.65, 7.63, 7.22 |

Interpretation:
- EAD-only improves attack macro-F1 over unprotected FedAvg in all nine seed/architecture comparisons. Small accuracy is lower in seed31415, despite the macro-F1 benefit, so avoid an all-metrics superiority claim.
- Adding KD to EAD improves Medium and Deep attack macro-F1 in every seed. Small improves in two seeds and declines in seed42. The seed42 Small/Deep accuracy losses do not repeat in both later seeds.
- The combined method has the highest descriptive mean attack macro-F1 for every architecture among these four methods at the fixed12round endpoint. It is not uniformly best in accuracy or individual runs, and three seeds do not establish broad statistical superiority.
- Lower observed macro-F1 variability for the combined method is a descriptive result conditional on the shared server supervision. It is not a robustness guarantee or proof of a single cause.
- Clean EAD rejection costs persist. Benign utility changes are seed- and class-dependent. The clean Medium seed42 macro-F1 loss remains8.12points, although the other seeds show smaller loss or a modest gain.
- No poisoned uploads survive screened Gaussian aggregation in the reports. Remaining attack/benign differences include retained contributors, false rejections and their later training/KD trajectories. A12round clean-mask replay has not been run, so do not claim its counterfactual equivalence.

## Accuracy guard limitations

Accepted adaptive KD candidates reduce macro-F1 in all three seeds in the combined attack condition. Examples:
- Seed42, round4 Small: accuracy+1.20pp, macro-F1-7.03pp; Deep: accuracy+2.74pp, macro-F1-10.78pp.
- Seed2026, round8 Medium: accuracy+0.25pp, macro-F1-0.47pp.
- Seed31415, round5 Deep: accuracy+5.59pp, macro-F1-2.69pp.

This directly reproduces the limitation that protecting current validation accuracy does not protect macro-F1. It does not imply every KD step is harmful. Original warm-start is intentionally unguarded. Avoid the unqualified label no-harm without identifying the metric, phase and validation set.

Final combined attack Injection recall is about48–52%, and DoS recall about73–74%, despite mean macro-F1 near85%. Perfect client detection is not perfect IDS performance. Security and per-class utility must remain separate outcomes.

## Evidence strength for the thesis

Supported conditional wording:

> Across three training and noise seeds on a fixed IID partition, EAD excluded all submitted Gaussian-poisoned models in the evaluated sigma0.5 setting. Screening also rejected benign submissions in clean controls. Adding cross-architecture KD improved mean validation macro-F1, with architecture- and seed-dependent changes in accuracy and a seed-dependent benefit for Small. Accuracy-based acceptance did not consistently preserve macro-F1.

This is repeated development evidence for Chapter4's integration study, supporting the argument that screening, aggregation and knowledge transfer must be evaluated jointly. Chapter5 can synthesise benign rejection, metric misalignment and server-supervision dependence. It does not replace Chapter3's frozen heterogeneity-impact questions, or establish non-IID/H_P behaviour.

Outstanding: independent evaluation, data provenance, alternative partitions/datasets, proxy/master supervision controls, statistical and participation heterogeneity, detector/ensemble ablations, stronger/held-out/adaptive threats, other aggregators, full efficiency accounting and original-source fidelity qualifications. No novelty by combination or formal privacy claim follows.

## Runtime

Recorded elapsed time per eight-cell batch: seed42 169.9min; seed2026 163.3min; seed31415 171.5min. Total approximately8.41hours. These include execution/logging/checkpoint costs and are not detector microbenchmarks.

## Next bounded experiment and stopping rule

The three-seed Gaussian development package is complete. Do not add Gaussian seeds or alter thresholds/gates in response to these outcomes before the viva package is consolidated.

Recommended next: four targeted-attack component conditions at12rounds for each existing seed,12new runs total. Reuse the12existing benign controls. The unified runner branches into label poisoning only for active targeted attack clients; all benign training uses original labels and no model noise. The saved protocol relabels each compromised client's Malware rows to Normal, preserving features and other labels. Keep malicious identities, original KD policy, shared initial weights/data/cohorts and final12round endpoint unchanged. Sigma0 is required for targeted runs because this attack changes labels, not Gaussian model noise.

Why: the Gaussian perturbations are conspicuous, whereas earlier four-round revised EAD targeted runs missed malicious submissions. Matched12round, three-seed targeted evaluation tests threat dependence and separates transient targeted effects from final recovery without changing the method.

Pre-specify reporting before inspecting these new results: final12round accuracy/macro-F1/per-class recall; screening confusion counts; per-round pre/post KD Malware-to-Normal TMR against the same-seed, same-component benign trajectory; per-run mean and maximum excess TMR over the12round horizon. Use independent runs for between-seed summaries, not clients or rounds. Report both final and transient targeted effects. Do not select best checkpoints or retune on final-test outcomes.

Estimated12run runtime is roughly4–5hours, based on the existing attack-condition totals; label-flipping detector calibration may change timing. After this bounded extension, stop adding experimental conditions for the current viva package, archive the evidence and prepare Chapter4 tables, trajectories, limitations and viva explanations. The overall thesis evaluation remains incomplete.

Run in the existing activated GPU environment:

```bash
for run_seed in 42 2026 31415
do
    python -u scripts/run_replication_batch.py \
        --matched-experiment "data/experiments/idsiot2024/replication_seed${run_seed}_rounds12_v1" \
        --scenarios targeted
done
```

For unattended execution, wrap the same loop with nohup and set -eu as in the established queue. No runner/manifest-bound source changes are required.
