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


### Targeted12round three-seed evaluation and main-package completion,27October2026

Inspected replication_targeted_three_seeds_rounds12_reports.tar.gz (SHA25607ddd496dbd62fdaaddad7bba9583782be3c817f96b1ce5258bb5d9c987b6c79). All12targeted reports completed12rounds. Combined with previous24reports, all36main development runs pass within-seed matched fingerprints, manifest/initial tensor/runner hashes, cohorts/orders, survivor coefficients, screening votes/calibration and KD commitment checks. Recorded targeted execution changes1497training labels per round (Small500/Medium499/Deep498), exactly the saved nine clients, with no Gaussian noise. Underlying data/poison arrays/checkpoint tensors were absent, so this remains report/source verification.

Label-flipping screening:
- EAD-only TP293/FN31/FP0/TN756, recall90.43%, calibration108/108group-rounds.
- EAD/KD TP287/FN37/FP3/TN753, recall88.58%, calibration105/108.
KD follows screening within each round; later screening differences are trajectory-dependent, not a direct alteration of current-round EAD decisions.

Combined postKD Malware-to-Normal TMR equals the same-seed/same-component benign value at all108seed/architecture/round observations. Absolute errors remain, commonly2/801=0.2497%. This supports a bounded measured-security conclusion, not universal robustness or absence of other poisoning effects.

Critical transient failure: seed42 Deep EAD-only round7 accepts all3attackers despite calibration0.20->0.30. LOF flagsnone, IForest[2,14,26], KNN[2,11,26]; strictintersectionempty. TMR424/801=52.93% vsbenign1/801, excess52.81pp. Final-round security summaries would hide this failure.

Critical transfer/gate failure: seed42 KD-only round6, Deepteacher44/801targeterrors; Medium2->45/801targeterrors afterKD while accuracy83.57->84.91% and macro-F181.36->83.12%. Candidate accepted. This directly shows accuracy and macro-F1 gains can coexist with worse targeted security. Counts are consistent with transfer, without proving identity of affected examples. Opposite trade-off: seed2026 KD-only Deep round5 candidate113->6targeterrors butaccuracy84.03->80.83%, rejected.

Targeted finalmacro-F1 mean±sampleSD%:
- FedAvg Small82.13±7.28, Medium78.29±2.37, Deep81.24±5.82.
- EAD/FedAvg Small79.36±8.29, Medium76.47±2.71, Deep80.26±5.34.
- KD/FedAvg Small84.63±0.20, Medium87.86±4.28, Deep85.07±0.85.
- EAD/KD/FedAvg Small83.80±2.03, Medium86.19±2.52, Deep84.13±1.42.
Thus combined has stronger observed targeted-TMR trajectories but lower mean targeted endpointmacro-F1 thanKD-only. Do not claim universal utility superiority.

Targeted elapsed4.49hours; main36run total12.90recorded hours. CSVs, auditmetadata and two reviewed SVG figures saved under docs/evidence/development_20261027/. Added scripts/summarise_development_archives.py for reproducible reportchecks/exports. CSVs cross-checked against a separately calculated analysis. Training source unchanged.

Consolidated interpretation, claimmatrix, Chapter4/5 links and viva brief: [development_evidence_summary_20261027.md](development_evidence_summary_20261027.md). Main package complete as a development study. Stop adding conditions for current viva preparation; preserve originalreports/checkpoints/settings. Finaltest untouched, finalprotocol notfrozen, provenance and broader thesis evaluation remain outstanding.


### Upstream data provenance and access constraint,27October2026

The user confirms that the script/notebook producing Process_1 IDS-IoT-2024.csv and the original unprocessed data are unavailable to them, with subscription access reported as a download constraint. Do not describe this access restriction as independently verified: browsing could not retrieve the IEEE DataPort landing page, including a robots-denied response, and did not verify an open raw-data/preprocessing download.

Reviewed current configs/data_protocol_groups2.json, scripts/prepare_candidate_split_groups2.py and scripts/prepare_development_clients.py. Top-level exact-feature groups are kept together and the additional StandardScaler is fitted on client_training rows only. The historical local14October audit reports file-wide moments consistent with earlier standardisation, but this is not proof of its fitting procedure. Supplied legacy notebooks load already processed CSVs and did not establish the producer pipeline in the reviewed cells. Upstream scaling/encoding/feature-selection provenance remains unverified, not confirmed leakage.

