# EAD–DC–FL: implemented development protocol and proposed next experiments


**Subsequent implementation update, 28 October 2026:** the user authorised the
24-run statistical label-skew block below. Its separate code, synthetic checks and
pre-run protocol are prepared; actual UWE allocation statistics, GPU fidelity replay
and numerical outcomes remain pending. See
[labelskew_development_protocol.md](labelskew_development_protocol.md). The existing
48 completed FL runs remain unchanged. Participation heterogeneity and the final
evaluation protocol remain separate, unresolved work.


Recorded 28 October 2026 after inspection of the executed source and uploaded
reports. This documents the completed development procedure; it is not a
retrospective preregistration or a frozen final-evaluation protocol. Proposed
extensions below are recommendations, not previously agreed or implemented settings.

## Completed evidence

There are 48 verified completed 12-round FL runs: 36 main-study runs and 12
additional KD schedule controls. Six server-only reference fits are separate.
Earlier four-round pilots, component checks and diagnostic replays are excluded.
The complete main study is four methods × three scenarios × three training seeds.
The 12 benign runs are shared across the two attack comparisons. The schedule
controls add two policies × benign/targeted × three seeds, reusing six original
full-KD references rather than counting them again.

## Implemented protocol

| Element | Executed setting |
|---|---|
| Dataset | Fixed processed IDS-IoT-2024 CSV, seven classes, 96 features |
| Data allocation | 49,160 client-training rows; 30,048 server-KD rows; 7,600 server-validation rows; 9,472 test rows |
| Split protection | Exact-feature groups kept together across top-level partitions; additional scaler fitted on client training only; upstream processing unverified |
| Clients | 30, with ten Small, ten Medium and ten Deep MLP clients |
| Architectures | Small [128], Medium [256,128], Deep [256,256,128]; linear output logits |
| Statistical heterogeneity | Class-stratified disjoint IID allocation; no controlled non-IID variation yet |
| Participation | All 30 clients, fixed order, every round; no participation-heterogeneity study yet |
| Local training | One epoch per round; batch 128; fresh Adam optimiser, learning rate 0.001, per-client/round order seeds |
| Aggregation | Sample-weighted FedAvg within architecture; renormalise sample weights over accepted clients |
| EAD inputs | Full submitted weights/biases flattened and standardised within the current architecture cohort |
| EAD ensemble | LOF, Isolation Forest and kNN; fitted-cohort predict/decision_function; unanimous three-detector rejection |
| EAD calibration | Reset contamination to 0.20 per group/round; if individual flagged counts disagree, rerun once at 0.30; never use attacker identities/true ratio as input |
| Master | Fixed seed-42 master, supervised on the labelled server-KD allocation for 20 epochs |
| Original KD warm-start | Rounds 1–3 use the fixed master with unconditional candidate acceptance |
| Original later KD | Highest pre-KD validation-accuracy eligible architecture teaches; stable architecture-order tie-breaking; skip self-distillation |
| KD objective/budget | Temperature 3; three epochs; batch 256; learning rate 0.001; full server-KD feature allocation; labels excluded from the KL loss |
| Adaptive acceptance | Accept candidate if validation accuracy is at least pre-KD accuracy; otherwise restore the current pre-KD aggregate |
| Main method cells | FedAvg; EAD + FedAvg; KD + FedAvg; EAD + KD + FedAvg |
| Malicious clients | Nine fixed identities, three per architecture; 30% of all clients |
| Gaussian attack | Add independent seeded noise to full submitted weights/biases after local training; sigma 0.5 in the main study |
| Targeted attack | All local Malware labels on compromised clients become Normal before training; current IID allocation changes 1,497 labels per round |
| Attack timing | Every round; server data and evaluation labels remain unchanged |
| Replications/horizon | Seeds 42, 2026 and 31415; 12 rounds; fixed split, master and compromised identities across seeds |
| Matching | Same initial tensors, allocation, local budgets/orders, master, participation and attack definitions within seed; saved manifests and hashes |
| Reporting | Per-architecture accuracy, macro-F1, class recall, targeted counts/rates, screening confusion counts and full pre/candidate/committed KD records |
| Evaluation status | Development validation used for teacher/gate decisions and reporting; final test not evaluated; final protocol not frozen |
| Privacy scope | Trusted server sees individual models; no formal privacy or secure-aggregation compatibility claim |

The main source is scripts/run_matched_replication.py, with the corresponding
matched manifests and uploaded reports. Historical Median, fitted-label EAD,
five-detector diagnostics and guarded warm-start remain separate configurations.
The working implementation is a documented reconstruction/adaptation, not a
claim of code identity with every published EAD-FL/DC-FL result.

## What the results establish

- Under the tested Gaussian attack, the combined method has the highest mean final
  macro-F1 across the three seeds in all architectures. This does not establish
  robustness to stealthy, adaptive or held-out attacks.
- Under label flipping, original combined and warm-start-only each match their own
  benign committed target rate across all 108 seed/architecture/round observations.
  Recurring KD after round 3 is unnecessary for reproducing that specific result
  in these configurations; EAD, FedAvg and local training remain.
