# Implementation roadmap

The first deliverable is a complete method specification and dependency audit. This repository currently contains documentation only. Implementation starts after the missing-input decisions and pilot settings are resolved.

## Stages and acceptance criteria

| Stage | Work | Acceptance criteria |
|---|---|---|
| 1. Resolve specification | Recover or reconstruct helpers; verify data; record numerical settings | Every unresolved item has a decision or explicit blocker; source versions identified |
| 2. Shared foundation | Implement data partitions, model registration, client training and run records | Disjoint partitions; common within-cluster initialisation; fixed schemas; traceable run configuration |
| 3. Benign DC-FL | Implement architecture-specific FedAvg, then S2 with correct KD | Fresh-environment execution; finite models; verified KD loss; correct pre/post-KD snapshots |
| 4. EAD-FL reproduction | Implement homogeneous filtering, voting and paper-rule calibration | Known detector orientation; correct votes; ground truth isolated from defence; independent model trajectories |
| 5. Combined pipeline | Insert per-cluster filtering before aggregation | Compatibility checks; explicit minimum cohorts; logged fallback; accepted sample weights normalised |
| 6. S4 and poisoning transfer | Add master warm start, adaptive teacher selection and candidate decisions | Validation/test separation; correct rejection restoration; frozen teacher; explicit teacher eligibility |
| 7. Controlled study | Matched clean/attack arms, baselines and ablations | Repeated seeds; per-cluster attack proportions; uncertainty across seeds; no test-based tuning |
| 8. Thesis outputs | Produce tables and figures from recorded runs | Every result maps to source revision, data manifest, environment, seed and configuration |

Stages 3 and 4 establish separate methods before interpreting integrated results. Readiness checks must distinguish implementation correctness from convergence and security performance.

## Planned component responsibilities

| Component | Responsibility |
|---|---|
| Data | Acquisition metadata, preprocessing, disjoint partitions and realised distributions |
| Models | Registered architectures, class ordering, parameter schemas and logits |
| Clients | Initialisation, local optimisation, sample counts and submission records |
| Attacks | Data/model poisoning definitions, severities and reproducible schedules |
| Detection | Representation, scaling, detector scores, calibration and voting |
| Aggregation | Accepted-contribution weighting and robust-rule validity |
| Distillation | S1-S4, frozen teachers, KD and candidate handling |
| Evaluation | Classification, detection, benign exclusion and KD transfer |
| Experiments | Configuration, random streams, manifests, checkpoints and summaries |

Use one experiment entry point with reusable modules. A notebook may provide an interface for execution and analysis. Module paths and interfaces are planning items; no empty implementation stubs are added at this stage.

## Required verification before substantial training

- Confirm pairwise separation of client, server and test sample identifiers.
- Confirm that preprocessing never fits on validation or test data.
- Confirm exact flatten/reconstruction, including shapes, order and dtypes.
- Confirm that different architectures cannot enter a common parameter-space detector or aggregator.
- Confirm that every client receives its own architecture cluster's correct round model.
- Confirm attack placement and that benign labels and samples are unchanged.
- Confirm identical teacher/student logits give zero KL within numerical tolerance, teacher weights remain fixed, and student gradients are finite.
- Confirm majority and strict voting on known prediction patterns.
- Confirm calibration changes predictions in the intended round and respects its configured bound.
- Confirm that rejected KD restores the pre-KD aggregate and does not revert accepted local learning from that round.
- Confirm that no accepted submissions causes documented model retention, rather than aggregation of rejected inputs.
- Confirm aggregator cohort constraints and detector minimum-sample behaviour.
- Confirm that classification accuracy logged for a method belongs to its own updated model.
- Confirm evaluation ground truth cannot affect defence decisions.
- Confirm run identity, source revision, split manifest and independent random streams are recorded.

These are planned checks, not checks already passed.

## Initial experiment sequence

1. Clean IID architecture-specific FedAvg.
2. Clean IID DC-FL with S2, compared with no KD.
3. Clean IID filtering without KD, including benign-client exclusion.
4. Separate sign-flip and Gaussian attack runs for all four core configurations.
5. Majority versus strict voting, then calibration as a separate ablation.
6. S4 and attacks concentrated in the teacher cluster, with pre/post-KD comparisons.
7. Non-IID severity, smaller proxy sets, small architecture clusters and partial participation.
8. Targeted and adaptive attacks under explicitly extended attack definitions.

Keep final thesis settings separate from development settings. Larger experiments proceed only after the relevant correctness checks pass; pilot success does not establish full-horizon stability or adversarial robustness.
