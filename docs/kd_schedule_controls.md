# Within-FL master and recurring-KD controls

Seed-42 execution completed and verified 28 October 2026. See
[kd_schedule_seed42_results.md](kd_schedule_seed42_results.md) for the results,
source checks, one-seed limitations and the planned replication decision.

Registered 28 October 2026, before running these controls. This is a separate, bounded
development diagnostic. The original 36 FL runs, their source, manifests and results
remain unchanged. Final-test evaluation and final-protocol freezing are not performed.

## Question and reason

The six central-only references do not reproduce overall FL utility, but already
achieve 99.50% Malware recall and 2/801 Malware-to-Normal errors. They do not isolate
the contribution of the master inside FL. The next control therefore changes the
KD schedule inside the matched pipeline, before undertaking proxy or data changes.

The question is whether the observed targeted-error protection persists when
recurring KD is removed after the master warm-start, or when adaptive cluster KD
replaces master teaching from the beginning. This addresses the central-supervision
reviewer concern and qualifies Chapter 4's integration results and Chapter 5's synthesis.

## Fixed design and interventions

| Condition | Rounds 1–3 | Rounds 4–12 | New training |
|---|---|---|---|
| Original full KD | Saved master, unconditional acceptance | Adaptive cluster teacher, accuracy guard | Reuse existing benign/targeted pair |
| warm_start_only | Identical saved master and unconditional acceptance | No teacher and no KD | One benign and one targeted run |
| adaptive_only | Adaptive cluster teacher and accuracy guard | Adaptive cluster teacher and accuracy guard | One benign and one targeted run |

First stage: seed 42, 12 rounds, EAD on and sample-weighted FedAvg. There are four
new FL runs, with two existing full-KD references. No EAD-off cross-product and
no new Gaussian sweep are required for this stage. The new batch can subsequently
be run with an existing seed 2026 or seed 31415 manifest, but do not treat seed 42
as sufficient evidence of a general effect.

Preserve all initial model tensors, client allocations, full-participation order,
local training budgets/orders, compromised identities, poison rows, attack timing,
EAD prediction/calibration/voting, proxy features and validation rows. The attack
remains Malware-to-Normal flipping in all nine fixed compromised clients, three
per architecture. Use each policy's own benign run to calculate excess targeted
misclassification, never the original policy's benign trajectory.

The contract's training_settings retain the registered baseline and per-phase
budgets. planned_kd_schedule and actual_kd_feature_presentations explicitly record
the intentionally different exposure. These comparisons are not compute-matched.
adaptive_only still uses labelled server validation for teacher selection and
acceptance. It is a no-master-teaching control, not a label-free server method.
The master is loaded and verified for the original contract and model-construction
RNG alignment, but is never selected as teacher in adaptive_only.

## Implementation identity and checks

- scripts/run_kd_schedule_control.py is a separately named adaptation of the
  unchanged scripts/run_matched_replication.py. There is no runtime source rewriting.
- src/ead_dc_fl/kd_control_protocol.py defines schedules and verification boundaries.
- scripts/run_kd_schedule_control_batch.py preflights inputs, launches sequentially,
  reuses only verified completed controls, and creates a report archive.
- tests/test_kd_schedule_controls.py checks policy boundaries, accuracy-gate
  semantics, original-reference identity, replay mismatch handling, correct pairing
  and preservation of conflicting archives without TensorFlow or actual data.

Preflight verifies the existing manifest and every registered input hash, original
report identity and reference rounds 1–3 checkpoint hashes. No new manifest is made.
Each control must exactly reproduce the original first-round local-update and EAD
records before KD. warm_start_only must additionally reproduce all cluster records
and checkpoint tensors in rounds 1–3. full_replay is an optional verification policy
that requires exact original records/tensors for all 12 rounds; it is not part of the
default four-run batch.

Exact replay is appropriate here because the same UWE environment and checked
deterministic implementation are being reused. On a mismatch, stop and preserve
control_verification_failed and its checkpoints. Inspect the first differing field
and environment. Do not relax equality, regenerate inputs or repeatedly rerun until
it happens to pass. If an unavoidable environment difference is established, register
a separate repeatability protocol and tolerances before interpreting the controls.

