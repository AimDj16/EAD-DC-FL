# Targeted poisoning with predict EAD

Registered 26 October 2026. Static verification passed; UWE execution pending.
Runner: scripts/run_targeted_predict_confirmation.py.
Configuration/output suffix: ead_predict_paper_3strict_targeted_v1.

## Four runs

Original mode, EAD on, FedAvg, benign/attack crossed with KDoff/KDon. Reuse existing saved matched manifest, initial weights, full30client schedule and row orders. No new data partition or attack selection.

Source attack protocol remains Malware-to-Normal, all saved Malware rows on nine compromised clients (three per architecture),1497 rows per round;100% of their Malware class rather than100% of their complete training data. Features, other labels, server/evaluation labels unchanged. Four rounds, seed42, validation-only. No Gaussian sigma argument is accepted for this label-flipping runner.

Only screening prediction calls differ from original targeted source: predict/decision_function instead of labels_/decision_scores_. Screening function AST exactly matches the completed Gaussian predict runner. Original targeted full training/poisoning/aggregation/calibration/KD round loop and other function definitions are unchanged. The script checks original targeted source hash. Three detectors, strict consensus, per-round gamma0.20 with count-range-triggered immediate rerun at0.30. Original master warm-start rounds1–3 remains unconditional for KDon; do not confuse with separate guarded Gaussian variant.

## Verification and analysis

Require all four reports completed and common inputs matched. Benign metrics, screening and KD records should match corresponding completed Gaussian predict benign runs with the same KD setting; compare before attributing attack effects. First round accepted counts and calibration must follow actual predictions; perfect detection is not a completion requirement.

Analyse per-round TMR attack minus matched benign, maximum excess TMR and fixed-horizon mean excess TMR as descriptive trajectory summaries, Malware recall, macro-F1, class recalls, and pre/candidate/committed KD values. Clients/rounds are not independent replications. Report detection TP/FN/FP/TN and benign rejection by architecture. Earlier fitted-label targeted runs remain preserved sensitivity comparisons, not results for this configuration.

No new gate/teacher/attack-strength tuning in these four runs. Perfect/low TMR does not establish all-class robustness, no leakage, final-test performance or generalisation. Revised configuration was selected using development observations. Freeze the viva development evidence after this bounded comparison; independent-seed and broader heterogeneity studies remain outstanding.
