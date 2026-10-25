import numpy as np


def gaussian_weight_poisoning(weights, sigma, seed, round_number, client_id):
    if not np.isfinite(sigma) or sigma < 0:
        raise ValueError("Sigma must be finite and non-negative.")
    for value in (seed, round_number, client_id):
        if not isinstance(value, (int, np.integer)) or value < 0:
            raise ValueError("Seed, round and client ID must be non-negative integers.")
    if not weights:
        raise ValueError("Weights must not be empty.")

    rng = np.random.default_rng(
        np.random.SeedSequence([seed, round_number, client_id])
    )
    poisoned = []
    noise_squared_norm = 0.0
    original_squared_norm = 0.0
    parameter_count = 0

    for tensor in weights:
        original = np.asarray(tensor)
        if not np.issubdtype(original.dtype, np.floating):
            raise ValueError("Model weights must have floating-point dtype.")
        if not np.isfinite(original).all():
            raise ValueError("Model weights must be finite.")

        if sigma == 0:
            submitted = original.copy()
        else:
            noise = rng.normal(0.0, sigma, size=original.shape)
            submitted = (original.astype(np.float64) + noise).astype(
                original.dtype
            )

        if not np.isfinite(submitted).all():
            raise FloatingPointError("Poisoned weights are non-finite.")

        actual_noise = (
            submitted.astype(np.float64) - original.astype(np.float64)
        )
        noise_squared_norm += float(np.sum(actual_noise**2))
        original_squared_norm += float(
            np.sum(original.astype(np.float64)**2)
        )
        parameter_count += original.size
        poisoned.append(submitted)

    noise_norm = float(np.sqrt(noise_squared_norm))
    original_norm = float(np.sqrt(original_squared_norm))
    diagnostics = {
        "sigma": float(sigma),
        "parameter_count": int(parameter_count),
        "noise_l2_norm": noise_norm,
        "noise_rms": float(np.sqrt(noise_squared_norm / parameter_count))
            if parameter_count else 0.0,
        "original_weight_l2_norm": original_norm,
        "noise_to_weight_norm_ratio": (
            noise_norm / original_norm if original_norm > 0 else None
        ),
    }
    return poisoned, diagnostics
