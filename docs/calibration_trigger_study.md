# Calibration trigger study and KD confirmation, 26 October 2026

## Immediate experiment

Run scripts/run_ead_predict_kd_confirmation.py for original/EADon/KDon/FedAvg benign sigma0 and attack sigma0.5. It retains identical screening functions and the complete original round loop from the KD-off predict confirmation; syntax and AST comparisons passed. GPU execution pending. Outputs suffix _ead_predict_paper_3strict_kd_v1. Shared inputs/manifest unchanged; no final test evaluation. Original-mode unconditional master KD rounds1–3 remains intentionally unchanged.

## Trigger question

Desired outcome: increase contamination when the true active malicious fraction exceeds its current value, while avoiding unnecessary increases under benign variation. The true fraction is unavailable at runtime. It can be used only for offline evaluation and an explicitly labelled oracle upper-bound control. Detector disagreement is a heuristic, not a verified estimate of that fraction.

Supplied EAD paper Table I: at0% malicious, 3-Strict FPR0.060 and5-Strict FPR0.034. These are ensemble results and do not establish that calibration never activated. Current completed predict3strict benign pilot has14/120 rejected submissions and7/12 calibration activations; current fixed-upload five-strict predict diagnostic has3/120 benign rejections. These are different experiments and cannot be directly equated.

## Bounded recommended study, not implemented or frozen

Finish the KD confirmation without changing its trigger. Next isolate calibration with KDoff, starting gamma0.20 and fixed enrolled malicious fractions0,0.10,0.20,0.30. Keep Gaussian sigma0.5 as an initial development threat, not the full validation scope. Fixed malicious sets per run should be nested or otherwise documented and matched across policies. Maintain architecture, data, seed and training controls. Partial participation is a separate extension, at which point evaluation must use active rather than enrolled malicious fraction.

Compare fixed0.20, existing count-range trigger, fixed0.30 and a truth-aware oracle control used only offline. Use fixed-upload comparisons first; follow with bounded end-to-end cases. Three/five strict voting must remain a separate factor because voting can reduce FP independently of triggering. Record TP/FN/FP/TN, calibration activation, underlying detector scores/counts, and per-class utility.

Offline trigger metrics: activation frequency when rho_t<=gamma, activation frequency when rho_t>gamma, and downstream changes in malicious rejection, benign rejection and utility. Triggering at rho_t>gamma is not intrinsically sufficient for a useful threshold update; assess actual outcomes. Oracle knowledge does not make it a deployable defence.

Only after these controls should a new evidence-based trigger be proposed. Candidate score-separation/temporal evidence requires its own development protocol and held-out validation. Do not feed known attacker ratios or identities into runtime policy. Freeze candidate decisions before independent-seed/held-out threat evaluation. Do not guarantee exact identification of rho_t>gamma from submitted model evidence.

Finish current comparison before adding new trigger code. Low FPR in one ensemble setting alone is not evidence of valid calibration or general robustness.