- Recurring KD has higher mean attacked endpoint macro-F1 than warm-start-only in
  every architecture, but individual paired effects include decreases and a tie.
- Adaptive-only security varies by seed. Recorded KD steps can repair targeted
  behaviour or worsen it while accuracy and macro-F1 improve. The accuracy guard
  is not a security guarantee.
- EAD has benign false rejections and threat-dependent misses. Calibration is
  active in many attacked rounds but does not guarantee correct screening.
- Server-only references do not reproduce overall FL utility, but already achieve
  high Malware recall. Trusted central supervision remains material to interpretation.

Use runs as the replication unit. Clients, architectures and rounds do not supply
independent replications. The early planning specification proposed at least five
seeds; the executed development programme used three. Decide the final replication
budget explicitly rather than describing the early proposal as already fulfilled
or retrospectively treating three seeds as a frozen final requirement.

## Proposed next stage 1: statistical heterogeneity

Priority recommendation: one controlled label-skew condition, retaining the three
architectures and full participation. Use four method cells × benign/targeted ×
three existing training seeds: 24 new development runs. Reuse the corresponding
IID references only after verifying runner fidelity. Do not add another KD-policy
grid or duplicate benign controls for a Gaussian sweep in this stage.

Keep the top-level training/server/validation/test allocation, scaler, master,
architecture definitions and initial checkpoints unchanged. Redistribute rows
among clients within each existing architecture training pool. Preserve group
totals and client sample-count budgets, so statistical label skew does not also
change architecture-level data coverage or client data quantity.

A proposed allocator is capacity-constrained classwise Dirichlet allocation with
alpha 0.5. This value is a development design choice, not an established optimum
or a previously agreed final setting. Inspect realised class distributions and
divergence using training labels only, and specify deterministic handling of
capacity limits before attack runs. Do not select the allocation using attack or
final-test performance, or force every client to contain every class.

Keep compromised identities fixed, then derive new Malware-to-Normal poison-row
lists from their new allocations. Log source-class opportunity and realised poison
counts. They may no longer total 1,497; this opportunity change is part of the
label-skew setting and limits a pure fixed-dose causal interpretation. Do not move
attackers or force the old poison count merely to reproduce stronger attacks.

Required evidence: realised skew/counts; matched initial states, schedules and
budgets; benign rejection by client and utility by group/class; detection counts under
attack; pre/candidate/committed security; teacher choices; seed-level uncertainty.
This directly tests whether screening mistakes legitimate statistical diversity
for poisoning and whether KD improves or harms the affected trajectories. It
extends Chapter 4's evaluation and informs Chapter 5 without replacing Chapter 3's
frozen heterogeneity-impact questions.

## Proposed next stage 2: participation heterogeneity

Study this separately on the IID allocation first, preserving the established H_P
definition. Compare uniform and unequal client inclusion probabilities at the same
mean participation, with controlled/comparable attacker availability. A lower
participation rate alone does not isolate unequal availability. Log intended and
realised client inclusion probabilities, cohort sizes and active malicious ratios.

A bounded proposed design is FedAvg versus original EAD–DC–FL, benign/targeted,
two matched-mean availability profiles and three seeds: 24 runs. This estimates
the integrated method's behaviour relative to FedAvg; it does not independently
identify EAD and KD effects under partial participation. Add component cells only
if a specific finding requires that attribution. The sampler and admissible cohort
sizes remain to be specified before implementation, not treated as already agreed.

New manifests and a separately identified runner are required: the existing
contract requires full cohorts and current detector checks assume ten uploads.
Specify sampling/stratification effects on actual marginals, minimum detector
cohorts and failure handling. Do not silently disable detectors or use attacker
labels in the deployed scheduler/defence. Keep the same saved schedule across
methods and benign/attack arms. Do not start a full non-IID × availability grid.

This is a secondary integration extension. Chapter 3's participation-impact study
and WEAD-FL retain their separate identities and are not made compulsory parts of
this integration experiment by this recommendation.

## Final-evaluation gate

The final protocol remains to be written and frozen before any final-test metric
is viewed. It must identify retained methods, attack settings, partitions, server
supervision, seeds, horizon, primary metrics, checkpoint rule, uncertainty and
scope limits. Existing development outcomes cannot become confirmatory evidence
merely by changing a report flag. For unchanged conditions, verified stored
checkpoints may support held-out reporting without repeating training; required
pre/candidate snapshots and any changed training protocol need explicit handling.

The additional original-CSV preprocessing remains unknown. A frozen within-file
held-out evaluation can retain that explicit limitation; it cannot establish
independent raw-data generalisation. The supplied thesis structure places empirical
heterogeneity characterisation in Chapter 3 (page 1), solutions/integration in
Chapter 4 and synthesis in Chapter 5 (page 2). Its chapter outline does not itself
specify the new sampling/Dirichlet parameters proposed here.

Evidence sources: [main study](development_evidence_summary_20261027.md),
[KD controls](kd_schedule_three_seed_results.md),
[server references](server_supervision_seed42_results.md),
[research log](development_research_log.md). These proposals strengthen evidence;
they do not introduce a new defence or support novelty by combination alone.
