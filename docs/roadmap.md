# Implementation roadmap

The first deliverable is a complete method specification and dependency audit. This repository currently contains planning documents and archived original helper files, but no new training implementation. Implementation starts after the missing-input decisions and pilot settings are resolved.

## Stages and acceptance criteria

| Stage | Work | Acceptance criteria |
|---|---|---|
| 1. Resolve specification | Use the recovered helpers; resolve paper/code differences; verify data; record numerical settings | Every unresolved item has a decision or explicit blocker; source versions identified |
| 2. Shared foundation | Implement data partitions, model registration, client training and run records | Disjoint partitions; common within-cluster initialisation; fixed schemas; traceable run configuration |
| 3. Benign DC-FL | Implement architecture-specific aggregation and S4, including master warm start and correct KD | Fresh-environment execution; finite models; verified KD loss; correct pre/post-KD snapshots |
| 4. EAD-FL reproduction | Implement homogeneous filtering, strict-vote candidates, paper-rule calibration and Median aggregation | Known detector orientation; correct votes; ground truth isolated from defence; independent model trajectories |
| 5. Combined pipeline | Insert per-cluster filtering before aggregation | Compatibility checks; explicit minimum cohorts; logged fallback; accepted sample weights normalised |
| 6. Targeted poisoning and KD transfer | Add targeted label flipping and a feasible backdoor; evaluate the verified S4/EAD-Median baseline | Validation/test separation; clean/attack pairing; target denominators; pre/post-KD comparisons; no test-based attack tuning |
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

1. Verify benign architecture-specific aggregation and S4, including master training and warm-start budgets.
2. Verify EAD filtering, calibration and Median aggregation in clean and untargeted positive-control runs.
3. Freeze the primary calibrated strict-voting configuration using the papers and separate development evaluation.
4. Evaluate targeted label flipping with matched clean controls across the four core filtering/KD combinations.
5. Evaluate a targeted backdoor only after trigger feasibility and clean/triggered evaluation sets are specified.
6. Examine attacks distributed across clusters and concentrated in the teacher cluster, with pre/post-KD comparisons.
7. Run voting, calibration, aggregation and KD ablations; extend to non-IID data and additional heterogeneity conditions.
8. Assess whether continuous detector evidence contains useful information lost by binary voting, and whether that supports the separate WEAD-FL study.

Targeted attacks are the main security question. Untargeted attacks check the implementation against the original threat setting. Do not tune the baseline to fail, assume S4 prevents targeted harm, or claim WEAD-FL superiority before a matched comparison.

Keep final thesis settings separate from development settings. Larger experiments proceed only after the relevant correctness checks pass; pilot success does not establish full-horizon stability or adversarial robustness.
