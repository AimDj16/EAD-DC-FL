# Server supervision audit and isolated references

**Results update,28October2026:** the UWE audit and all six requested central-only reference fits have completed. Master validation metrics replayed exactly; boundary/scaler checks passed. See [server_supervision_seed42_results.md](server_supervision_seed42_results.md) for verified outcomes and their limits. The protocol below records what was specified before that execution.


Prepared28October2026. This is an additional control protocol, not a replacement for the completed36run development evaluation. No control outcomes are claimed before UWE execution.

## Verified implementation facts

| Component | Inputs and label use | Implementation evidence | Scientific implication |
|---|---|---|---|
| Master pre-training | All30,048 server_kd examples with their class labels;20epochs; fixed final-epoch checkpoint | [Partition loading](../scripts/pretrain_development_master.py#L64), [supervised fit](../scripts/pretrain_development_master.py#L106), [checkpoint policy](../scripts/pretrain_development_master.py#L170) | KD methods inherit a centrally supervised teacher. Their benefit is not attributable solely to federated knowledge exchange. |
| Recurring KD | All30,048 server_kd feature rows, without ground-truth labels in the distillation loss | [KD input selection](../scripts/run_matched_replication.py#L244), [KL objective](../src/ead_dc_fl/models_and_kd.py#L30) | Calling KD inputs unlabelled does not make the overall method independent of labelled server data. |
| Validation |7,600 separate labelled server_validation examples, used for teacher selection, acceptance and reported metrics | run_matched_replication.py | Validation is a model-selection resource, not an independent final test. |
| Final test |9,472 held-out rows; no predictions performed by this audit | audit_server_supervision.py | The final-test outcomes remain outside these reference controls. |

The KD_SAMPLE_LIMIT=512 constant in the training runner is unused in the current input-selection path. The actual selected_kd_rows array is the complete server_kd allocation. Do not describe the completed runs as a512example proxy study.

The pre-training fit does not receive validation_data, early stopping or validation checkpoint selection in the inspected script. The final validation evaluation is separate from its20epoch supervised fit. This source fact does not recover the unavailable upstream preprocessing pipeline or independently reproduce training the existing master.

## Why these controls are needed

The completed comparison evaluates the whole KD treatment, including trusted master supervision. It does not establish how much performance the centrally labelled data could supply without any clients. That gap affects interpretation of utility gains and reviewer concerns about unequal access to central supervision.

The smallest additional programme is an input/boundary audit, a fixed-master replay, and two isolated references per architecture. It creates no new defence, changes no EAD/KD threshold, uses no attacks and performs no client training.

| Reference | What is held fixed | Training performed | Question answered | Limit |
|---|---|---|---|---|
| Existing master only | Saved master checkpoint, server validation and normalisation | None | What performance does the existing supervised master already provide? | Different capacity from Small/Medium/Deep. |
| Server-supervised only, each architecture | Shared same-seed initial tensors, same30,048 server examples, validation and normalisation | Supervised training on server labels for20epochs, Adam0.001, batch256, final epoch only | How much performance can the same architecture obtain directly from the centrally labelled data alone? | Training presentations and computation differ from FL; report them rather than claiming compute matching. |
| Master-distilled only, each architecture | Same initial tensors, fixed master and server features | Three3epoch master-KD phases, temperature3, batch256, no client training, no validation acceptance gate | How much can the pretrained master supply through the original warm-start KD budget alone? | Inherits master labels and pre-training; omitting client training is deliberate and is not the FL warm-start trajectory. |

The six student reference fits are additional diagnostics. They are not six more matched FL runs and do not change the main count of36. Begin with seed42 as a bounded supervision diagnostic. It is not a three-seed control study.

These references do not isolate the master’s causal contribution inside the interacting FL trajectory. Warm-start-only, no-master/adaptive-from-round1 and equivalent-server-supervision comparisons within FL remain separate ablations if stronger causal claims are needed. In particular, a no-master variant would still use labelled validation for teacher selection and acceptance unless that mechanism were separately changed.

## Audit programme and decision criteria

The new [audit script](../scripts/audit_server_supervision.py) performs the following:
1. Loads the existing matched experiment and checks its registered input and initial-checkpoint hashes.
2. Checks master source, partition, normalisation and checkpoint hashes and its reported training partition/class/feature registry.
3. Recomputes exact feature groups from the source and checks all top-level row allocations and group separation. This establishes exact-feature separation, not capture/device/time separation.
4. Recomputes the training-only StandardScaler statistics in memory and compares them with the saved normalisation. It does not replace or save a new scaler. Relative tolerance1e-10 and absolute tolerance1e-12 address arithmetic precision, not upstream provenance.
5. Loads the four completed same-seed benign component reports and verifies their common experimental fingerprint and initial/master/settings metadata.
6. Loads the saved master and recomputes validation accuracy, macro-F1, recalls, confusion matrix, Normal false alarm rate and Malware-to-Normal TMR.
7. Compares the saved master’s accuracy, macro-F1 and per-class recalls with the replay, using absolute tolerance1e-12. If they differ, it saves status=reference_mismatch and stops before any student reference training. The replay is one defined verification step, not a claim that different hardware must always give bit-identical inference.
8. If the replay passes and the optional flag is supplied, trains the six student references from the saved initial tensors, logs budgets/timing/history, evaluates validation only and saves separate weights and predictions.
9. Verifies that the master weights are unchanged.

Success requires status=completed, boundary/normalisation checks passing, saved-master validation metrics reproduced, requested references completed with finite outputs, unchanged master weights and test_evaluated=false.

If the master replay differs, inspect the saved hash/environment/metric comparison before continuing. Do not bypass the check or overwrite its output directory. Any legitimate replay tolerance or source change must be a separately recorded decision.

## Outputs and interpretation

A new output directory contains report.json, validation predictions and student checkpoints. Existing reports/data/checkpoints are not overwritten. Logs include source/code/checkpoint hashes, initial tensor hashes, classes, server/validation label counts, software/GPU metadata, labelled/unlabelled training presentations, training seconds, histories and per-class outcomes.

Normal false alarm rate is Normal validation examples predicted as an attack class. It is distinct from EAD’s benign-client rejection rate. TMR uses Malware examples predicted as Normal, with a different denominator. Both are recorded alongside the full confusion matrix.

The master’s earlier pre-training computation is inherited by distilled references and is not timed again. Their recorded training seconds therefore do not include that original cost. Twenty supervised epochs and nine unlabelled KD epochs are different budgets, deliberately reported explicitly. No efficiency superiority follows from these reference timings.

The source CSV is read for integrity and exact-feature grouping, including the held-out rows’ feature identities. No test predictions, test performance, test-driven tuning or test-labelled training is performed. Only server_kd and server_validation are extracted for model use. Upstream preprocessing remains unverified.

These references are unexposed to malicious clients. They quantify central-data utility, not poisoning robustness. Evaluate differences against the existing same-seed benign FL results as descriptive controls. Do not rank them as fair attack-defence baselines without stating the changed data, threat exposure and training budget.

## Validation completed here

- Python syntax and CLI help: passed.
- Six new integrity/metric tests: passed. They include exact-feature overlap despite disjoint row IDs, duplicate/missing allocation, training-only versus whole-file normalisation, and distinct targeted-error/IDS-false-alarm denominators.
- Existing12matched-experiment tests: passed.
- TensorFlow inference/training with the actual UWE data and master: not executed in this environment. The saved master report/checkpoint must be inspected through the UWE audit output before any new numerical conclusion is written.

## Run on UWE

From the project root in the activated GPU environment:

```bash
git pull --ff-only
python -m unittest discover -s tests -p 'test_server_supervision_audit.py' -v
python -u scripts/audit_server_supervision.py \
    --matched-experiment data/experiments/idsiot2024/replication_seed42_rounds12_v1 \
    --output outputs/controls/server_supervision_seed42_v1 \
    --include-server-only-controls
```

Audit-only execution omits --include-server-only-controls and must use a separate unused output directory. Avoid running audit-only and then reusing that directory for controls.

After successful completion:

```bash
tar -czf server_supervision_seed42_v1_report.tar.gz \
    outputs/controls/server_supervision_seed42_v1/report.json
```

Upload the report archive for review. Aggregate JSON is sufficient for the first analysis; keep checkpoints and per-example validation predictions on UWE for any follow-up verification.

## Thesis role

Chapter4 can use these references to quantify central-supervision dependence and qualify the interpretation of KD gains. Chapter5 can distinguish utility supplied by server labels from security/utility effects of recurring transfer. Proxy-size/representativeness sensitivities, repeated controls, final-test evaluation and matched within-FL master-policy ablations remain outstanding. This audit does not convert development validation into independent evidence or resolve unavailable upstream preprocessing.
