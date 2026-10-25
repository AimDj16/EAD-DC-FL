# EAD-DC-FL method specification

Version 0.2, 14 October 2026. Status: planning specification, not an implemented or validated method.

## Objective

Establish one reproducible experimental framework combining DC-FL S4 with calibrated EAD-FL and sample-weighted FedAvg aggregation, and evaluate targeted poisoning under architectural and statistical heterogeneity. Determine whether targeted harm survives binary filtering or transfers through server-side KD while clean utility remains acceptable. Use the resulting evidence, if limitations are observed, to motivate WEAD-FL.

Improved robustness is an experimental question. Combining the methods is not evidence of improved detection, classification, or security. S4 and EAD filtering provide the component foundations. FedAvg is the primary aggregation rule for matched development experiments; Median is a separate comparator. Their combination is not claimed to be globally optimal. The exact calibrated three- or five-detector voting configuration remains to be verified. See the [targeted-attack study](targeted_attack_study.md) for selection criteria.

## System and threat assumptions

- Clients share an input feature schema, class vocabulary, and class ordering. Their architectures may differ.
- Architecture clusters are predefined by registered model metadata. They are not clusters inferred from update similarity.
- Clients within a cluster use the same model definition and ordered parameter schema. Matching tensor dimensions alone is insufficient to establish semantic compatibility.
- The server maintains and distributes one model per architecture cluster. Clients in that cluster receive the same initial weights for a round.
- The initial pilot uses synchronous, full participation. Participation heterogeneity is a later extension.
- The server and its proxy data are trusted. Client submissions are individually visible to the server. Secure aggregation and differential privacy are outside the initial scope.
- The adversary controls selected clients and may poison their training labels, inject a feasible trigger into local training samples, or manipulate submitted model contributions according to the specified attack. The server does not receive malicious-client identities or the true malicious proportion.
- Ground-truth client status is available only to the simulator and evaluation process. It must not control detector thresholds, teacher selection, filtering, or aggregation.
- KD occurs entirely at the server. Clients do not receive proxy samples and do not submit logits or features. A poisoned cluster model can nevertheless produce harmful teacher outputs.

## Data contract

Create mutually disjoint client-training, server-KD, server-validation, and held-out test partitions. When a master teacher is used, its supervised training data must be identified explicitly and excluded from validation and test data. Labels attached to server-KD samples may be used for master pre-training if the selected strategy requires this; they are withheld during unlabelled KD.

Fit imputers, encoders, and numerical transformations using permitted training data only. Record which training partitions provide fitting statistics, including any central preprocessing assumed by the simulation. Validation and test samples do not provide fitting statistics.

Select features by explicit names, excluding the target, rather than assuming that the last CSV column is the target. Record row identifiers, dataset hashes, feature names and order, label mapping, preprocessing parameters, split seed, and allocation indices. Inspect duplicate records and related flows; specify whether grouped or temporal separation is needed before freezing the split.

IID allocation must partition client-training samples without overlap. Dirichlet allocation must preserve disjointness and record realised sample counts and class distributions. Empty or undersized clients require an explicit allocation policy and a record of any resampling.

## Initial development configuration

These settings are proposed pilot choices. They do not reproduce either paper in full and are not final thesis settings.

| Component | Proposed choice | Status |
|---|---|---|
| Dataset | IDSIoT2024 | Acquisition, exact version and schema pending |
| Client count | 30, with 10 clients per architecture | Provisional; sufficient observations are not assumed |
| Architectures | Small [128], Medium [256, 128], Deep [256, 256, 128] | Taken from the supplied DC-FL paper |
| Output | Linear class logits; cross-entropy from logits | Required for the selected DC-FL implementation |
| Regularisation | No Batch Normalisation or Dropout in the combined pilot | DC-FL model choice; EAD-FL reproduction retains its own architecture |
| Allocation | Disjoint IID; equal client sample counts where feasible | Initial development condition |
| Participation | All clients in every round | Initial scope |
| Aggregation | Sample-weighted FedAvg within each cluster | Primary matched baseline; coordinate-wise Median is a comparator |
| Detection | LOF, Isolation Forest, kNN, PCA and One-Class SVM | Per-cluster fitting; settings pending |
| Voting | Calibrated strict voting, with three- and five-detector candidates | Exact primary configuration pending verification; majority voting is a sensitivity comparison |
| Calibration | Paper-rule calibration in the primary EAD baseline | Activation and persistence must be specified; no-calibration is an ablation |
| KD | Adaptive S4 | Primary DC-FL strategy; no KD and static S2 are controls |
| Attacks | Targeted label flipping, then a feasible targeted backdoor | Separate families; clean and untargeted controls retained |
| Repetitions | At least five matched seeds for main comparisons | Final seeds pending |