Original reports and checkpoints are read-only. New outputs use separate
outputs/controls/matched_fedavg_<id>_kd_schedule_<policy>_<arm>_ead_on_seed42_rounds12_v1
directories. Existing incomplete or different outputs are preserved and stop the
batch. Completed controls require policy/runner/reference hashes, full rounds,
recorded replay checks and unchanged checkpoint hashes before reuse.

Existing per-round logs retain detector scores, thresholds, flags, calibration,
accepted clients, aggregation coefficients, local losses, teacher/tie order,
pre-KD/candidate/committed accuracy, macro-F1, class recall and targeted errors,
KD acceptance, model checkpoints and elapsed time. Extra logs identify schedule,
reference hash, policy-source hash and actual KD feature presentations.

## Run on UWE

Use the same activated .venv-gpu environment and GPU-library export as the existing
runs. Pull the current branch, then run the new checks and preflight:

```bash
git pull --ff-only
python -m unittest discover -s tests -p 'test_kd_schedule_controls.py' -v
python scripts/run_kd_schedule_control_batch.py --preflight-only
```

Only after preflight passes:

```bash
python -u scripts/run_kd_schedule_control_batch.py
```

The batch stops on the first failure and can reuse verified completed controls.
Keep the terminal session alive, or use the university's supported persistent-job
facility if disconnecting. Four runs should be budgeted using previous per-condition
times, roughly 1–2 hours on the same machine, with actual cost recorded afterwards.
GPU speed or completion time is not guaranteed.

Upload kd_schedule_seed42_v1_reports.tar.gz when it reports completion. It contains
the four control reports, two original reference reports, manifest, sources, protocol
and descriptive summary, but no raw dataset or large checkpoint arrays. A SHA256
is printed. Checkpoint replay is verified on UWE and recorded in reports, not
independently reproducible from this aggregate archive alone.

## Analysis, decisions and permissible claims

Use round-12 accuracy/macro-F1 and per-class recall, together with the complete
pre-KD/candidate/committed targeted-error trajectories. The summary reports final
utility, peak positive excess committed TMR over the policy-matched benign run,
all per-round excess values and actual performed/accepted KD counts. Inspect the
underlying stage-specific records as well: the summary's committed peak can hide
harmful rejected candidates. Rounds and clients are not independent replications.

- If warm_start_only preserves the full policy's low excess TMR, recurring KD is
  not required to reproduce that measured protection in this one-seed setting.
  This does not establish that the master alone explains all protection.
- If adaptive_only loses protection while full KD retains it, the tested master
  schedule is a plausible contributor. It is not an isolated estimate of labelled
  data benefit: teacher identity, first-phase acceptance and KD exposure also differ.
- If adaptive_only preserves protection, master teaching is not necessary to
  reproduce it in this tested configuration; labelled validation and proxy inputs
  remain part of the pipeline.
- If both alternatives lose protection, their interaction and training trajectories
  warrant replication. This does not prove formal synergy or universal necessity.

If checks fail, revise implementation before training more. If the four runs pass,
inspect both utility and security and record any negative finding. Replicate a
substantive interpretation using the two existing additional-seed contracts before
promoting it beyond a diagnostic. Do not select the best schedule on final-test
outcomes. No new defence, novelty claim, security-aware gate or proxy tuning is
introduced in this stage. Broader H_S/H_P and held-out threats remain separate work.

## Current validation status

All 34 available local tests passed, including 12 new protocol tests. Python syntax
and batch CLI checks passed. The new reference/policy validators also accepted the
six uploaded original full-KD benign/targeted reports across the three seeds, including
all 72 round records. Static comparison confirms local training, attacks, EAD, FedAvg,
distillation loss and acceptance implementation are retained from the original runner.

TensorFlow, actual UWE data and matched checkpoints are not
available in the assistant runtime. Numerical execution, GPU replay and the four
control outcomes require the user's UWE run. Passing local protocol tests does not
establish full-run fidelity or performance.
