# Dependencies and source audit

Static notebook review conducted on 13 October 2026; repository planning recorded on 14 October 2026. The notebooks were not rerun. Source text and stored outputs may represent different execution states.

## Reviewed inputs

| Input | Role | SHA-256 of reviewed notebook |
|---|---|---|
| main.ipynb | DC-FL prototype, 15 cells | 0fdb5e439a23fa5de3f557f85a8a3775fcf58ab4b107639628fcddd8261fb05f |
| main(1).ipynb | EAD-FL experiments, 69 cells | cb06863e311c06d27b256e264476894e70b4bfc4934bf8e10fa7026718c6e291 |

The associated method references are listed in the [README](../README.md). Original notebooks, data, and PDF attachments have not been copied into this repository. Their hashes identify the reviewed notebook versions, not validated implementations.

## Recovery status, 14 October 2026

A GitHub inventory search and complete current default-branch tree listings were inspected for the accessible research repositories. Code searches for group_clients_by_model_shape, create_model_deep and Attack_Category_x returned no matches. This does not establish absence from local files, other branches, historical commits, or unindexed content. A separate legacy notebook returned no content through the connector and could not be inspected.

| Dependency | Recovery outcome | Remaining action |
|---|---|---|
| utility.py | Not recovered from the inspected current repository trees | Obtain the original or document a reconstruction of its grouping contract |
| client_models.py and create_model_deep | Not recovered | Obtain the original; otherwise use explicitly reconstructed paper architectures |
| Small/Medium/Deep architecture specification | Available in the supplied DC-FL manuscript | Verify definitions during implementation; original weights and helper source remain unavailable |
| Process_1 IDS-IoT-2024.csv identity | A related-study configuration and checksum record were located | Obtain the local file and independently check its bytes and schema |
| df_test_reduced.csv | No matching current repository path found | Obtain the exact file or document a replacement and its relationship to the processed CSV |
| Original preprocessing pipeline | Not recovered | Obtain the generation script or audit the processed representation and state inherited limitations |
| Original package environment | Not recovered | Obtain an environment export, or label the new environment as reconstructed |

The related-study metadata records a processed representation with 96,280 rows, 97 columns, seven classes and target column Attack_Category_x. The configuration and checksum record agree on the expected SHA-256:

54b24fb0405e5f6f03ae2792c65bbd93a98db47e573778d1f4cd3719b6859fbd

This is a reference checksum, not a fresh validation of the dataset in this repository. The raw CSV was not available through GitHub. The existing study's metadata also leaves the generation of the inherited processed representation unresolved; equivalence to an official preprocessed release is not established.

The references were read through authorised GitHub access on 14 October 2026: the IDSIoT2024 dataset configuration blob 2af9e2103312fcc4350e1072b37289495cc08397 and checksum-record blob a4bbbeef8e7a9458c46245e724af2b9f0bfec739. These records are evidence for locating and checking the local file, not replacement preprocessing code.

No private source code, notebook content, or raw data was copied into this public repository. The other study's split policy, client count and frozen experimental settings are not adopted by EAD-DC-FL. This recovery stage changes dependency status only; it does not authorise claims of exact reproduction.

## Inputs needed before implementation

- [ ] Obtain utility.py and inspect the return contract of group_clients_by_model_shape.
- [ ] Obtain client_models.py and the missing create_model_deep definition.
- [ ] Identify the authoritative Small/Medium/Deep and optional master definitions for paper reproduction.
- [x] Locate a reference identity and checksum record for Process_1 IDS-IoT-2024.csv (indirect metadata only).
- [ ] Obtain and hash the actual CSV versions referenced by the notebooks: df_test_reduced.csv and Process_1 IDS-IoT-2024.csv, or document their replacement.
- [ ] Verify how those CSVs were generated, including encoding, normalisation, feature selection, missing-value handling and duplication.
- [ ] Verify feature names, target placement, class mapping, row count and dataset identity.
- [ ] Obtain the original package versions if available, including TensorFlow/Keras, NumPy, pandas, scikit-learn and PyOD.
- [ ] Decide whether missing helpers will be recovered or reconstructed from the method contract. Mark reconstructed components explicitly; do not claim exact reproduction.
- [ ] Resolve data allocation fractions, training budgets, optimiser-state handling and numerical pilot settings in the specification.