Data fractions, communication rounds, local epochs, batch sizes, learning rates, optimiser-state policy, detector parameters, and attack severity must be resolved before running this pilot. The DC-FL paper reports KD temperature 3, three KD epochs and batch size 256; these are reproduction references, not validated combined-framework settings.

## Model representation and aggregation

For EAD-FL reproduction, flatten full submitted model weights in a fixed order. Flattening must return both the numerical vector and metadata needed for exact reconstruction. Detector inputs use the vector, not a tuple containing vector and metadata.

Standardise detector inputs within the current architecture cluster, as a documented adaptation of the EAD-FL pipeline. Fitting this transformation on submitted contributions includes potentially adversarial samples; its robustness must be assessed. Do not pool incompatible architectures or use padding to imply shared parameter semantics.

Retain full-weight detection as the first integration baseline. Update differences relative to the received cluster model are a distinct later variant. Any normalisation or dimensionality reduction beyond the reproduction pipeline also requires a separate configuration and ablation.

Only accepted, compatible contributions enter aggregation. Sample-weighted FedAvg is the primary aggregation rule and uses accepted clients' recorded training sample counts, renormalised after filtering. Coordinate-wise Median remains an explicitly selected unweighted comparator. Use the same validated sample-count convention across methods. Other robust rules remain comparisons, with their admissible cohort sizes and tolerance parameters declared explicitly.

## Federated round

1. Distribute each architecture cluster's current model and record its round identifier.
2. Train participating clients. Apply data poisoning before local training and model poisoning at the submission boundary, according to the attack definition.
3. Validate submission metadata, tensor schema, and finite values. Log protocol failures separately from statistical anomaly decisions.
4. Group submissions by registered architecture identifier. Run the selected detectors, voting, and optional calibration within each group.
5. Aggregate accepted contributions within each cluster and retain a pre-KD snapshot.
6. Select and freeze the teacher according to the configured KD strategy. Evaluate the same frozen S2 teacher for all student updates in that round.
7. Distil students using server-KD inputs. Evaluate candidates using server-validation data only when the strategy includes a validation decision.
8. Commit or reject candidates according to the strategy, record all decisions, evaluate on the held-out test partition for reporting, and distribute the resulting cluster models.

Test measurements must never select a teacher, threshold, hyperparameter, or stopping point.

## Voting and calibration

Five-detector majority voting flags a client when at least three detectors flag it. Strict voting flags a client only when all five detectors flag it. Three-detector strict voting is the configuration described in the paper's calibration experiment; five-detector strict voting is also retained as a candidate because of its benign-client preservation results. The primary vote size must be resolved through paper-to-code verification and development evaluation, not by selecting the weakest targeted-attack result. Record which detectors drive calibration and voting. Diagnostic scores from additional detectors must not silently affect the deployed ensemble.

The supplied EAD-FL paper defines detector anomaly counts, their range, and a disagreement threshold. If the range exceeds the threshold, increase contamination by the specified step, bounded by its maximum, and rerun detection once before voting. Its reported parameters are initial contamination 0.2, step 0.1, maximum 0.4, and disagreement threshold 0.

Implement and log this rule literally for reproduction. Specify activation rounds, whether contamination persists between rounds, and whether adaptation is shared or cluster-specific before enabling it in the combined study. Those integration choices are unresolved. Equal counts can conceal disagreement over client identities, and increasing contamination is not an estimate of true adversarial prevalence.

## KD semantics

Teacher and student outputs must be logits. For temperature T, use softened distributions softmax(z_teacher/T) and softmax(z_student/T), and the loss T squared times KL(teacher || student). Average over samples consistently. Freeze teacher parameters and update student parameters only. Do not apply temperature softmax repeatedly to probabilities.

