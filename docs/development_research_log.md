# EAD–DC–FL development research log

## 25 October 2026: matched FedAvg development and teacher diagnostic

### Scope and provenance

Development experiments only: four rounds, seed 42, 30 fully participating clients, ten per Small/Medium/Deep architecture. No final-test evaluation; final protocol and attack strengths are not frozen. Preprocessing provenance remains unverified. Results below come from uploaded benign and Gaussian reports inspected by the assistant, and user-supplied UWE verification/diagnostic outputs. GPU execution occurs on UWE, not in the assistant workspace.

Branch: codex/matched-fedavg-seed42-20261025.
Matched experiment ID: 5d5868aff5eddd60255a6229546fe6881a50c28bbad1b1ea8bf219a0c005b2b6.
Manifest: data/experiments/idsiot2024/matched_seed42_v1/manifest.json.

### Implementation and controls

- UWE Python 3.12.3, TensorFlow 2.21.0, NVIDIA RTX A1000. GPU discovery and actual GPU matrix multiplication passed. Environment recorded in requirements-linux-gpu.lock.txt.
- Input transfer archive SHA256 matched between Windows and UWE; recorded data, allocation, normalisation and master checks passed.
- Synthetic KD, rollback, Gaussian operator and EAD component checks passed. Twelve matched-experiment unit tests passed.
- Sample-count-weighted FedAvg operates within compatible architecture groups. After screening, coefficients are renormalised over accepted clients. Median remains a separate comparator.
- Conditions: FedAvg; EAD+FedAvg; KD+FedAvg; EAD+KD+FedAvg.
- Shared saved initial states, data allocations, participation order, minibatch orders, master and training budgets. Local training: one epoch, batch 128, Adam learning rate 0.001. KD: three epochs, batch 256, temperature 3.
- EAD: LOF/Isolation Forest/kNN, unanimous rejection, within-architecture standardised flattened weights. Initial contamination 0.20; one rerun at 0.30 when detector outlier counts disagree.
- Original KD: unconditional master warm-start in rounds 1–3; adaptive teacher selection and validation-accuracy guard in round 4. Guarded warm-start is a separate variant.
- Fixed malicious IDs: Small [0,15,24], Medium [16,25,28], Deep [2,11,26]. Nine of 30 clients; three of ten in each group.
- Gaussian attack: after normal local training, add independently seeded noise to submitted weights and biases. Noise seed 242 with client/round-specific streams; labels and server data unchanged. All four rounds attacked.
- Published EAD-FL Section IV-C specifies Gaussian sigma 0.5 and mixed attack assignment. Current sigma 0.05 isolated Gaussian pilots are not a reproduction of the full paper.

### Repeatability

- Zero-noise benign versus attack, EAD off/KD on: all four rounds matched exactly in tensors, metrics and KD decisions.
- All four benign conditions passed matched-input verification; uploaded eight benign/attack reports also matched recorded common inputs.
- Combined sigma 0.05 attack repeated once, preserving the first output folder with suffix _first_run. All cluster records, teachers and round-end tensors matched exactly over four rounds.
- These checks establish same-seed repeatability for the checked configurations/environment, not robustness across independent seeds.

### Round-4 benign validation results

Percentages, accuracy / macro-F1.

| Condition | Small | Medium | Deep |
|---|---|---|---|
| FedAvg | 91.38 / 77.45 | 82.55 / 73.32 | 93.91 / 83.60 |
| EAD+FedAvg | 91.41 / 77.47 | 82.59 / 75.06 | 93.80 / 83.40 |
| KD+FedAvg | 90.78 / 87.03 | 92.18 / 88.90 | 88.62 / 82.48 |
| EAD+KD+FedAvg | 90.99 / 86.62 | 84.54 / 79.31 | 88.18 / 81.79 |

EAD rejected 11/120 benign client-round submissions without KD and 14/120 with KD. These are repeated submissions, not independent replications. Original warm-start can reduce accuracy: round-1 KD-only Medium 85.22 to 63.57%, Deep 84.99 to 64.42%.

### Round-4 Gaussian sigma 0.05 validation results

| Condition | Small | Medium | Deep |
|---|---|---|---|
| FedAvg | 91.34 / 76.11 | 82.61 / 73.39 | 93.25 / 83.43 |
| EAD+FedAvg | 91.75 / 76.43 | 82.33 / 71.95 | 93.30 / 82.58 |
| KD+FedAvg | 91.24 / 86.86 | 91.46 / 88.10 | 91.68 / 88.04 |
| EAD+KD+FedAvg | 70.96 / 61.68 | 88.46 / 82.55 | 83.88 / 69.84 |

EAD rejected 17/36 malicious submissions without KD, 16/36 with KD, and 0/84 benign submissions in either attack condition. Calibration was not triggered in these attack runs. Plain FedAvg accuracy degradation was limited at this exploratory strength.

### Controlled round-4 teacher diagnostic

Script: scripts/diagnose_round4_teachers.py.
Output: outputs/development/matched_fedavg_5d5868aff5ed_gaussian_sigma0p05_attack_original_ead_on_kd_on_seed42_teacher_diagnostic_v1/report.json.

