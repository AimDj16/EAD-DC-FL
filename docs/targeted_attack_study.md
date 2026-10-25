# Targeted poisoning against EAD-DC-FL

Version 0.1, 14 October 2026. Planning protocol; no attack experiments have been run.

## Study purpose

Evaluate whether targeted poisoning succeeds against a combination of strong EAD-FL and DC-FL components, and whether server-side KD transfers targeted harm across architecture clusters. If limitations are observed, determine which evidence supports the motivation for Weighted Evidence Aggregation Defence (WEAD-FL).

This study must allow a favourable result for EAD-DC-FL. It does not assume that targeted attacks will evade filtering or that continuous evidence fusion will improve the defence.

## Main baseline selection

Use DC-FL S4: a master-teacher warm start, adaptive selection of the cluster teacher by server-validation accuracy, and the paper's candidate commit/revert rule in its adaptive branch. Do not replace accuracy with attack success rate, modify warm-start acceptance, or add attack-aware teacher screening without identifying a separate variant.

Use calibrated EAD-FL filtering followed by sample-weighted FedAvg inside each architecture cluster for the primary matched study. Coordinate-wise Median remains a separate comparator. In the supplied EAD-FL paper, EAD-Median reports 98.0%, 97.6%, 96.5% and 96.1% final accuracy for 10, 20, 50 and 100 clients under the reported 30% untargeted malicious condition. It is a strong starting point, but is not the unique best rule at every scale.

The calibration experiment describes three-detector strict voting; five-detector strict voting also has strong benign-client preservation results. Table II does not fully identify the voting configuration behind every aggregation row. Verify this correspondence before claiming an exact reproduced baseline. The current matched development configuration uses three-detector strict EAD-FedAvg. Retain five-detector candidates, majority-voting sensitivities and EAD-Median as explicit separate comparisons.

Resolve the primary voting configuration from paper/code verification and separate development evaluation of clean utility, benign exclusion and the original untargeted setting. Record selection criteria before inspecting the held-out targeted results. Do not select the least effective variant to manufacture a gap. If the evidence does not distinguish candidates, report both.

## Targeted attack families

### Targeted label flipping

Choose a source class and target class before final evaluation. Compromised clients relabel a declared fraction of their source-class training samples to the target class; their other labels remain unchanged. Record the fraction, actual eligible sample counts, compromised-client allocation and activation rounds.

Evaluate targeted misclassification on untouched held-out source-class samples. This attack requires no trigger. It must be distinguished from random label flipping and from a backdoor.

Use the same partitions, initialisation, participation and training budget in matched benign runs. If an eligible client has no source-class examples, record that absence rather than silently borrowing data or changing the class pair. Fix source-target selection using domain rationale or development evidence, not final test behaviour.

### Targeted backdoor

After verifying the feature schema, define a trigger whose modifications respect feature types, valid ranges and the intended intrusion-detection scenario. Specify poisoning fraction, label reassignment, activation schedule, source/target scope and whether original or additional local samples are used.

The attacker may modify compromised clients' local data and permitted submissions. It does not modify server-KD or server-validation data under the initial threat model.

Create a separate triggered evaluation view from held-out samples. Preserve its source row identifiers and keep it out of training, teacher selection, detector calibration and model acceptance. Do not treat an arbitrary perturbation of normalised features as a realistic trigger without checking its meaning.

Targeted model-update manipulation and adaptive evasion are later, explicitly specified attack families. A backdoor does not automatically require model replacement, and a label-flip attack is not automatically stealthy.

## Comparisons

Run independent model trajectories for:

1. Architecture-specific sample-weighted FedAvg without filtering or KD.
2. DC-FL S4 with sample-weighted FedAvg and no EAD filtering.
3. Calibrated EAD-FedAvg without KD.
4. Calibrated EAD-FedAvg with DC-FL S4.

This main comparison holds sample-weighted FedAvg constant while varying filtering and KD. Median, no calibration, alternative voting and static S2 are separate comparisons. Report paper-faithful DC-FL reproduction separately where its client allocation or other settings differ. Every matched condition must share the saved initial checkpoints, data allocations, normalisation, master and participation schedule defined in [matched development](matched_fedavg_development.md).

Keep server data, master-training budgets, class mappings and evaluation samples identical where applicable. When KD is disabled, report the removed master/KD computation rather than implying identical total compute.

Evaluate attacks distributed across clusters and concentrated in the teacher architecture. Record federation-level and cluster-level malicious proportions. Identify whether an attacked cluster was actually selected as teacher in each round, rather than assuming that the deepest cluster is always the S4 teacher.

## Target-specific outcomes

For targeted label flipping, report targeted misclassification rate: the proportion of clean held-out source-class samples predicted as the target class. Report the matched benign rate and their difference, source-class recall and confusion-matrix changes.

For backdoors, report attack success rate on the declared eligible triggered samples. State the denominator, class exclusions and targeting scope. Exclude samples already belonging to the target class when the objective is forcing another class to that target. Report corresponding clean-source and triggered benign-control outcomes.

For both families, report clean macro-F1, accuracy, per-class recall, per-cluster utility, malicious-client recall, FPR/FNR and benign-client exclusion. Zero-malicious runs quantify exclusion caused by the defence itself.

Measure target-specific outcomes on pre-KD aggregates and post-KD candidates or committed models, together with teacher identity and KD acceptance. This distinguishes filtering failure, within-cluster aggregation effects and cross-cluster transfer. A validation-accuracy tie can coexist with target-specific harm; the S4 rule is not a targeted-security guarantee.

Record round trajectories, a predefined final/tail summary and seed-level uncertainty. Do not treat correlated rounds as independent repetitions.

## Evidence for WEAD-FL

Retain continuous anomaly scores, detector thresholds, binary flags, vote patterns, calibration history, accepted/rejected identities and cluster membership. Additional diagnostic detectors must not alter the selected deployed voting rule.

Assess whether targeted submissions survive because detectors give low scores, detectors disagree, calibration is unsuitable, or binary thresholding discards useful ranking information. Relate these outcomes to benign non-IID variation and targeted utility.

A failure of hard filtering alone does not establish that continuous weighting can solve it. If the underlying detector scores contain little usable information, WEAD-FL may require different evidence; fusion cannot be assumed to recover information the detectors do not observe.

Any later WEAD-FL comparison must hold the architecture, KD strategy, server visibility, proxy data, training budget and attack conditions constant where possible. Its use of continuous scores changes the defence mechanism; any additional signals or data access must be declared and ablated.

The separate WEAD-FL method and frozen attack identifiers are not redefined here. This repository establishes the precursor evaluation and its evidence requirements.

## Unresolved items before execution

- Exact dataset and preprocessing audit.
- Primary calibrated strict-voting configuration, calibration activation and persistence.
- Master pre-training data, optimiser, epochs and S4 warm-start duration.
- Source-target class pair, poisoning fractions, schedules and malicious-client allocation.
- Feasible backdoor trigger and eligible evaluation population.
- Development selection criteria, experiment horizon, tail window and repeated seeds.

No attack or defence settings are selected by assuming a desired outcome.