Retain the36run development package as a conditional comparison on the fixed, checksum-identified processed representation. Shared inputs support matched method comparisons but cannot remove or quantify any unknown upstream bias. Do not reset preprocessing_provenance_verified totrue, reconstruct fictitious preprocessing, overwrite results or imply leakage-free raw-to-test evaluation.

Recommendation: record this evidence gap explicitly and proceed with other verifiable controls. A later protocol may be frozen for held-out evaluation within the processed representation with that limitation retained; obtaining raw data is not an automatic prerequisite to any such evaluation, and a within-file holdout cannot establish independent raw-data generalisation. Broader claims should be supported through a separately documented dataset/pipeline with verified preprocessing when feasible. No subscription purchase is required to preserve and analyse the current evidence.


### Server supervision source audit and prepared controls,28October2026

The user authorised proceeding with master pre-training/server-data controls after retaining the upstream-provenance limitation. This permits a bounded additional diagnostic; the earlier recommendation to stop adding main FL conditions does not require confirmation to perform this authorised check.

Inspected current scripts/pretrain_development_master.py, scripts/run_matched_replication.py and src/ead_dc_fl/models_and_kd.py. Master training uses labelled server_kd rows,20epochs, final-epoch checkpoint, with validation evaluated afterwards and no validation_data/early-stopping/checkpoint selection in fit. Recurring KD uses the full server_kd feature allocation without labels in its KL objective. Labelled server_validation is used for teacher selection, acceptance and reported development metrics. KD_SAMPLE_LIMIT=512 is unused; actual selected_kd_rows is the full allocation. Overall label dependence cannot be described as absent merely because recurring KD uses features only.

Added isolated scripts/audit_server_supervision.py and tests/test_server_supervision_audit.py, plus docs/server_supervision_audit.md. Existing training/attack/model/matched-contract files were not edited. The audit rechecks registered hashes, exact-feature group separation, training-only normalisation, same-seed benign references and saved-master validation metrics. A mismatch saves reference_mismatch and stops before student control training.

Optional controls: same-seed initial Small/Medium/Deep students trained solely on labelled server data for the master's20epoch budget, and master-distilled-only students with three3epoch KD phases and no client training. These are six additional reference fits, not matched FL runs. They measure centrally available utility; they are unexposed to client poisoning, use different explicitly logged training budgets, inherit existing master pre-training where applicable, and do not isolate the master's causal contribution inside interacting FL.

Six new non-TensorFlow boundary/normalisation/metric tests passed locally; existing12matched tests passed; syntax and CLI checks passed. Full TensorFlow/data/checkpoint execution has NOT been performed here because the runtime lacks TensorFlow and actual UWE inputs. Actual saved-master report/weights and reference metrics await the user's UWE audit output. No new numerical control findings or runtimes are claimed.

Output is a new outputs/controls/server_supervision_seed42_v1 directory, with aggregate report, validation predictions and student weights; final-test predictions are not performed. All36main FL results remain unchanged. Protocol, interpretation limits, commands and completion criteria are in [server_supervision_audit.md](server_supervision_audit.md).


### Server supervision audit completed,28October2026

Inspected server_supervision_seed42_v1_report.tar.gz, statuscompleted, six student references. Audit source hashmatches; initial tensors and all four benign reference report hashes/finalmetrics match the prior seed42 main archive. Confusion-matrix arithmetic independently reproduces accuracy/F1/classcounts/targeted errors/Normal false alarms. Feature-group overlaps zero; training-only scaler numerically matches. Saved-master metrics reproduce exactly. Masterunchanged, existingoutputs unmodified, testnot evaluated. Original arrays/checkpoints absent from this aggregate upload.

Master accuracy65.47%, macro-F164.68%.
Server-supervised-only accuracy/macroF1%: Small66.28/65.25, Medium66.51/65.37, Deep68.12/66.89.
Master-distilled-only: Small64.21/65.32, Medium65.49/63.94, Deep67.99/65.86.
Matched seed42 benign combined FL has roughly86%accuracy/85%macroF1. The tested central-only procedures do not reproduce its overall utility, but this is not an isolated causal KD estimate or a compute-matched comparison.
All central references already have99.50%Malware recall and2/801Malware-to-Normal errors. Trusted server supervision remains a plausible contributor to targeted protection. DoS recall29.01–37.52% in student references exposes class-specific limitations. References are unpoisoned, one seed only, not robustness demonstrations.

Elapsed82.22seconds, excluding inherited master-pretraining cost. Main FL count remains36; six additional reference fits and one master replay are separate diagnostics. Full tables and claim limits: [server_supervision_seed42_results.md](server_supervision_seed42_results.md). These results can now be included in the viva evidence, replacing any pending-control description.


