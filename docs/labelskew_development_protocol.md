# Controlled statistical heterogeneity: 24-run development protocol

Prepared 28 October 2026, before these runs. The user authorised implementing the
proposed non-IID block. This protocol identifies the development condition; it does
not freeze the final PhD evaluation or authorise final-test tuning/evaluation.
The completed 48 FL runs and six server-only fits remain unchanged.

## Question and scope

Does legitimate within-architecture label skew change EAD false rejection,
poisoning detection, utility and pre/candidate/committed KD security? The preceding
study varied component use under IID/full participation, not statistical diversity.
This block extends Chapter 4's evaluation and Chapter 5's synthesis without
replacing Chapter 3's frozen heterogeneity-impact questions or making WEAD-FL part
of this integration experiment.

One fixed label-skew allocation is shared across three training seeds. Full
participation and the three MLP capacities remain. No participation-heterogeneity
sampler, revised defence, Gaussian sweep or KD-schedule grid is added here.

## Fixed design

| Element | Choice |
|---|---|
| Methods | FedAvg; EAD + FedAvg; KD + FedAvg; EAD + KD + FedAvg |
| Conditions | Benign and Malware-to-Normal label flipping |
| Training seeds | 42, 2026, 31415 |
| Horizon | 12 rounds, fixed endpoint; not a convergence claim |
| Count | Four methods × two arms × three seeds = 24 new FL runs |
| Diagnostic | One extra four-round IID fidelity replay, not counted as a new scientific condition |
| Statistical allocation | Within-architecture capacity-constrained Dirichlet-derived class preferences, alpha 0.5, allocation seed 42 |
| Participation | Same 30 clients, same full-cohort order in every round |
| Preserved data | Same top-level split, each architecture's exact training-row pool, every client's sample count, normalisation, server data and master |
| Initial models | Byte copies of each training seed's existing matched initial checkpoints |
| Attacker identities | Same nine fixed compromised clients, three per architecture |
| Attack | Flip all locally available Malware labels on those clients to Normal each round |
| EAD/KD/training | Original three-strict predict-mode EAD/calibration, sample-weighted FedAvg and original master/adaptive KD, unchanged per-phase/local budgets |
| Evaluation | Development server validation only; final test untouched; upstream preprocessing remains unverified |

The original IID comparison reports are reused only after metadata checks and
runner fidelity verification. They are not counted as 24 new runs. Their data
allocations intentionally differ from the label-skew condition; within each new
seed, all methods/arms share exactly the same allocation and initial states.

## Allocation algorithm and training-data-only checks

For each architecture, concatenate its existing ten clients' disjoint training
rows. Draw one positive Dirichlet preference vector across clients for each
nonempty class, using a separate allocation stream. Iterative proportional fitting
(IPF) balances those preferences to the fixed architecture class totals and client
capacities. A unit-capacity residual bipartite flow rounds cell counts to integer
floors/ceilings with exact class/client margins. Shuffle row identities separately
within each class, split by the resulting counts and shuffle client row order.

This is a constrained Dirichlet-derived design, not an unconstrained Dirichlet
partition. Alpha 0.5 is a chosen development setting, not an optimum or novelty
claim. No rows are duplicated, dropped or moved between architectures. Classes
may be absent from individual clients; all-classes-per-client assertions are not
carried over falsely from IID. Identical-feature rows may still span training
clients, as in the existing data protocol.

Allocation uses client-training labels only. Labels outside that pool do not
determine skew. Training/server/test partitions, source representation and the
training-pool scaler remain unchanged. Register realised class counts, proportions,
class coverage, total variation (TV) from the architecture distribution and
Jensen-Shannon divergence in bits, for both IID and label skew.

Predeclared data-only eligibility: every architecture's mean TV must be at least
0.10 and exceed its IID mean TV by more than 0.05. IPF uses tolerance 1e-8 and a
10,000-iteration limit. Failure saves allocation diagnostics and stops without
automatic redraw, row dropping or attack-driven allocation selection. The same
allocation seed is fixed across training seeds, so generalisation over allocation
randomness is not evaluated.

## Poison opportunity and ground truth

Recompute poison-row lists from the new allocations while keeping compromised
identities fixed. Do not force the old 1,497 changes per round, relocate attackers
or select partitions using attack success. Require at least one poisonable Malware
row across the compromised clients; a zero-total no-op attack stops preparation.
An individual compromised client may have zero Malware rows and is retained.

Two audits are distinct:

- screening_audit uses designated compromised identities, preserving the original
  client-detection definition. A missed designated client may have no label changes.
- effective_poisoning_screening_audit records actual label-changing clients,
  their rejection/acceptance and designated zero-opportunity clients.

Per-client logs include available source-class count, actual changed-label count,
before/after label hashes and submitted tensor hashes. poisoning_applied is true
only if labels actually changed. Ground truth is used for attack simulation and
analysis only, never calibration, voting, teacher selection or aggregation.

IID/non-IID poisoning opportunities can differ. Therefore comparisons estimate
behaviour under the resulting label-skew/attack-opportunity setting, not a pure
heterogeneity effect at an equalised poisoning dose. Both opportunity and security
must be reported. A fixed-dose study would be a separate control if later required.

## Source identity, contracts and replay

New files:

- src/ead_dc_fl/label_skew.py: allocation, metrics and protocol validators.
- scripts/prepare_labelskew_development.py: training-only preparation and three
  separately hashed matched contracts, without TensorFlow training.
