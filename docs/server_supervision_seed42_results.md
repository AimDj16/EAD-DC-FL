# Server supervision references: seed42 results

Verified28October2026 from server_supervision_seed42_v1_report.tar.gz, SHA2564f095710326682c024331797d4ecbe84b4244544611a1cd04f497d0030bb0d65. This is one seed, one master, one partition and six isolated reference fits, additional to the36matched FL runs.

## Verification

Report status completed; expected six reference conditions present; report script hash matches the inspected audit source. Initial tensors match the seed42 manifest, and hashes/final metrics for all four benign reference reports match the previously uploaded main archive. Confusion matrices independently reproduce accuracy, macro-F1, class support, Malware-to-Normal counts and Normal false alarms for the master and all initial/final student evaluations.

All six top-level partition pairs have zero exact-feature-group overlap. Recomputed client-training-only scaler statistics match within the predeclared numerical tolerances (maximum mean difference1.74e-13, scale difference1.42e-12). This confirms the additional scaler's fitting partition, not unavailable upstream processing.

Saved master validation accuracy, macro-F1 and per-class recalls reproduce exactly as reported: accuracy65.47%, macro-F164.68%. The runtime records master unchanged, existing outputs unmodified and test_evaluated=false. Raw checkpoint arrays and predictions were not included in this aggregate report archive for independent reload here.

## Validation results

Entries are accuracy / macro-F1 percentages. The master alone has65.47/64.68%.

| Reference | Small | Medium | Deep |
|---|---|---|---|
| server_supervised_only | 66.28 / 65.25 | 66.51 / 65.37 | 68.12 / 66.89 |
| master_distilled_only | 64.21 / 65.32 | 65.49 / 63.94 | 67.99 / 65.86 |
| Matched benign FedAvg, round12 | 96.64 / 88.91 | 86.01 / 83.79 | 95.50 / 87.83 |
| Matched benign KD + FedAvg, round12 | 86.43 / 85.43 | 86.12 / 85.39 | 85.99 / 85.11 |
| Matched benign EAD + FedAvg, round12 | 96.64 / 88.67 | 83.76 / 75.68 | 94.75 / 87.08 |
| Matched benign EAD + KD + FedAvg, round12 | 86.37 / 85.52 | 86.13 / 85.28 | 86.01 / 85.18 |

Supervised references use20passes over30,048labelled server rows (600,960training presentations per model). Distilled references use nine KD passes (270,432unlabelled presentations) and inherit the master's supervised pre-training. FL rows/training budgets differ; these are descriptive central-data references, not compute-matched attack baselines.

All central references have Malware recall99.50% and2/801Malware-to-Normal errors (0.2497%). Their DoS recall is only29.01–37.52%, versus the master's32.97%. Normal false alarm rates range4.74–11.74% among the six student references. These distinguish class-specific knowledge from overall utility.

## Interpretation and permissible claims

The tested server-only references do not reproduce the benign FL models' overall utility. For example, combined benign FL accuracy is about86% for all architectures at round12, versus64–68% for the server-only references. This weakens the explanation that the tested central-only training procedures fully reproduce the observed endpoint utility. It does not prove an isolated causal benefit for KD or establish that no alternative central-data procedure could match FL.

The central models already classify Malware accurately and rarely as Normal. Therefore the combined method's low targeted error remains plausibly dependent on trusted server supervision. These unpoisoned references do not prove poisoning robustness. They do not determine how much protection comes from the master inside FL.

The master and its isolated students show substantial class-specific limitations. Low DoS recall is consistent with the need to inspect negative transfer, but the controls alone do not prove why a particular FL trajectory changes.

Next controls, if needed for stronger final claims, are within-FL warm-start-only and no-master/adaptive variants, fixed-teacher/gate ablations, and controlled proxy-size/distribution changes without a master trained on a larger hidden server dataset. No such within-FL ablation has been run here.

## Cost and thesis role

Recorded audit/reference elapsed time82.22seconds; individual training times7.29–20.98seconds. These omit the original master-pretraining cost and are not a detector/FL efficiency benchmark.

The findings strengthen Chapter4's supervision qualification and Chapter5's utility/security synthesis. They provide partial evidence addressing reviewer concerns about central supervision and validation dependence, not closure of the proxy-sensitivity or fairness questions. The final-test/protocol/provenance limitations remain. Use [server_supervision_audit.md](server_supervision_audit.md) for the predeclared protocol and [development_evidence_summary_20261027.md](development_evidence_summary_20261027.md) for the main36run findings.