Reconstructed round 4 from original round-3 checkpoints. Reconstruction records matched; original Medium-teacher replay passed exact metrics/tensor checks before completion. Frozen teacher snapshots and identical student initial tensors, KD inputs, per-student order seeds and budgets were used for Medium versus Deep. Self-distillation was skipped, recorded with accepted=null.

User-supplied terminal output, accuracy / macro-F1 percentages:

| Teacher | Student | Accepted | Committed accuracy | Committed macro-F1 |
|---|---|---|---|---|
| Medium | Small | Yes | 70.9605 | 61.6822 |
| Medium | Medium | Self skipped | 88.4605 | 82.5513 |
| Medium | Deep | Yes | 83.8816 | 69.8417 |
| Deep | Small | Yes | 90.9868 | 86.7166 |
| Deep | Medium | Yes | 92.2237 | 88.6944 |
| Deep | Deep | Self skipped | 81.5526 | 81.8965 |

Interpretation: teacher choice materially changes immediate KD outcomes for fixed Small students. Deep-to-Deep is a no-KD control, not an alternative distillation result. Both Medium-to-Small and Medium-to-Deep increased accuracy while decreasing macro-F1; the accuracy gate therefore does not protect macro-F1 or class recall. This does not establish malicious behaviour transfer or a universal Deep-teacher advantage. All groups were attacked, so clean-recipient propagation is not isolated. The full diagnostic JSON has not yet been uploaded for assistant inspection.

### Next registered development step

Run the same four component conditions at Gaussian sigma 0.5, original mode and sample-weighted FedAvg, reusing the existing matched manifest and benign controls. This aligns the stated noise standard deviation with EAD-FL, not its full experimental protocol. Preserve all sigma 0.05 results. Do not select a final strength or claim robustness from these pilots.

After completion: verify matching, inspect per-round screening confusion counts, class recall, pre/candidate/committed metrics, teachers and gate decisions. Do not use final-test data. Defer choosing a revised teacher or guard policy until the development evidence is assessed.

### Remaining thesis evidence

Independent seeds, justified training duration, targeted/held-out attacks, benign statistical heterogeneity, proxy/master-supervision controls, detector/calibration ablations, costs and independent evaluation remain outstanding. Guarded warm-start and alternative selection/gating policies must retain separate identities. Existing duplicate/conflicting-label and preprocessing limitations remain unresolved. No novelty, formal privacy, general robustness or generalisation claim follows from this log.


### Gaussian sigma 0.5 analysis, 25 October 2026

Assistant inspected all four uploaded sigma 0.5 JSON reports and the full teacher diagnostic JSON. All four Gaussian runs completed four rounds; recorded common hashes, initial states, environment, KD rows and budgets matched the benign controls. Diagnostic status completed and original_teacher_replay_exact=true.

Round-4 validation percentages, accuracy / macro-F1:

| Condition | Small | Medium | Deep |
|---|---|---|---|
| FedAvg | 58.80 / 40.36 | 51.21 / 34.88 | 52.21 / 34.86 |
| EAD+FedAvg | 77.12 / 53.77 | 65.00 / 60.33 | 59.86 / 52.22 |
| KD+FedAvg | 63.20 / 53.27 | 62.66 / 43.99 | 64.97 / 52.96 |
| EAD+KD+FedAvg | 66.11 / 52.75 | 73.37 / 56.98 | 58.42 / 47.92 |

Plain FedAvg accuracy losses against its benign control: Small 32.58, Medium 31.34, Deep 41.70 percentage points. EAD without KD rejected 15/36 malicious submissions and 0/84 benign submissions; EAD with KD rejected 19/36 and 0/84. Calibration triggered in one of 12 group-rounds with EAD+KD, none with EAD alone. Counts are descriptive repeated client-round observations.

EAD improved accuracy and macro-F1 over unprotected FedAvg in each group under this attack. The combined method was not uniformly best: EAD-only had higher Small accuracy, Deep KD-only had higher accuracy, and combined Small/Deep macro-F1 was below both EAD-only and KD-only. Combined round-4 Medium-teacher KD increased Small accuracy 65.00 to 66.11% while reducing macro-F1 57.64 to 52.75%; Deep accuracy increased 57.78 to 58.42% while macro-F1 fell 50.42 to 47.92%. These are repeated examples of the metric-specific guard limitation.

Targeted Malware-to-Normal rates in Gaussian runs are descriptive error rates, not attack success for a targeted objective. For example EAD-only Deep had 55.81% Malware-to-Normal error despite an untargeted attacker. Accuracy alone therefore conceals security-relevant class errors.

Next: matched targeted label-flipping study using saved poisoned rows and malicious identities. Execute same-runner benign and attack conditions so baseline reuse across runners is verified rather than assumed. Preserve data, manifest, original KD policy and all previous outputs. Freeze a preliminary viva evidence package by Tuesday 27 October, ahead of Thursday 29 October; do not present it as completed confirmatory thesis evaluation. Independent-seed confirmation remains conditional on implementing appropriate manifests and budgets, not reusing seed42 with only a label change.


### Source recovery and fidelity correction, 25 October 2026

Original uploads were already available and have now been re-inspected directly. Earlier requests to resend them were unnecessary.

