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
