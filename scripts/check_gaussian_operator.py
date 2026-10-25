import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path("src").resolve()))
from ead_dc_fl.attacks import gaussian_weight_poisoning

weights = [
    np.ones((200, 100), dtype=np.float32),
    np.zeros(100, dtype=np.float32),
]
original = [value.copy() for value in weights]

arguments = dict(sigma=0.05, seed=242, round_number=1, client_id=0)
first, diagnostics = gaussian_weight_poisoning(weights, **arguments)
second, _ = gaussian_weight_poisoning(weights, **arguments)

assert all(np.array_equal(a, b) for a, b in zip(first, second))
assert all(np.array_equal(a, b) for a, b in zip(weights, original))
assert all(a.shape == b.shape and a.dtype == b.dtype
           for a, b in zip(first, weights))

# Verify the exact seeded additive operator.
rng = np.random.default_rng(np.random.SeedSequence([242, 1, 0]))
expected = [
    (value.astype(np.float64)
     + rng.normal(0.0, 0.05, size=value.shape)).astype(value.dtype)
    for value in weights
]
assert all(np.array_equal(a, b) for a, b in zip(first, expected))

other_round, _ = gaussian_weight_poisoning(
    weights, 0.05, 242, 2, 0
)
other_client, _ = gaussian_weight_poisoning(
    weights, 0.05, 242, 1, 1
)
assert not np.array_equal(first[0], other_round[0])
assert not np.array_equal(first[0], other_client[0])

unchanged, _ = gaussian_weight_poisoning(weights, 0.0, 242, 1, 0)
assert all(np.array_equal(a, b) for a, b in zip(unchanged, weights))

for invalid in (-1.0, np.nan, np.inf):
    try:
        gaussian_weight_poisoning(weights, invalid, 242, 1, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid sigma was accepted.")

output = Path("outputs/checks/gaussian_operator/report.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({
    "status": "pass",
    "operator": "local_model_plus_absolute_gaussian_noise",
    "diagnostics": diagnostics,
    "training_performed": False,
    "final_sigma_selected": False,
}, indent=2), encoding="utf-8")

print("Exact seeded additive noise: PASS")
print("Shapes, dtypes and original weights preserved: PASS")
print("Client and round noise separation: PASS")
print("Zero sigma and invalid sigma checks: PASS")
print("GAUSSIAN OPERATOR CHECKS: PASS")
print(f"Saved: {output}")