- upload/main(1).ipynb: EAD experiments, 69 cells, SHA256 cb06863e311c06d27b256e264476894e70b4bfc4934bf8e10fa7026718c6e291.
- upload/main.ipynb: DC prototype, 15 cells, SHA256 0fdb5e439a23fa5de3f557f85a8a3775fcf58ab4b107639628fcddd8261fb05f.
- upload/utility.py and upload/client_models.py: historical helpers, also archived under references/legacy in the repository.
- Earlier docs/dependencies_and_source_audit.md already documented source/paper differences. These are research notebooks, not proven authoritative scripts for every published result. Static review only; original notebooks have not been rerun.

All cell references below are physical one-based notebook positions, not execution counts.

Critical EAD difference:
In EAD notebook cells 24, 25 and 27, first-round calibration checks strict_count <= min(adjusted_counts), where strict_count is the five-detector intersection and adjusted_counts contains four individual detector counts. The intersection count cannot exceed any of those individual counts, so this condition always holds for valid binary flags, including equality. It raises contamination to 0.30 and persists that value in later rounds. Cell 25 immediately reruns detectors; cells 24/27 change the value without an immediate rerun. This differs from the paper's count-range rule and the current integration's per-round reset to 0.20 followed by a rerun only when counts disagree. Do not describe the integration as code-identical EAD-FL.

