# EAD prediction API confirmation

Status: implemented, syntax and structural checks passed; UWE execution pending. Registered 26 October 2026.

Purpose: test whether the fixed-upload prediction/calibration finding persists when screening decisions affect subsequent rounds. This is a separately named development configuration, not retrospective replacement of existing results.

Runner: scripts/run_ead_predict_confirmation.py.
Configuration: ead_predict_paper_3strict_v1.
Allowed runs: original mode, EAD on, KD off, sample-weighted FedAvg; benign sigma0 and attack sigma0.5.

Only screening changes from the original runner: use detector.predict(scaled) and detector.decision_function(scaled) instead of fitted labels_ and decision_scores_. LOF/IForest/kNN, seeds, neighbour counts, per-round contamination reset0.20, count-range calibration to0.30 with one immediate rerun, and unanimous voting remain otherwise unchanged. Original training/poisoning/calibration/aggregation loop was checked by AST comparison and is unchanged.

Reuse matched_seed42_v1. Save outputs with suffix _ead_predict_paper_3strict_v1, preserving existing folders. Base-runner hash is checked before execution and recorded in reports. Independent output folders are required; existing outputs are never overwritten.

Commands, from activated UWE project:
```bash
python -u scripts/run_ead_predict_confirmation.py --mode original --ead on --kd off --arm benign --sigma 0 --aggregation fedavg
python -u scripts/run_ead_predict_confirmation.py --mode original --ead on --kd off --arm attack --sigma 0.5 --aggregation fedavg
```

Run sequentially. Compare first-round detector counts and decisions with matching fixed-upload diagnostic conditions. In later rounds compare actual detector counts, confusion counts, calibration, accepted clients, aggregate accuracy, macro-F1 and class recall. Later differences from original trajectories are expected. All subsequent rounds start from this variant's own committed aggregate.

Completion requires both reports completed with four rounds, matched-input verification across original/confirmation conditions, and inspection of first-round equivalence and later outcomes. Stop for input/hash failures or invalid numerical values. Do not require perfect detection as an implementation check.

This is one seed and four rounds; no final-test evaluation or general robustness claim. Five-detector voting is a secondary development option and is not changed here. KD remains disabled to isolate EAD. Original notebook seed42 and other legacy training/architecture choices are not adopted, so full notebook reproduction is not claimed.