## Findings to resolve

Cell numbers refer to the physical cell order in the reviewed notebook.

| Finding | Location or evidence | Required action |
|---|---|---|
| Train/test variables are referenced without an active defining split | DC-FL cells 4-6 | Make the complete data pipeline explicit |
| Missing imports and deep model definition | DC-FL cells 2, 9 and 13 | Recover or document replacements |
| Independent client sampling produces overlapping allocations | DC-FL cell 6; EAD-FL IID loops | Use disjoint allocations and record indices |
| Cluster enumeration is used as architecture identity | DC-FL cells 13 and 15 | Register architecture identifiers and tensor schemas |
| A grouping result is treated as a dictionary although a saved error reports a tuple | DC-FL cell 15 | Verify and standardise the helper contract |
| Softmax outputs are treated as logits, with repeated softening in the earlier KD loop | DC-FL cells 7, 11, 13 and 15 | Use verified logits and temperature-scaled KL |
| Supplied notebook mainly implements S2, rather than paper-default S4 | DC-FL cells 13 and 15 | Keep strategies explicit; implement S4 separately |
| Notebook hidden-layer sizes and budgets differ from the paper | DC-FL model builders and round settings | Separate notebook reconstruction from paper reproduction |
| Sign flipping negates all full-weight tensors; label flipping is absent | EAD-FL cell 5 | Define exact attack objects and separate variants |
| Binary strict-vote intersection is used to trigger contamination adjustment | EAD-FL cells 24, 25 and 27 | Replace this condition only in the paper-rule configuration; preserve audit traceability |
| Some calibration variants change contamination without immediate rerunning | EAD-FL cells 24 and 27 | Record activation and persistence semantics explicitly |
| Several methods are logged with accuracy from one selected defence trajectory | EAD-FL cells 14-27 | Run downstream method comparisons independently |
| Accuracy is saved before current-round evaluation | EAD-FL cells 59-62 | Associate metrics with the correct round and model state |
| unflatten_weights contains reshapev; flattened-vector and metadata contracts are inconsistent in a saved trace | EAD-FL cell 10 and stored cell 25 error | Verify exact flatten/reconstruct round trips |
| Duplicate definitions and experiment loops depend on notebook state | EAD-FL throughout | Use reusable components and explicit configuration |
| Empty-inlier handling is absent in many loops; M3D variant restores all rejected inputs | EAD-FL aggregation blocks and cell 36 | Define failure policies without silent reintroduction |
| Python, NumPy, TensorFlow and detector randomness are not comprehensively controlled | Both notebooks | Separate and record random streams |

The static review does not establish feature leakage, dataset quality, convergence, or the correctness of saved numerical results. The input CSVs and missing modules were not supplied. Stored exceptions are diagnostic evidence, not fresh execution results.

## Reproduction distinctions

Maintain three explicit categories:

1. Notebook reconstruction: preserve the supplied notebook behaviour where feasible, including documented deviations.
2. Paper reproduction: implement the stated method and record any ambiguities or reconstructed components.
3. Combined-framework experiments: apply the declared adaptations for architecture-specific filtering, failure handling and comparisons.

Do not silently present a corrected notebook, new architecture, update-based attack, or modified S4 acceptance metric as the original implementation.

## Runtime dependencies

The notebooks use TensorFlow/Keras for models and KD; PyOD for detectors; scikit-learn for preprocessing, splitting and evaluation; NumPy and pandas for numerical processing and records; and plotting libraries for analysis.

TensorFlow/Keras is the proposed starting runtime to minimise migration from the supplied code. Package versions, CPU/GPU support and the exact environment remain unverified. Do not add an executable requirements file with guessed versions. Freeze and record a tested environment during implementation, including hardware and determinism limitations.