Other verified EAD differences:
- Legacy cells use fit followed by predict(flat_scaled)/decision_function(flat_scaled); integration uses fitted labels_/decision_scores_. Numerical equivalence is not established.
- Legacy neighbour count max(2,n_clients//2), IForest seed42; integration neighbours5 and round/group-specific seeds. Neighbour counts agree at ten clients.
- Legacy cells train three local epochs, batch32, model hidden128/64 with BN/dropout and AdamW (cell3); current architecture-specific pilots use one epoch, batch128, Adam.
- Legacy calibrated cells fit five detectors; downstream selected voting and aggregation vary: cell24 five-strict mean, cell25 three-strict median, cell27 three-strict mean. Current uses three-strict sample-weighted FedAvg.
- Legacy attack helper cell5 adds Gaussian sigma0.5 through global NumPy RNG without preserving original dtype explicitly; integration has independent client/round streams and preserves dtypes.
- Legacy sweeps assign sign-flip or Gaussian randomly, not Gaussian alone. Label flipping is absent from the inspected helper despite the paper describing it.
- Legacy IID allocations independently subsample a shared pool and can overlap, whereas current allocations are disjoint. Do not restore this design as a purported correction.
- Cell25 stored output terminates in a ValueError. Saved source/output states and published table provenance must not be assumed identical.

Verified current sigma0.5 EAD-only per-cluster counts over four rounds:
Each group has 12 malicious submissions and 28 benign submissions. For Small, Medium and Deep separately, each individual detector LOF/IForest/kNN has TP8/FN4/FP0/TN28. The three-strict ensemble has TP5/FN7/FP0/TN28 in each group. Thus individual count agreement conceals identity disagreement, and strict intersection loses detections. These are descriptive repeated-submission counts, not independent replication.

DC prototype differences:
main.ipynb cells13/15 use deepest-group teaching, rather than the integration's master warm-start plus adaptive accuracy-guard policy. Cells7/11/13 show softmax model outputs subsequently treated/softened as logits; cell15 assumes linear outputs without establishing that in builders. Uploaded helpers define additional architectures that differ from notebook-local builders and paper architectures. The integration is a documented reconstruction/adaptation, not direct script reuse.

Priority correction:
Preserve completed runs as paper-rule integration pilots. First audit EAD per cluster with KD disabled; compare separately named notebook-calibration, paper-calibration and fixed0.30 controls on identical submitted models. Keep prediction API and three/five detector effects distinguishable. No claim that the calibration mismatch fully explains the performance gap until controlled evidence exists. Retain the safe data split, dtype and numerical corrections. Do not silently modify the original runner or regenerate the shared manifest. The exact cells/checkpoints/CSV mapping behind published results remains unresolved.


### EAD fidelity diagnostic results, 25 October 2026

Inspected uploaded ead_fidelity_reports.tar.gz containing completed benign sigma0 and attack sigma0.5 reports. KD disabled; all four reconstruction/baseline checks passed in each report. Each alternative screens the same original uploads. Alternative aggregated models do not feed future rounds. This is an immediate screening/aggregation diagnostic, not an independently trained alternative trajectory.

Aggregate confusion counts (attack TP/FN/FP/TN; benign FP out of120):

| API | Calibration | Ensemble | Attack counts | Benign FP |
|---|---|---|---|---|
| fitted labels | paper count range | 3-strict | 15/21/0/84 | 11 |
| fitted labels | paper count range | 5-strict | 15/21/0/84 | 2 |
| fitted labels | legacy cell25 | 3-strict | 36/0/0/84 | 16 |
| fitted labels | legacy cell25 | 5-strict | 36/0/0/84 | 4 |
| predict | paper count range | 3-strict | 36/0/0/84 | 14 |
| predict | paper count range | 5-strict | 36/0/0/84 | 3 |
| predict | legacy cell25 | 3-strict | 36/0/0/84 | 15 |
| predict | legacy cell25 | 5-strict | 36/0/0/84 | 3 |

Fixed0.30 gives the same reported confusion counts as legacy cell25 for the corresponding API and ensemble in both arms. This demonstrates no advantage of the legacy trigger over fixed0.30 on these uploads.

For every attacked group/round, three-detector initial counts are [2,2,2] using fitted labels, versus [0,2,2] using predict. LOF produces the observed count difference. The count-range trigger therefore activates in all12 group-rounds with predict and in none with fitted labels. After rerunning at0.30, predict+paper policy has TP12/FN0/FP0/TN28 within each architecture across four rounds. The five-detector version offers no extra malicious detections here but fewer benign false rejections: 3/120 versus14/120. These are repeated-submission counts, not independent replications.

Round4 attack candidate accuracy on original uploaded-model trajectory: baseline fitted+paper 3-strict Small77.12%, Medium65.00%, Deep59.86%; predict+paper (3 or5) Small89.18%, Medium78.43%, Deep88.50%. These are immediate candidate aggregate metrics on an inherited trajectory and must not be presented as final results of four-round training under the alternative policy. Previous contamination may remain embedded in benign uploads.

Interpretation correction: initial poor screening cannot be attributed simply to EAD-FL failing under architecture heterogeneity. A substantive prediction-API adaptation changed the calibration dynamics. The observed difference does not establish predict as universally superior, nor justify the legacy always-true trigger. Original package environment and exact source-to-published-result mapping remain unresolved.

Next recommended bounded confirmation: register a separately named predict+paper-count-range configuration, with current seeds and all other settings held fixed; first run EAD+FedAvg benign/attack without KD. Preserve fitted-label originals and contract-bound source hashes. Retain 3-strict as primary fidelity comparison; evaluate 5-strict as a labelled secondary configuration because its benign false-rejection benefit is development-selected. Reintroduce KD only after end-to-end screening behaviour is verified. Do not silently relabel original runs or choose contamination using the known malicious fraction.


### End-to-end EAD predict confirmation, 26 October 2026

Inspected both reports from uploaded ead_predict_confirmation_reports.tar.gz. Both completed four rounds; configuration ead_predict_paper_3strict_v1, EAD on, KD off, FedAvg. Verified original common input fields, initial weights, data hashes, training settings, runtime environment, attack protocol and actual participation/minibatch-order records match corresponding originals. base_runner_sha256 matches original script hash. First-round candidate metrics and rejected IDs exactly match the earlier fixed-upload predict+paper three-detector diagnostic, in both arms.

Attack sigma0.5: TP36/FN0/FP0/TN84 across four rounds. Each architecture TP12/FN0/FP0/TN28. Every group-round initial counts [0,2,2], calibration rerun at0.30, three malicious models rejected. Detection precision/recall/F1 are1.00 and benign rejection0 in this attack pilot. These are36 repeated submissions from nine compromised clients, not36 independent adversaries or runs.

Benign sigma0: FP14/TN106 out of120 submissions (11.67%); Small4/40, Medium5/40, Deep5/40. Calibration triggered in7/12 benign group-rounds. Therefore disagreement is not a reliable indication of malicious presence by itself. This study does not isolate the effect of calibration from a no-calibration alternative on the new trajectory.

Round4 validation percentages, accuracy / macro-F1:
- New benign: Small91.39/77.46, Medium82.59/75.06, Deep94.05/83.68.
- New attack: Small91.36/77.44, Medium82.47/73.24, Deep94.07/82.90.
- Old fitted-label EAD attack: Small77.12/53.77, Medium65.00/60.33, Deep59.86/52.22.

Despite perfect malicious filtering, the new attack run is not identical to its benign control: attack rejects all nine compromised clients, whereas benign includes their honest contributions unless screened. It consequently trains on different accepted data. Medium attack macro-F1 is1.83 points below matched new benign. Small Injection recall remains0 in both new arms. Perfect detection does not imply perfect utility, all-class security or generalisation.

Conclusion: same inputs and independently evolving trajectories support the prediction/calibration fidelity finding, with substantially better attack-run utility than the old fitted-label variant in this seed. This is not exact reproduction of the published experiment, nor final independent confirmation: configuration selection used earlier development observations. Both four-round runs are validation-only; final test remains untouched.

Next: retain this named three-detector predict+paper configuration as the working fidelity configuration. Reintroduce original-mode KD in a separately named matched benign/attack pair after removing the runner's intentional KD-off restriction through a reviewed new variant; the current command cannot enable KD. Defer broad H_P expansion until integration behaviour is assessed. Preserve old fitted-label runs as implementation-sensitivity evidence. Consider a benign control excluding exactly the compromised identities if later needed to separate filtering-composition effects from poisoning damage. Five-strict remains a secondary option requiring end-to-end benign/attack evaluation. Independent seeds, stronger/held-out threats and adequate training duration remain outstanding.


### Predict EAD plus original KD confirmation, 26 October 2026

Inspected benign/attack reports in ead_predict_kd_confirmation_reports.tar.gz. Both completed four rounds. Shared input fields, initial tensors, training settings, runtime environment, master/data/model/attack hashes, attack protocols and KD row allocations match corresponding KD-off predict runs. Actual participation and local row orders match. Round1 initial/final screening records and pre-KD metrics exactly match KD-off runs, confirming same-round screening independence from later KD.

Attack sigma0.5: TP36/FN0/FP0/TN84. Every architecture/round rejects all three poisoned submissions; calibration triggers in12/12 group-rounds from initial [0,2,2] to contamination0.30. Benign KD-on FP12/TN108 out of120 submissions (10%); calibration7/12 group-rounds.

Round4 percentages, accuracy / macro-F1:
- KDoff benign Small91.39/77.46, Medium82.59/75.06, Deep94.05/83.68.
- KDon benign Small91.09/86.83, Medium84.54/79.31, Deep88.39/81.92.
- KDoff attack Small91.36/77.44, Medium82.47/73.24, Deep94.07/82.90.
- KDon attack Small69.88/61.70, Medium84.66/79.71, Deep83.87/70.50.

Original master warm-start still causes large immediate accuracy reductions despite complete screening: attack round1 Medium85.03 to63.53%; Deep85.96 to62.20%. It is accepted unconditionally by design.

Round4 attack selects Medium, while benign selects Deep. Medium-to-Small KD increases accuracy68.68 to69.88% but reduces macro-F1 68.73 to61.70%; Medium-to-Deep increases accuracy81.13 to83.87% but reduces macro-F1 81.28 to70.50%. MITM recall drops from62.22% pre-KD to0 post-KD in both student groups. The accuracy guard accepts both. Benign Medium candidate accuracy81.05% <84.54% is rejected although macro-F1 increases79.31 to80.53%.

Interpretation: screening success and KD utility are separate. No poisoned submission enters the attack aggregates in this pilot. Therefore low final utility must not be presented as evidence of poisoning propagated through accepted malicious uploads. Attack-arm aggregates retain seven clients/group, whereas benign screening retains different client sets. Missing contributions and resulting optimisation/teacher-selection trajectories can explain differences; these mechanisms need controls.

Next essential diagnostic: an explicitly labelled benign/oracle-mask control that uses clean local models but the exact accepted IDs from the attack run, with same initial states, row orders, budgets and original KD. Evaluate whether accepted aggregate tensors, teacher choices and committed tensors match the attacked run. True malicious identities or attack-derived masks are diagnostic-only controls, never deployable policy inputs. Do not call this attack leakage if it matches.

Then evaluate guarded warm-start as a separate variant to address unconditional master-KD damage. Accuracy gating alone still does not protect macro-F1 or minority classes; do not claim it solves all failures. Any new teacher/gate metric requires its own development/independent evaluation. Existing original/predict results remain preserved; four-round one-seed validation evidence is preliminary.


### Clean reference-mask control completion, 26 October 2026

User supplied terminal completion: CLEAN REFERENCE-MASK CONTROL: COMPLETE; sigma0, original mode, no final test, no final protocol freeze. The saved path was truncated in the message. Full control report has not yet been uploaded or independently inspected.

Given the published control's fail-on-first-mismatch logic, reaching completion indicates all four round comparisons passed for teacher/phase/participation, row orders, local losses, accepted sample counts and coefficients, pre-KD metrics, candidate KD losses/metrics, acceptance decisions, committed metrics and exact committed tensor arrays. This is inferred from the executed script's completion condition, not a fresh inspection of the resulting JSON.

The clean control has no poisoning and no EAD execution; it applies exact accepted-client lists from the completed predict-EAD+original-KD attack. Therefore the poor trajectory is reproducible without any poisoned uploads when retained contributions are matched. This supports an attribution to the retained-client learning/KD process rather than residual poisoned uploads in this specific Gaussian seed42 experiment.

It does not establish that removing three clients alone causes the degradation, that EAD is generally robust, or that KD is universally harmful. Original master warm-start and accuracy-only gate remain separate utility limitations, already evidenced directly by pre/candidate/committed metrics.

Next bounded comparison: separately identified guarded warm-start with predict EAD, keeping data, seed, screening and KD budgets matched; compare benign and attack arms against original mode. Apply accuracy acceptance during rounds1–3 rather than unconditional commitment. Retain accuracy guard limitations for macro-F1/minority recall; do not change teacher metric and warm-start guard simultaneously. First inspect control reference_comparisons or upload its report to archive verification.


### Guarded predict-EAD KD results, 26 October 2026

Inspected ead_predict_guarded_reports.tar.gz, both completed four-round reports. Common recorded inputs/initial tensors/master/environment/budgets/attack protocols match corresponding original-mode predict-KD reports. Actual participation/row-order hashes match. Round1 initial/final screening, pre-KD metrics and KD candidate metrics exactly match original mode, isolating the initial acceptance-policy difference. For every performed KD attempt, validation_accuracy_guard is recorded, accepted==(candidate_accuracy>=pre_accuracy), committed metrics equal accepted candidate or pre-KD metrics as appropriate, and committed accuracy>=pre-KD accuracy. This is report-level validation; guarded checkpoint rollback tensors have not been independently loaded here.

Each arm rejects8/9 master warm-start candidates, accepting only Small round1. Benign overall KD decisions:1 accepted,10 rejected,1 self-distillation skip. Attack:2 accepted,9 rejected,1 skip. EAD attack TP36/FN0/FP0/TN84, calibration12/12; benign FP15/TN105 (12.5%), calibration6/12.

Round4 percentages, accuracy / macro-F1:
- Guarded benign Small71.93/74.97, Medium82.59/75.06, Deep94.05/83.68.
- Guarded attack Small72.87/61.41, Medium82.47/73.24, Deep94.07/82.90.
- Original predict-KD attack Small69.88/61.70, Medium84.66/79.71, Deep83.87/70.50.
- Predict EAD KDoff attack Small91.36/77.44, Medium82.47/73.24, Deep94.07/82.90.

Immediate guard works as specified: attack round1 rejects Medium63.53% candidate and preserves85.03%, rejects Deep62.20% candidate and preserves85.96%. But this does not establish better final trajectories for all groups.

Small round1 master-KD increases accuracy57.65 to66.45% and is accepted. Despite later guarding, final Small accuracy72.87% remains18.49points below KDoff91.36%. Do not attribute this single-seed trajectory effect solely to one update without the relevant fixed-intervention control.

Attack round4 Deep-to-Small KD increases accuracy69.54 to72.87% but reduces macro-F1 71.18 to61.41%; MITM recall is0 after KD. Thus harmful class/metric trade-offs occur even with Deep teaching and guarded warm-start. Medium candidate is rejected although macro-F1 improves73.24 to74.22%, because accuracy falls82.47 to82.30%.

Conclusion: guarded warm-start prevents the specified immediate validation-accuracy declines, preserves Medium/Deep KDoff-equivalent final results in this attack pilot, but does not establish beneficial KD overall or protect macro-F1/minority recall. It is a methodological variant, not a complete solution or formal no-harm guarantee. Validation is reused for decisions; independent performance remains unverified. All settings one development seed/four rounds/full participation/IID client allocations.

Priority: freeze the bounded Gaussian development analysis and preserve original/guarded identities; collect pending targeted reports and clean-control JSON before launching more changes. Further teacher/gate optimisation requires predeclared criteria and independent evaluation; do not keep selecting variants on these same results. Hypotheses for future work include objective alignment, proxy/master distribution, insufficient horizon and transfer suitability, not established causal diagnoses.


### Targeted study and clean-control report inspection, 26 October 2026

Inspected targeted_and_clean_control_reports.tar.gz: eight targeted runner reports and one clean reference-mask report. All completed. Targeted common experiment ID, initial tensors, data/master/model hashes, budgets, runtime environment, KD rows, actual participation and minibatch orders match. All eight targeted script hashes are c910bd09ded185a06152ef22f31f5041b68c0d1c356de3a0e4d473a2925753b7, matching the inspected run_targeted_development_pilot.py source. It uses fitted labels_/decision_scores_, not the revised predict API. Keep these results as historical fitted-label EAD pilots; they cannot validate revised EAD on targeted poisoning.

Across all four benign targeted configurations and all rounds, pre/post KD metrics, KD records, teachers and rejected IDs exactly match the corresponding original Gaussian benign runner reports. This confirms recorded benign cross-runner behaviour; checkpoint arrays were not included for independent comparison.

Attack protocol: 9 fixed malicious clients,3 per architecture, all4 rounds. 100% of each compromised client's Malware rows are relabelled Normal;1497 distinct allocated training rows total per round (Small500, Medium499, Deep498). Features, other labels, server/evaluation labels unchanged. Repeated epochs/round exposures are not distinct poisoned observations. Source_label_poison_fraction1.0 is conditional on local Malware class, not all local data.

Crucial trajectory result: unprotected FedAvg attack TMR%, rounds1–4:
- Small17.23,9.49,9.49,0.
- Medium22.10,12.48,1.87,0.
- Deep40.20,33.33,15.48,0.125.
Matched benign TMR0 in each case. Therefore the targeted attack has pronounced early effects but little persistent final source-to-target error in this4round configuration. Do not call it ineffective solely from final results.

Fitted-label EAD without KD attack TMR%, rounds1–4:
- Small5.12,0,0,0.
- Medium10.99,0.50,0,0.
- Deep10.99,0.37,13.98,0.
EAD mitigates but does not uniformly remove transient targeted error (Deep round3 still13.98%). Screening TP17/FN19/FP0/TN84 across rounds. With original KD, TP16/FN20/FP0/TN84.

Original KD-only post-KD TMR closely matches benign across rounds, apart from Small final0.375 vs benign0.250%. Combined fitted-label EAD+originalKD post-KD TMR matches corresponding benign across rounds, final2/801=0.250% eachgroup. This may reflect trusted master supervision and requires utility/central-data controls; not proof that EAD alone supplies the benefit.

Round4 targeted attack accuracy/macro-F1%:
- FedAvg Small91.67/77.78, Medium81.78/74.95, Deep93.05/82.28.
- EAD+FedAvg Small91.59/77.71, Medium81.87/75.05, Deep93.01/82.40.
- KD+FedAvg Small90.88/87.64, Medium84.24/78.78, Deep88.83/81.76.
- EAD+KD+FedAvg Small91.57/88.06, Medium92.36/89.25, Deep92.70/89.04.

Despite final TMR near0, FedAvg Medium Malware recall91.01% vs99.63% benign; Deep90.64% vs99.63%. EAD-only Medium/Deep91.14% vs99.63%. Malware may be misclassified as classes other than Normal. Evaluate full confusion matrices before identifying those destinations; no such confusion matrix inference is made here.

Clean-mask JSON now inspected: status completed, configuration clean_reference_mask_kd_v1, all4 reference_comparisons exact_match=true, mismatches empty. This independently confirms the saved verification record, based on script comparisons; original tensor files themselves were not uploaded. Preserves conclusion that revised Gaussian EAD+originalKD trajectory can be reproduced with no poisoning under matched retained contributors.

Next priorities: consolidate trajectories and metric trade-offs; collect original protocol/checkpoint metadata and classify revised-predict targeted evaluation as outstanding. A bounded revised EAD targeted benign/attack comparison is needed before claiming the current working integration is validated on both poisoning families. Preserve original versions and avoid universal superiority or novel-method claims.


### Revised predict-EAD targeted confirmation, 26 October 2026

Inspected four reports in targeted_predict_confirmation_reports.tar.gz: benign/attack crossed with KDoff/originalKDon, EADon/FedAvg. All completed4rounds. Shared initial tensors/experiment/data/master/model/budgets/environment/KD rows and actual participation/minibatch orders matched. Both benign trajectories exactly match corresponding Gaussian predict benign reports in teacher choices, initial/final screening, pre/post KD metrics, KD records and rejection lists.

Targeted attack Malware-to-Normal on saved1497 training rows in nine compromised clients per round, three per architecture. Revised three-detector predict API with per-round count-range calibration. All12 attack group-rounds triggered calibration to0.30, but complete detection did not always follow.

Attack screening counts:
- KDoff TP30/FN6/FP0/TN84; recall83.33%. Per-group TP Small12/12, Medium11/12, Deep7/12.
- KDon TP32/FN4/FP0/TN84; recall88.89%. Per-group TP Small11/12, Medium11/12, Deep10/12.
These are repeated submissions, not independent runs. Later KDoff/KDon detection differences arise on their respective training trajectories, not a direct same-round KD change to EAD.
Benign FP14/120 KDoff, FP12/120 KDon, matching Gaussian predict benign controls.

KDoff targeted excess TMR against benign:
Small0 across4rounds; Medium0.499percentage points in round1 then0; Deep0 until round3, then11.111percentage points (89/801) in round3, returning0 in round4. Deep round3 missed2/3 malicious submissions. Round4 Malware recall remains91.14% in Deep versus99.63% benign despite TMR0. Need all-class metrics/confusion for error destinations.
Original-KDon post-KD excess TMR0 for every group/round. Final absolute TMR2/801=0.2497% eachgroup, equal to corresponding benign; absolute errors remain. This supports a conditional targeted-error result, not general security.

Final attack validation accuracy/macro-F1 percentages:
- EAD+FedAvg: Small91.36/77.44, Medium82.46/73.23, Deep93.01/82.40.
- EAD+originalKD+FedAvg: Small90.71/85.92, Medium91.63/87.44, Deep88.07/81.70.
Corresponding benign KDon Small91.09/86.83, Medium84.54/79.31, Deep88.39/81.92. Medium attack accuracy exceeding benign is a trajectory observation, not a benefit-of-poisoning claim.
KD improves macro-F1 versus KDoff for Small/Medium but Deep accuracy/F1 fall and Small accuracy slightly falls. Master warm-start still unconditionally commits large first-round declines: Medium84.28 to63.18%, Deep85.24 to64.45%. Server supervision and teacher/gate controls remain necessary.

Across completed pilots:
Predict EAD detects all36 Gaussian sigma0.5 submissions in checked modes but only30/36 or32/36 label-flipped submissions. Successful calibration activation is not sufficient for universal detection. Gaussian and label flipping should not be conflated as equally detectable.
The bounded development package now covers revised EAD/aggregation with and without original KD for both poisoning families, plus Gaussian guarded variant and attribution/teacher/fidelity diagnostics. Guarded targeted behaviour remains unevaluated. No final protocol/test evaluation, independent seeds, adequate convergence study, non-IID integration study or H_P execution has been completed.

Priority: consolidate viva evidence using explicit implementation/variant labels; avoid further ad hoc gate changes. Distinguish source fidelity corrections from proposed methods and state unresolved original package/provenance and data-quality limitations. Choose a frozen confirmatory design only after the viva development package is reviewed.


### Twelve-round matched Gaussian batch, seed 42, 26 October 2026

Inspected replication_seed42_rounds12_reports.tar.gz: manifest plus all eight benign/attack crossed EAD/KD reports, completed rounds 1–12, experiment 33fc67b96cead72110ff9613e42c2c9e9f127f56fec055555bc03f6a902fd9dd. Recomputed manifest ID; shared matched-run fingerprint, actual participation, row-order hashes, initial tensors and registered runner hash agree. Checked survivor sample counts/FedAvg coefficients and upload/screening audit consistency. All eight first-four-round JSON trajectories and recorded checkpoint hashes match the corresponding earlier reports. One report additionally records successful runtime exact-prefix checks. Uploaded arrays were absent, so no independent checkpoint-array reload was performed.

Attack screening: both EAD-only and EAD/KD TP108/FN0/FP0/TN252, calibration36/36 architecture-rounds. Clean false rejections: EAD-only42/360 (11.67%); EAD/KD37/360 (10.28%). Repeated submissions are not independent replications.

Round12 attack accuracy/macro-F1%:
- FedAvg: Small77.61/48.84, Medium68.42/41.70, Deep35.18/27.25.
- EAD/FedAvg: Small96.68/88.93, Medium83.62/78.95, Deep90.68/79.00.
- KD/FedAvg: Small92.03/82.89, Medium88.62/70.97, Deep87.08/68.13.
- EAD/KD/FedAvg: Small86.28/85.27, Medium86.08/85.24, Deep86.68/85.65.

Combined Small round4/8/12 accuracy 69.88/93.66/86.28% shows horizon dependence and fluctuation, not convergence. Combined method does not dominate. Clean Medium EAD-only macro-F1 75.67% versus FedAvg83.79%, with MITM recall62.22% versus100%, warrants explicit benign-cost reporting. Accuracy-accepted KD can reduce macro-F1; round4 combined attack Small accuracy +1.20pp/F1 -7.03pp, Deep accuracy +2.74pp/F1 -10.78pp. All attack uploads are excluded in screened Gaussian runs, so retained poisoned aggregation inputs cannot explain their remaining utility differences. The four-round mask replay was not extended here.

All final-test/protocol-freeze flags remain false and provenance verification unresolved. No new targeted, non-IID or participation-heterogeneity results in this archive. Full tables, verification limits and measured elapsed times are in [replication_seed42_rounds12_results.md](replication_seed42_rounds12_results.md).

Eight runs total169.9 minutes, approximately2h50. Next recommended bounded step: same frozen12round eight-cell Gaussian/benign batch for predeclared training/noise seeds2026 and31415, approximately5h40 additional at observed runtime. Fixed data/master/compromised IDs limit replication scope. Preserve seed42 outcomes and avoid method changes or best-round selection in response to them.


### Completed three-seed twelve-round Gaussian replication, 27 October 2026

Inspected the new replication_additional_seeds_rounds12_reports.tar.gz and seed42 archive together: three manifests and24reports, eight matched cells per seed42/2026/31415, all completed12rounds. Manifest IDs recomputed; within-seed matched inputs, actual cohorts/order hashes, initial tensor hashes, sample-weighted survivor coefficients, upload/screening audit consistency, strict voting/calibration triggers and KD acceptance/committed metrics verified. Cross-seed source/configuration/runtime hashes, data/master/compromised selection, client allocations, participation and budgets agree. Gaussian sigma0.5, noise seeds trainingseed+200 and three active compromised clients per group verified. No checkpoint/data arrays were independently reloaded from these JSON-only result archives.

Attack final macro-F1%, mean ± sampleSD across3runs:
- FedAvg Small53.73±5.09, Medium43.32±12.06, Deep40.38±11.83.
- EAD/FedAvg Small79.36±8.28, Medium76.32±2.62, Deep77.98±1.25.
- KD/FedAvg Small78.70±3.98, Medium64.81±7.29, Deep65.70±4.77.
- EAD/KD/FedAvg Small84.88±0.45, Medium85.19±0.18, Deep85.15±1.17.

Each screened configuration pools TP324/FN0/FP0/TN756 across the3seeds, calibration108/108 architecture-rounds. These are repeated client-round submissions, not324 independent replications. Clean false rejections EAD-only136/1080=12.59%, EAD/KD120/1080=11.11%.

Important update to seed42-only interpretation: adding KD to EAD improves Medium/Deep attack macro-F1 in all3seeds, Small in2/3. Small KD-induced accuracy/F1 losses in seed42 do not persist as the same sign in both new seeds. Combined method has highest mean attack macro-F1 for all architectures among these four methods at fixed12rounds; it does not dominate accuracy or all individual runs. Accuracy-accepted adaptive KD reduces macro-F1 in all3combined attack runs at some rounds. Benign rejection persists. Gaussian noise/model L2 ratios roughly2.86–7.29 in screened runs, so complete detection is conditional on a conspicuous perturbation regime.

Replication varies initialisation/training/noise/EAD seed only, conditional on fixed IID partition/master/compromised identities. Finaltest and finalfreeze remainfalse, provenance unresolved. Three runs give descriptive repeatability evidence, not broad statistical superiority or generalisation. Both data/validation selection dependencies and trusted master supervision require qualification.

All24 recorded elapsed times total8.41hours. Gaussian package complete; no more Gaussian seeds or threshold/gate changes recommended for the viva package. Next bounded extension: same12round four-cell targeted attack batch for each existingseed,12newruns, reusing same-component benigncontrols, estimated4–5hours. Pre-specify finalmetrics, per-round pre/postKD TMR and per-run mean/maximum excessTMR to preserve transient effects. Existing runner already supports this without changing manifest-bound source. Then consolidate rather than adding conditions before viva preparation.

Full tables and claim limits: [replication_three_seed_rounds12_results.md](replication_three_seed_rounds12_results.md).