S2 selects the highest-capacity registered architecture as teacher and does not distil that teacher into itself. Capacity is measured by parameter count, with deterministic tie handling.

S4 adds master-teacher warm-start rounds, validation-based teacher selection, and candidate acceptance. Reproduction must preserve the paper's strategy, including its warm-start branch; extending candidate checks into warm start is a separately named variant. Master training, warm-start duration, and validation tie handling remain to be specified.

In S4's adaptive branch, compare each candidate's validation accuracy with the same cluster's pre-KD aggregated model. If KD is rejected, restore that pre-KD model, not the previous round's model. This rule limits observed validation regression and does not guarantee protection against backdoors or class-specific harm. A macro-F1 or class-specific acceptance rule would be an extension, not an unreported replacement for paper S4.

## Failure policies

- With no valid or accepted contributions, retain the previous cluster model, mark the round as unaggregated for that cluster, and do not reintroduce rejected contributions.
- Specify minimum cohort sizes for every detector. An inadmissible configuration must fail clearly; it must not silently disable detection or alter voting.
- If an enabled aggregator's cohort requirement is not met after filtering, retain the prior cluster model and log aggregation failure. Do not silently reduce trimming or Byzantine tolerance.
- A cluster without a successful current-round aggregation is excluded from teacher eligibility. For S2, skip KD if its predefined teacher is ineligible. For S4, skip adaptive KD if no eligible teacher exists. These are combined-framework failure policies, not claims about the original papers.
- Log malformed submissions, detector failures, numerical failures, and validation rejection separately. Silent fallback is prohibited.

## Experimental comparisons and outcomes

Compare architecture-specific FedAvg, DC-FL without filtering, cluster-specific EAD-FL without KD, and EAD-DC-FL. Use S4 plus calibrated strict EAD-FedAvg as the primary matched combined baseline. The current development runners use the three-detector strict ensemble; five-detector and alternative voting choices require their own configurations. Keep alternative aggregation, no calibration, majority voting, and KD strategies as separate ablations. Keep homogeneous EAD-FL reproduction as a separate configuration; its direct comparison with heterogeneous runs must identify architectural differences.

Match data partitions, initial weights, client sample counts, participation, and attack schedules where applicable. Maintain independent random streams for allocation, initialisation, client training, attack construction, and detectors so disabling one component does not change unrelated stochastic conditions.

Run each defence in its own training trajectory. Multiple detector predictions may be analysed on one round's inputs, but that does not provide each detector's downstream model accuracy.

Report classification macro-F1, accuracy, per-class recall, and per-cluster utility; detection precision, recall, F1, FPR and FNR; benign-client exclusion; accepted cohort sizes; teacher identity; pre/post-KD utility; candidate acceptance; runtime; and communication volume. Report continuous-score AUC separately from vote-count ranking. Mark single-class AUC and other undefined metrics explicitly rather than treating them as successful detection.

Vary both total malicious proportion and its allocation across clusters. Record realised proportions, including within-cluster majorities. Examine whether attacks concentrated in the teacher cluster affect other clusters after KD. Clean controls are necessary to measure exclusion caused by contamination assumptions alone.

The current specification does not define a single global prediction ensemble. Per-cluster evaluation uses the same held-out test partition; any summary across clusters must state its weighting rule. Targeted attacks are the principal security evaluation after correctness verification. Use target-specific metrics and backdoor attack success rate as specified in the targeted-attack study. Non-IID severity, smaller proxy sets, small clusters, and participation heterogeneity provide additional conditions.


## Matched development controls added 25 October 2026

All new compared conditions must load the same saved initial weights per
architecture and the same hash-verified data, client allocations, normalisation,
master and compromised-client selection. All 30 clients participate in each of
the four development rounds, in a recorded fixed order. Local minibatch row
orders are generated independently by client/round and Keras shuffling is
disabled. Changes to any registered input or training budget cause a failure
before training. EAD may intentionally change aggregation contributors, and KD
and attacks may intentionally change later models. See
[matched FedAvg development](matched_fedavg_development.md). Existing Median
results must not be relabelled or mixed into this new matched baseline.
