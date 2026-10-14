# Original helper references

These files were supplied by the researcher on 14 October 2026 and are archived unchanged. They are reference inputs, not the EAD-DC-FL implementation.

| File | SHA-256 |
|---|---|
| client_models.py | da2481d73c4958d5839736f62676da7ef7532c65b24e732bc91b1691a4118d5d |
| utility.py | 5aafac7a11532236a5da6b82e5c9dcdcf5e6f4f527c8ea9219b4ce28bbdf4dad |

See the [source audit](../../docs/dependencies_and_source_audit.md) for architecture differences, softmax/logit handling, grouping return values and aggregation semantics.

The utility functions passed limited synthetic checks. TensorFlow models and training have not been executed. Future implementation must not import these files as validated components without resolving the documented differences.