- scripts/run_labelskew_development.py: isolated adaptation of the immutable IID
  runner, with additional diagnostic counts/hashes.
- scripts/run_labelskew_batch.py: preparation, preflight, fidelity replay, 24
  sequential conditions, verified reuse and an aggregate archive.
- tests/test_label_skew.py: allocation, leakage boundaries, attack opportunity,
  metric/replay audits and synthetic end-to-end preparation checks.

The existing model, attack, aggregation, IID runner and original manifests are not
edited. New contracts reuse the full-cohort matched schema, copy original initial
checkpoint bytes and bind the original inputs plus new allocation/attack files,
preparation report, source and this protocol by SHA256. Changes after preparation
stop loading; incomplete/different outputs remain preserved.

Before non-IID training, the new runner replays the seed-42 original combined benign
condition for four rounds. It compares every original field recursively, allowing
only additional diagnostics, and compares exact checkpoint tensors on UWE. This
covers master rounds1–3 and the first adaptive/guarded round. A mismatch stops the
batch with the failure and checkpoints preserved. Do not relax equality or repeat
until a passing result appears. Only a separately justified environment-repeatability
protocol can replace this same-environment deterministic replay requirement.

The four-round diagnostic does not prove all long-run behaviours. New full runs
also validate teacher/acceptance logic, poisoning, voting, calibration, sample
weights and metrics after completion. Existing results are reused only when source,
input, reference and checkpoint hashes and complete reports agree.

## Logs, outcomes and analysis

Retain detector scores/thresholds/flags, count-disagreement trigger, accepted IDs,
sample counts and FedAvg coefficients, aggregation output tensor hashes, teacher
and tie order, pre-KD/candidate/committed metrics, KD decisions/reasons, checkpoint
hashes, configuration/seed/environment metadata and elapsed time.

New validation metrics also include confusion matrices, class supports and the
Normal false alarm rate. These are diagnostics and do not change the accuracy-only
guard. Candidate security can deteriorate even if a model is accepted. Recompute
accuracy, macro-F1, class recall and target counts from confusion matrices to audit
report consistency. The four-round IID replay compares the original numerical
fields exactly, while permitting the new count fields.

Primary summaries: round-12 per-architecture macro-F1, full committed excess
Malware-to-Normal trajectories against the same-regime/same-method/same-seed benign
run, and benign-client rejection. Report accuracy, class recall, Normal false
alarms, designated and effective detection counts, candidate/committed differences,
teacher choices and costs. Old IID reports lack some new diagnostic fields; do not
fabricate missing values or imply they were measured previously.

Use independent training runs as the replication unit, conditional on this one
allocation/master/attacker set. Report seed-level outcomes and mean ± sample SD;
do not treat clients, architectures or rounds as independent replicates. Do not
select methods, attacks, allocations or checkpoints from final-test outcomes.
Earlier IID generalisation/provenance and privacy limitations remain.

## UWE commands and completion

Use the same activated .venv-gpu and GPU-library export as the preceding runs.

```bash
git pull --ff-only
python -m unittest discover -s tests -p 'test_label_skew.py' -v
python scripts/run_labelskew_batch.py --prepare-only
```

Preparation prints the realised TV and new poisoning counts and performs no
training. The full programme then runs from one command:

```bash
python -u scripts/run_labelskew_batch.py
```

Keep the session alive or use the university's supported persistent-job facility.
Budget using measured prior per-condition times, allowing several hours per seed;
no GPU speedup or completion-time guarantee is made. The batch stops at the first
failure and reuses only verified complete outputs on restart.

Prepared allocation:
data/clients/idsiot2024/development_labelskew_a0p5_alloc42_v1.
Matched contracts:
data/experiments/idsiot2024/labelskew_a0p5_alloc42_seed<seed>_rounds12_v1.
New runs use separate matched_fedavg_<id>_labelskew_a0p5_alloc42 output names.

Upload labelskew_a0p5_alloc42_three_seed_reports_v1.tar.gz after completion.
The archive includes 24 new reports, 24 reused IID reports, preparation/class-count
metadata, three manifests, source/protocol, replay report and summary. It excludes
raw row-level data and large checkpoints. Source paths/hashes permit traceability;
uploaded reports do not independently provide the arrays checked on UWE.

Completion requires passed preparation/fidelity checks, all24complete matched
runs, consistent poison opportunities/count metrics, preserved old results and a
verified archive. Numerical non-IID findings require the actual UWE outputs; local
synthetic checks do not establish learning performance or GPU replay fidelity.

## Local validation status

All 49 available local tests passed, including 15 new allocation, audit and
preparation tests. The synthetic preparation pipeline creates all three contracts,
preserves original inputs, copies normalisation/initial files and reuses verified
preparation; altered registered allocation files fail without regeneration. Its
CSV contains invalid class labels outside client training, confirming those labels
are not used to allocate training data. Confusion-count and effective-versus-designated
poison checks also pass. Python syntax and batch CLI checks pass. Static source
comparison retains the original local training, EAD, FedAvg and KD implementation.

Actual UWE data, checkpoint tensors and TensorFlow are unavailable in the assistant
runtime. Actual allocation statistics, the GPU fidelity replay and the 24 numerical
outcomes remain pending. The verified completed FL count remains 48 until those
new reports are received and inspected.