### Within-FL KD schedule controls prepared, 28 October 2026

Following the completed server-supervision audit, the user asked to continue coding.
The next bounded diagnostic separates the original master warm-start from recurring
adaptive KD inside FL. Six central-only fits cannot isolate those interacting roles.

Added separate scripts/run_kd_schedule_control.py,
scripts/run_kd_schedule_control_batch.py, src/ead_dc_fl/kd_control_protocol.py,
tests/test_kd_schedule_controls.py and docs/kd_schedule_controls.md. Original
manifest-bound training, attack, model, contract and preparation sources remain
unchanged. Original runner SHA256 remains
7553b723b338a05a1a444a650049265dbcc95bcdfba40b22a563acc06d8ee308.

First stage is four new seed-42, 12-round runs with EAD on and FedAvg:
warm_start_only and adaptive_only, each benign and Malware-to-Normal attacked.
The original full-KD benign/targeted pair is reused. All initial states, allocations,
local training/orders, participation, EAD, attack identities/rows/timing, proxy inputs
and validation rows stay fixed. KD exposure intentionally differs and is recorded.
adaptive_only still uses labelled validation for teacher selection and acceptance;
it is not a label-free server method. This is an ablation, not a new defence.

Preflight checks the existing contract, registered hashes, original references and
shared-prefix checkpoints. Every control must reproduce original round-1 pre-KD
training/screening records. warm_start_only must reproduce all original round1–3
cluster records and exact checkpoint tensors, then skip KD. full_replay is an
optional verification mode, excluded from the default four-run batch. Conflicts
and incomplete outputs stop execution and remain preserved.

All 34 local tests passed, including 12 new protocol tests. Syntax and batch CLI
checks passed. New validators accepted six uploaded original full-KD benign/targeted
reports and all 72 round records across seeds42/2026/31415. Static diff confirms
inherited local training, attacks, EAD, FedAvg, KD loss and accuracy acceptance.
TensorFlow and real UWE inputs/checkpoints are unavailable here, so GPU replay
and new control outcomes remain pending. No numerical benefit is claimed.

The batch produces policy-matched benign/attack summaries and
kd_schedule_seed42_v1_reports.tar.gz. Analyse complete security trajectories and
round-12 utility; do not use rounds or clients as independent replications.
Replicate a substantive one-seed interpretation with the two existing additional
seed contracts before stronger claims. No final-test use, final protocol freezing,
proxy tuning or change to the main36-run evidence package occurs in this stage.


### Within-FL KD schedule controls completed, 28 October 2026

Inspected kd_schedule_seed42_v1_reports.tar.gz, SHA256
d9e73c1416c416379ff1cea52d58063b1e77c98fe055d84ef046deeae76ca7ee.
Four new seed42,12round EAD-on/FedAvg controls completed, with the two original
full-KD references reused. Source/report hashes match; original reference bytes
match earlier archives; common fingerprints, initial tensors, participation and
orders agree. Recomputed every summary exactly. Round-1 pre-KD records match for
all controls. Warm-start-only round1–3 cluster records and recorded checkpoint
hashes match original references, with runtime exact-tensor checks reported.
Actual checkpoint/data/prediction arrays are not in this aggregate upload.

Key finding: both original full KD and warm-start-only have zero excess committed
Malware-to-Normal TMR at all36architecture/round observations under their own benign
controls. Recurring KD after round3 is therefore unnecessary to reproduce that
specific protection in this one-seed setting. This does not establish master-only
sufficiency, since EAD/FedAvg/local training remain, or protection of other metrics.

Adaptive-only peaks: Small0.1248pp, Medium13.1086pp, Deep52.8090pp. Attacked Deep
is teacher all12rounds and never receives KD; its checkpoint hashes match earlier
EAD-only Deep at every round. Benign Deep hashes also match earlier EAD-only Deep.
Deep round7 retains424/801target errors against1/801benign, with all3attackers
accepted. This exposes both screening misses and teacher self-skip limitations.

New accepted-KD failure: adaptive-only round3, Deepteacher89target errors;
Medium preKD0/801, candidate105/801, accepted. Accuracy81.7763->90.5526% and
macro-F178.5225->80.0525%, while TMR worsens13.1086pp. Counts support security
deterioration during KD, without proving per-example teacher/student error identity.
Round7 Small/Medium candidates have428/425errors but are rejected; Deep retains424.

