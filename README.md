# EAD-DC-FL

Research planning for integrating Ensemble Anomaly Detection (EAD-FL) with server-centric Distilled Clustered Federated Learning (DC-FL).

The proposed framework groups clients by architecture, filters submitted contributions within each architecture cluster, aggregates accepted contributions, and performs cross-cluster knowledge distillation (KD) at the server. It retains one model per architecture cluster.

## Current status

Documentation stage, 14 October 2026. Training code has not been implemented and experiments have not been run in this repository. The initial notebook review was static and included stored execution traces. Reported results from the individual methods do not establish the performance of their integration.

## Planning documents

- [Method specification](docs/method_specification.md): system assumptions, round structure, proposed pilot settings, and unresolved choices.
- [Dependencies and source audit](docs/dependencies_and_source_audit.md): missing inputs, implementation discrepancies, and reproduction requirements.
- [Implementation roadmap](docs/roadmap.md): staged work and acceptance criteria.

The structural requirements are recorded for implementation. Numerical pilot settings remain provisional until the dataset, preprocessing, and original dependencies have been verified. Any subsequent methodological change must be recorded with its reason and affected comparisons.

## Immediate next step

Recover or explicitly replace the missing DC-FL helpers and complete architecture definitions. Verify the IDSIoT2024 feature schema and preprocessing, then resolve the outstanding pilot settings before implementing the benign baseline.

## Scope

This repository concerns the EAD-FL/DC-FL integration. It does not change the specifications, attack identifiers, or results of the separate WEAD-FL or heterogeneity-impact studies.

Raw datasets, trained models, notebook outputs, and experiment results are not included. Dataset acquisition and permitted redistribution must be documented before data are added. No software licence has been selected.

## Method references

The planning documents use the supplied manuscript versions:

1. Aimen Djemaa, Djamel Djenouri and Phil Legg, *EAD-FL: Ensemble Anomaly Detection to Mitigate Poisoning Attacks in Federated Learning*.
2. Aimen Djemaa, Djamel Djenouri and Phil Legg, *DC-FL: A Server-Centric Distilled Clustered Federated Learning Framework for Heterogeneous Networks*.
3. Aimen Djemaa, Djamel Djenouri and Phil Legg, *Heterogeneity-Aware Poisoning Attacks and Mitigation in Federated Learning: A Comprehensive Survey and Taxonomy*.

Bibliographic identifiers and the exact manuscript versions should be verified before preparing publication outputs. PDFs are not redistributed in this repository.
