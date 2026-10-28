# Clean control using fixed reference inclusion lists

Registered 26 October 2026. Implemented and statically checked; UWE execution pending.

## Question

Can the completed predict-EAD+original-KD attack trajectory be reproduced with no poisoning, when exactly the same clean contributors are aggregated?

This is an offline attribution diagnostic, not a deployable defence or a new method. Reference masks are derived from completed attack outputs. They are not estimated by the control.

## Execution

Runner: scripts/run_clean_reference_mask_control.py.
Allowed configuration: original mode, EAD off, KD on, benign arm, sigma0, FedAvg.

```bash
python -u scripts/run_clean_reference_mask_control.py --mode original --ead off --kd on --arm benign --sigma 0 --aggregation fedavg
```

Reference directory is resolved using the existing experiment ID and suffix gaussian_sigma0p5_attack_original_ead_on_kd_on_seed42_ead_predict_paper_3strict_kd_v1. The reference must contain four completed rounds, seven accepted clients per architecture and rejection of every malicious upload with no benign rejections. Its report, runner and checkpoint hashes are checked. Common data/master/environment/budget hashes and initial tensor hashes are compared.

Control trains all30 clients normally with identical allocations, order, local epochs, optimiser and seeds. No uploads are poisoned. EAD screening is disabled. Saved per-round/per-group rejection lists are applied externally; retained uploads are sample-weighted and original-mode KD proceeds. The control starts from matched initial checkpoints; it does not initialise from any attacked trajectory checkpoint. Reference checkpoints are read solely for comparison.

Outputs have suffix _clean_reference_mask_kd_v1, separate from all earlier outputs. The original runner and matched manifest are unchanged. Excluded honest clients are recorded under mask_control_audit, not as EAD false positives.

Each round compares participants, row-order hashes, local losses, accepted counts/coefficients, pre-KD validation, teacher/phase, KD candidate metrics and losses, acceptance/rollback, committed metrics and committed tensor shape/dtype/exact values. Stop at first mismatch; write comparison_failed report. Completion requires all four exact comparisons to pass. Exact matching is justified here by the prior exact-repeat results in this environment; differences require diagnosis, not an assumption of attack leakage.

## Interpretation

If identical: no poisoned-upload contribution is needed to reproduce this trajectory under the fixed retained-client masks. This supports attribution to retained contributions and the original learning/KD process. It does not isolate the separate causal effect of removing clients versus teacher choice/warm-start, establish utility fairness, or prove robustness on another seed/threat.

If different: examine earliest mismatch, runtime equality and possible implementation dependencies. Do not infer residual malicious transfer merely from unequal final performance.

Static verification: Python syntax, unchanged original function definitions, and unchanged local-fit/distil/commit_or_revert/aggregate_models call arguments. Full TensorFlow execution is deferred to UWE. No final test data are evaluated.
