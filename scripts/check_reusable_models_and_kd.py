import sys
from pathlib import Path

import numpy as np
import tensorflow as tf

sys.path.insert(0, str(Path("src").resolve()))
from ead_dc_fl.models_and_kd import (
    build_model, copy_weights, kd_loss, distil, commit_or_revert,
)

tf.keras.utils.set_random_seed(42)
rng = np.random.default_rng(42)
features = rng.normal(size=(16, 96)).astype(np.float32)

teacher = build_model("deep", 96, 7)
student = build_model("small", 96, 7)
teacher_before = copy_weights(teacher)
student_before = copy_weights(student)

logits = teacher(features, training=False)
assert abs(float(kd_loss(logits, logits).numpy())) < 1e-6

losses = distil(
    student, teacher, features,
    epochs=1, batch_size=8, seed=42,
)
candidate_weights = copy_weights(student)

assert any(
    not np.array_equal(before, after)
    for before, after in zip(student_before, candidate_weights)
)
assert all(
    np.array_equal(before, after)
    for before, after in zip(teacher_before, teacher.get_weights())
)

# Synthetic validation values check policy behaviour, not model accuracy.
assert not commit_or_revert(student, student_before, 0.80, 0.79)
assert all(
    np.array_equal(before, after)
    for before, after in zip(student_before, student.get_weights())
)

student.set_weights(candidate_weights)
assert commit_or_revert(student, student_before, 0.80, 0.81)
assert all(
    np.array_equal(before, after)
    for before, after in zip(candidate_weights, student.get_weights())
)

assert commit_or_revert(student, student_before, 0.80, 0.80)

print(f"Synthetic KD epoch loss: {losses[0]:.6f}")
print("Teacher unchanged: PASS")
print("Student optimisation: PASS")
print("Rejected candidate restores pre-KD weights: PASS")
print("Accepted candidate retains KD weights: PASS")
print("Equal validation accuracy accepted: PASS")
print("REUSABLE MODEL AND KD CHECKS: PASS")
