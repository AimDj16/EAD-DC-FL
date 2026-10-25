import numpy as np
import tensorflow as tf


ARCHITECTURES = {
    "small": (128,),
    "medium": (256, 128),
    "deep": (256, 256, 128),
    "master": (1024, 512, 256),
}


def build_model(architecture, feature_count, class_count):
    if architecture not in ARCHITECTURES:
        raise ValueError(f"Unknown architecture: {architecture}")

    inputs = tf.keras.Input(shape=(feature_count,))
    hidden = inputs
    for width in ARCHITECTURES[architecture]:
        hidden = tf.keras.layers.Dense(width, activation="relu")(hidden)

    logits = tf.keras.layers.Dense(class_count)(hidden)
    return tf.keras.Model(inputs, logits, name=architecture)


def copy_weights(model):
    return [value.copy() for value in model.get_weights()]


def kd_loss(teacher_logits, student_logits, temperature=3.0):
    if temperature <= 0:
        raise ValueError("Temperature must be positive.")

    teacher_logits = tf.stop_gradient(teacher_logits)
    teacher_log_prob = tf.nn.log_softmax(
        teacher_logits / temperature, axis=-1
    )
    student_log_prob = tf.nn.log_softmax(
        student_logits / temperature, axis=-1
    )
    teacher_prob = tf.exp(teacher_log_prob)
    divergence = tf.reduce_sum(
        teacher_prob * (teacher_log_prob - student_log_prob),
        axis=-1,
    )
    return tf.reduce_mean(divergence) * temperature**2


def distil(student, teacher, features, epochs=3, batch_size=256,
           learning_rate=0.001, temperature=3.0, seed=42):
    if student is teacher:
        raise ValueError("Self-distillation must be skipped by the caller.")
    if len(features) == 0:
        raise ValueError("KD features must not be empty.")
    if epochs < 1 or batch_size < 1:
        raise ValueError("Epochs and batch size must be positive.")

    teacher_before = copy_weights(teacher)
    optimiser = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    rng = np.random.default_rng(seed)
    epoch_losses = []

    for _ in range(epochs):
        order = rng.permutation(len(features))
        loss_sum = 0.0
        sample_count = 0

        for start in range(0, len(order), batch_size):
            batch = tf.convert_to_tensor(
                features[order[start:start + batch_size]],
                dtype=tf.float32,
            )
            teacher_logits = teacher(batch, training=False)

            with tf.GradientTape() as tape:
                student_logits = student(batch, training=True)
                loss = kd_loss(
                    teacher_logits, student_logits, temperature
                )

            gradients = tape.gradient(loss, student.trainable_variables)
            if not np.isfinite(float(loss.numpy())):
                raise FloatingPointError("Non-finite KD loss.")

            for gradient in gradients:
                if gradient is None:
                    raise RuntimeError("Missing KD gradient.")
                tf.debugging.assert_all_finite(
                    gradient, "Non-finite KD gradient"
                )

            optimiser.apply_gradients(
                zip(gradients, student.trainable_variables)
            )
            batch_count = int(batch.shape[0])
            loss_sum += float(loss.numpy()) * batch_count
            sample_count += batch_count

        epoch_losses.append(loss_sum / sample_count)

    assert all(
        np.array_equal(before, after)
        for before, after in zip(teacher_before, teacher.get_weights())
    ), "Teacher weights changed during KD."

    return epoch_losses


def commit_or_revert(student, pre_kd_weights,
                     pre_kd_accuracy, candidate_accuracy):
    # Apply only in the adaptive phase, after master warm-start.
    if not np.isfinite([pre_kd_accuracy, candidate_accuracy]).all():
        student.set_weights(pre_kd_weights)
        raise ValueError("Validation accuracies must be finite.")
    if not 0 <= pre_kd_accuracy <= 1 or not 0 <= candidate_accuracy <= 1:
        student.set_weights(pre_kd_weights)
        raise ValueError("Validation accuracies must lie in [0, 1].")

    accepted = candidate_accuracy >= pre_kd_accuracy
    if not accepted:
        student.set_weights(pre_kd_weights)
    return bool(accepted)
