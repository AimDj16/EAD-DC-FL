# Longer-horizon matched development replication

Registered 26 October 2026. New scripts; old runners, shared helper and four-round manifests unchanged. This is development replication infrastructure, not a frozen final-test protocol.

## Scientific scope and fixed choices

Start with12rounds (3master warm-start,9adaptive rounds for originalKDon), seed42. This horizon is chosen to increase adaptive exposure, not because of selected validation performance; it is not a convergence claim. First verify EADon/KDoff Gaussian attack against its existing4round seed42 pilot. Then complete benign and Gaussian sigma0.5 four-cell batches. Inspect learning curves, calibration and runtime before scheduling additional work. If still changing, report inconclusive convergence and predeclare any further horizon; never choose a best validation round as final performance.

Planned additional training seeds2026 and31415 are distinct from seed42 and not selected by outcomes. Use identical horizon/settings for comparisons across these seeds once the development horizon is retained. Three-seed results remain preliminary, particularly after development-led configuration selection. OriginalKD is the primary transfer policy for continuity; guarded is a separate comparator, not silently substituted.

Each seed changes architecture initialisation, local minibatch permutations, KD permutations, detector seeds and Gaussian noise (seed+200). Raw data/split/client allocation/normalisation, compromised identities/targeted rows and the single seed42 pretrained master stay fixed. Participation remains full and fixed-order. Thus replication estimates training/noise variability conditional on fixed data/master/attack allocation; it does not replicate preprocessing, partition or master-training uncertainty.

Architecture initial seeds: seed+100*architecture_index. Local seeds: seed+1000*round+client_id+1. KD seed: seed+1000*round+architecture_index. Gaussian stream: SeedSequence([seed+200,round,client_id]). Attack every round through the registered horizon. EAD uses LOF/IForest/kNN predict/decision_function, strict consensus, per-round contamination0.20 with one count-range-triggered rerun at0.30. FedAvg within compatible groups, survivor sample weights renormalised. All budgets otherwise unchanged.

## Infrastructure

- scripts/prepare_matched_replication.py: requires seed,rounds,output; creates fresh initial states and complete schedules; verifies inherited input hashes/coverage. Refuses existing directory. Uses unchanged matched_development_v1 schema, which already validates arbitrary registered seed/horizon. Registers preparation and new runner source hashes.
- scripts/run_matched_replication.py: requires seed,rounds,matched-experiment,attack gaussian/targeted,arm,mode,EAD,KD. Only FedAvg, original/guarded. Gaussian attack requires positive sigma; benign/targeted requires sigma0. Preserves original targeted label assertions and Gaussian helper. Records configuration, seed scope, round and total time; saves checkpoints eachround. Original test is never evaluated.
- optional --pilot-reference DIRECTORY: compares common inputs, initial tensors, per-round screening/metrics/teacher/KD and exact committed tensors over the complete reference horizon. Stops and saves pilot_prefix_failed on mismatch. Reference checkpoints are comparison-only.
- scripts/run_replication_batch.py: sequential four-cell original-mode batches. Scenarios benign,gaussian,targeted; default all3. Benign uses Gaussian runner path sigma0 once for reuse; new targeted benign equivalence is already established at4rounds but longer mixed-runner behaviour remains checked through unified source. Reuses completed same-script/same-manifest outputs; stops on incomplete/different existing directories.

Outputs: matched_fedavg_ID_replication_predict3_FAMILY_sigmaTAG_ARM_MODE_ead_E_kd_K_seedS_roundsR.
No old output name is reused.

## First UWE steps

```bash
python -m unittest discover -s tests -p 'test_replication_contract.py' -v
python scripts/prepare_matched_replication.py --seed 42 --rounds 12 --output data/experiments/idsiot2024/replication_seed42_rounds12_v1
python -u scripts/run_matched_replication.py --seed 42 --rounds 12 --matched-experiment data/experiments/idsiot2024/replication_seed42_rounds12_v1 --attack gaussian --arm attack --sigma 0.5 --mode original --ead on --kd off --aggregation fedavg --pilot-reference outputs/development/matched_fedavg_5d5868aff5ed_gaussian_sigma0p5_attack_original_ead_on_kd_off_seed42_ead_predict_paper_3strict_v1
```

Four PILOT PREFIX EXACT MATCH messages are required, then continue to12. Runtime GPU execution pending; no performance result is promised.

After first-run verification, batch:
```bash
python -u scripts/run_replication_batch.py --matched-experiment data/experiments/idsiot2024/replication_seed42_rounds12_v1 --scenarios benign gaussian
```
It reuses the completed first Gaussian EADon/KDoff run, leaving seven additional jobs. Seed42 horizon stage totals8conditions at12rounds. Add targeted later through --scenarios targeted if it remains in the bounded budget. All3scenarios*4cells*3seeds=36runs,432communication rounds; model fits also scale with30clients and KD. This is a run count, not a walltime estimate. Do not promise same-day completion before measuring runtime.

## Evidence and decision criteria

- First4round compatibility is an implementation check, not statistical replication.
- Continue after matching only if inputs/outputs finite and reports complete. Stop for contract or prefix mismatch.
- Inspect curves at predetermined rounds4,8,12; report trajectory and round12, no best-round selection.
- Use each independent training run as replication unit. Report per-seed paired differences, means and dispersion; three-run confidence estimates are imprecise. Do not treat clients/rounds as independent samples.
- Keep proxy validation reused-for-decision limitation explicit. Final independent test remains untouched until method and final protocol are frozen.
- Master-supervision controls, benign statistical heterogeneity, H_P, adaptive/held-out threats, costs beyond elapsed time and dataset provenance remain unresolved.

## Verification

All3scripts syntax checked; screen AST equals verified predict implementation.12existing matched contract/aggregation tests and4new seed/horizon/input-mutation tests passed locally. No TensorFlow installation is available locally for full training execution; verify on UWE. Do not infer GPU success from static checks.
