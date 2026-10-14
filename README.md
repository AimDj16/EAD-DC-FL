# EAD-DC-FL

Research planning for integrating Ensemble Anomaly Detection (EAD-FL) with server-centric Distilled Clustered Federated Learning (DC-FL).

The proposed framework combines DC-FL's adaptive S4 distillation with calibrated EAD-FL filtering and Median aggregation within architecture clusters. It retains one model per architecture cluster. The principal study evaluates targeted poisoning and whether harmful class-specific behaviour survives filtering or transfers through server-side knowledge distillation (KD).

## Current status

Planning and source-audit stage, 14 October 2026. No new training implementation or experiment has been run in this repository. The supplied original helper files are preserved in references/legacy; their grouping and equal-weight averaging functions passed limited synthetic checks. Model construction and training remain unverified. Results from the individual methods do not establish targeted-attack robustness or the performance of their integration.

## Planning documents

- [Method specification](docs/method_specification.md): system assumptions, round structure, proposed pilot settings, and unresolved choices.
- [Dependencies and source audit](docs/dependencies_and_source_audit.md): missing inputs, implementation discrepancies, and reproduction requirements.
- [Implementation roadmap](docs/roadmap.md): staged work and acceptance criteria.
- [Targeted-attack study](docs/targeted_attack_study.md): baseline selection, attack definitions, evaluation and the evidence needed to motivate WEAD-FL.
- [Legacy helper references](references/legacy/README.md): unchanged uploaded source files and verified hashes.

The structural requirements are recorded for implementation. Numerical pilot settings remain provisional until the dataset, preprocessing, and original dependencies have been verified. Any subsequent methodological change must be recorded with its reason and affected comparisons.

## Immediate next step

The DC-FL helpers have now been supplied and inspected. Resolve their differences from the paper, obtain and verify the processed IDSIoT2024 data and preprocessing, and specify S4's master-training and warm-start settings before implementing the benign baseline.

## Scope

This repository evaluates targeted poisoning against the strongest supported EAD-FL/DC-FL components. It is intended to establish an empirical motivation for WEAD-FL if limitations are observed. Neither failure of EAD-DC-FL nor improvement from WEAD-FL is assumed. The specifications, attack identifiers, and frozen results of those separate studies are unchanged.

Raw datasets, trained models, notebook outputs, and experiment results are not included. Dataset acquisition and permitted redistribution must be documented before data are added. No software licence has been selected.

## Method references

The planning documents use the supplied manuscript versions:

1. Aimen Djemaa, Djamel Djenouri and Phil Legg, *EAD-FL: Ensemble Anomaly Detection to Mitigate Poisoning Attacks in Federated Learning*.
2. Aimen Djemaa, Djamel Djenouri and Phil Legg, *DC-FL: A Server-Centric Distilled Clustered Federated Learning Framework for Heterogeneous Networks*.
3. Aimen Djemaa, Djamel Djenouri and Phil Legg, *Heterogeneity-Aware Poisoning Attacks and Mitigation in Federated Learning: A Comprehensive Survey and Taxonomy*.

Bibliographic identifiers and the exact manuscript versions should be verified before preparing publication outputs. PDFs are not redistributed in this repository.