Attacked round12accuracy/macroF1%:
- FullKD Small86.38/85.11, Medium86.01/84.66, Deep86.01/84.66.
- Warm-start-only Small85.22/84.39, Medium83.76/81.19, Deep85.87/84.86.
- Adaptive-only Small83.53/75.89, Medium84.95/82.31, Deep94.05/86.41.
High final Deep utility conceals earlier security failure. FullKD does not dominate
all utility metrics. Warm-start-only Medium still loses macroF1 against benign,
despite zero excess targeted error.

Attack screening TP/FN/FP/TN: full100/8/0/252, warm101/7/0/252,
adaptive95/13/0/252. Clean false rejections37/360,40/360,42/360respectively.
All36attackedgroup-rounds trigger calibration under each policy. These are repeated
submissions, not independent replications. Four new elapsed times sum8998.01seconds,
2.50hours; KD exposure differs and master-pretraining cost is inherited.

Results: [kd_schedule_seed42_results.md](kd_schedule_seed42_results.md);
audit/216trajectory rows under docs/evidence/kd_schedule_seed42_20261028/.
Main36run evidence unchanged, plus4new FL controls and6earlier central-only fits.
Finaltest untouched, finalprotocol notfrozen. Recommended next bounded step is the
same four controls with existing seed2026/31415contracts, eight additional runs,
before stronger claims. Preserve original policy and report seed dependence if the
finding fails to replicate. Chapter4/5 must qualify the role of master supervision
and recurring KD, rather than attributing the measured protection to recurring KD alone.


### Within-FL KD schedule replication: seed 31415, 28 October 2026

Inspected kd_schedule_seed31415_v1_reports.tar.gz, SHA256
6521d93804f7836bc65ce3b534f39aea1869b54c327ba1f96a4962ebc916c170.
Four additional 12-round controls completed, plus two reused original references.
Source/report hashes, manifest identity, initial hashes, common fingerprints,
participation/orders, original-reference bytes, first-round pre-KD records,
warm-start round1–3 records/recorded checkpoint hashes and the recomputed summary
all pass. Detector/calibration/FedAvg/poisoning/teacher/KD records are consistent.
Actual raw arrays, predictions and checkpoint tensors remain absent from this
aggregate upload. Runtime exact-tensor checks are reported, not independently
reloaded here. No final-test evaluation or final-protocol freezing.

Warm-start-only and original full KD both match their policy-matched benign
committed targeted-error rates throughout all 36 architecture/round observations.
Across seeds42 and31415, this is72 observations per policy, with two independent
run replications, not72 independent runs. Recurring KD after round3 is unnecessary
to reproduce that measured protection in these two tested configurations.

Adaptive-only positive excess TMR peaks in seed31415: Small0.1248pp,
Medium0.3745pp, Deep0.1248pp, unlike seed42 Medium13.1086pp/Deep52.8090pp.
Master teaching cannot therefore be described as universally necessary.
Adaptive teachers vary; Deep receives7KD phases,6accepted. In round2,
Medium teaches Deep and accepted KD changes target errors101->1/801,
accuracy75.51->77.34%, macroF167.67->70.03%. This records beneficial security
recovery, contrasting the seed42 accepted harmful-KD case. Teacher identity,
recipient eligibility and complete trajectories matter; this is not an isolated
causal explanation for every seed difference.

Seed31415 attacked endpoint accuracy/macroF1%:
full Small85.86/84.83, Medium86.09/84.81, Deep86.13/85.21;
warm-only Small83.05/80.14, Medium83.83/81.32, Deep86.03/83.25;
adaptive-only Small82.55/79.12, Medium82.75/79.31, Deep83.12/79.58.
FullKD leads both alternatives on these endpoint metrics in this seed, while
seed42 showed a different Deep utility ranking. Targeted protection and utility
must remain distinct claims.

Attack screening TP/FN/FP/TN: full96/12/1/251, warm96/12/1/251,
adaptive99/9/0/252. Clean false rejections34/360,44/360,37/360.
New elapsed time9443.19seconds,2.62hours. Recorded costs omit inherited
master-pretraining and exposures differ, so no compute-matched efficiency claim.

Verified total now44completed12round FL runs: main36 plus8KD controls.
Six server-only fits are separate. Seed2026 KD-control archive has not been
received, so its four requested controls are not counted as verified. Request
kd_schedule_seed2026_v1_reports.tar.gz if already completed, without rerunning
existing conditions. No new factor sweep is needed before that inspection.
Results: [kd_schedule_seed31415_results.md](kd_schedule_seed31415_results.md).
Audit and216trajectory rows: docs/evidence/kd_schedule_seed31415_20261028/.
