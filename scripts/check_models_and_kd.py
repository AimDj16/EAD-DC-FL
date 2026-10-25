import json
from pathlib import Path

import numpy as np
import tensorflow as tf

tf.keras.utils.set_random_seed(42)

manifest_path = Path(
    "data/partitions/idsiot2024/candidate_seed42_groups2/manifest.json"
)
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

input_dim = len(manifest["feature_names"])
classes = manifest["classes"]
num_classes = len(classes)

assert input_dim == 96
assert num_classes == 7

architectures = {
    "small": [128],
    "medium": [256, 128],
    "deep": [256, 256, 128],
    "master": [1024, 512, 256],
}


def build_model(name, widths):
    layers = [tf.keras.Input(shape=(input_dim,))]
    layers.extend(
        tf.keras.layers.Dense(width, activation="relu")
        for width in widths
    )
    layers.append(tf.keras.layers.Dense(num_classes, activation=None))
    return tf.keras.Sequential(layers, name=name)


def kd_loss(teacher_logits, student_logits, temperature=3.0):
    temperature = tf.cast(temperature, tf.float32)
    teacher_log_probs = tf.nn.log_softmax(
        tf.stop_gradient(teacher_logits) / temperature, axis=-1
    )
    student_log_probs = tf.nn.log_softmax(
        student_logits / temperature, axis=-1
    )
    teacher_probs = tf.exp(teacher_log_probs)
    per_sample = tf.reduce_sum(
        teacher_probs * (teacher_log_probs - student_log_probs),
        axis=-1
    )
    return tf.reduce_mean(per_sample) * temperature**2


models = {
    name: build_model(name, widths)
    for name, widths in architectures.items()
}

rng = np.random.default_rng(42)
x = tf.constant(rng.normal(size=(8, input_dim)).astype(np.float32))
y = tf.constant(rng.integers(0, num_classes, size=8), dtype=tf.int32)

parameter_counts = {}
for name, model in models.items():
    logits = model(x, training=False)
    assert tuple(logits.shape) == (8, num_classes)
    assert bool(tf.reduce_all(tf.math.is_finite(logits)).numpy())
    assert model.layers[-1].activation == tf.keras.activations.linear
    parameter_counts[name] = model.count_params()
    print(f"{name}: parameters={model.count_params()}, output={logits.shape}")

student = models["small"]
teacher = models["master"]
teacher.trainable = False

teacher_before = [w.copy() for w in teacher.get_weights()]
student_before = [w.copy() for w in student.get_weights()]

teacher_logits = teacher(x, training=False)
student_logits = student(x, training=False)

identity_loss = float(kd_loss(teacher_logits, teacher_logits).numpy())
assert abs(identity_loss) < 1e-6

ce_loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
ce_value = float(ce_loss(y, student_logits).numpy())
assert np.isfinite(ce_value)

optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
with tf.GradientTape() as tape:
    logits = student(x, training=True)
    loss = kd_loss(teacher_logits, logits)

gradients = tape.gradient(loss, student.trainable_variables)
assert all(g is not None for g in gradients)
assert all(
    bool(tf.reduce_all(tf.math.is_finite(g)).numpy())
    for g in gradients
)

loss_value = float(loss.numpy())
gradient_norm = float(tf.linalg.global_norm(gradients).numpy())
assert np.isfinite(loss_value) and loss_value >= -1e-6
assert np.isfinite(gradient_norm) and gradient_norm > 0

optimizer.apply_gradients(zip(gradients, student.trainable_variables))

teacher_unchanged = all(
    np.array_equal(before, after)
    for before, after in zip(teacher_before, teacher.get_weights())
)
student_changed = any(
    not np.array_equal(before, after)
    for before, after in zip(student_before, student.get_weights())
)

assert teacher_unchanged
assert student_changed

report = {
    "status": "synthetic_checks_passed",
    "tensorflow_version": tf.__version__,
    "input_dim": input_dim,
    "classes": classes,
    "parameter_counts": parameter_counts,
    "temperature": 3.0,
    "identity_kl_loss": identity_loss,
    "synthetic_ce_loss": ce_value,
    "synthetic_kd_loss": loss_value,
    "gradient_norm": gradient_norm,
    "teacher_unchanged": teacher_unchanged,
    "student_changed": student_changed,
    "synthetic_optimisation_steps": 1,
    "real_dataset_training_performed": False,
    "federated_training_performed": False,
}

output = Path("outputs/checks/models_and_kd_smoke/report.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

print("\nIdentity KL loss:", identity_loss)
print("Synthetic KD loss:", loss_value)
print("Gradient norm:", gradient_norm)
print("Teacher unchanged:", teacher_unchanged)
print("Student changed:", student_changed)
print("MODEL AND KD CHECKS: PASS")
print("Saved:", output)
