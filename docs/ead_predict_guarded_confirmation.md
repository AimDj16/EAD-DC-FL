# Guarded master warm-start confirmation

Registered 26 October 2026. Static checks and shared guard checks passed; full UWE execution pending.

Runner: scripts/run_ead_predict_guarded_confirmation.py.
Configuration ID: ead_predict_paper_3strict_guarded_kd_v1.
Output suffix: _ead_predict_paper_3strict_guarded_kd_v1.

## Isolated change

Relative to run_ead_predict_kd_confirmation.py original mode, require --mode guarded. In rounds1–3 retain master teacher and identical KD budget, but commit a candidate only if its validation accuracy is at least the pre-KD accuracy. Otherwise restore pre-KD aggregate tensors. Round4 keeps adaptive selection and the same accuracy guard.

LOF/IForest/kNN, predict/decision_function API, strict voting, contamination reset0.20 and count-disagreement rerun at0.30, compatible-group sample-weighted FedAvg, data/initial states/master/participation/batch orders/seeds are unchanged. Screening functions and full round-loop AST match the original-mode predict runner; existing mode branch implements guarded behaviour. Actual shared commit_or_revert function was checked without TensorFlow for decline rollback, improvement acceptance and tie acceptance.

## Sequential runs

From activated UWE project:

```bash
python -u scripts/run_ead_predict_guarded_confirmation.py --mode guarded --ead on --kd on --arm benign --sigma 0 --aggregation fedavg
python -u scripts/run_ead_predict_guarded_confirmation.py --mode guarded --ead on --kd on --arm attack --sigma 0.5 --aggregation fedavg
```

Reuse matched_seed42_v1; do not regenerate manifest or overwrite old results.

## Required analysis

Both four-round reports complete; verify common inputs and first-round screening/pre-KD equality to original mode. Check all performed KD entries use validation_accuracy_guard and committed accuracy>=pre-KD accuracy. Inspect rejection cases and saved checkpoints; synthetic guard checks alone do not prove full runner correctness. Record pre/candidate/committed macro-F1, class recall and targeted error without asserting that these improve. Compare each attack run with its own guarded benign control and with original-mode results.

Later EAD decisions, teacher choices and model states can differ because guard decisions alter subsequent training. Do not demand identical later trajectories between modes. Candidate training still occurs before rejection; it incurs cost. This variant does not change teacher metric, optimise macro-F1 or use attacker labels.

## Interpretation boundaries

Tests whether unconditional master warm-start causes avoidable validation-accuracy losses in this development configuration. It does not guarantee higher final performance, independent-test/client-specific protection, minority recall, security, privacy or general robustness. One seed, four rounds, IID client allocation, validation-only; original test remains untouched. Keep original-mode results as methodological evidence. Calibration-trigger redesign and H_P remain separate studies.

Clean-mask control completion was reported by user before this extension; its full JSON still awaits independent inspection. Do not claim final confirmatory evaluation or published-code equivalence.
