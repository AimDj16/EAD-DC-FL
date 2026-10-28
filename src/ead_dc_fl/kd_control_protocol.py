"""Protocol checks for separately identified within-FL KD schedule controls.

No TensorFlow dependency. These controls change KD exposure, not local training,
data, participants, attack identities, aggregation or the original runner.
"""
from pathlib import Path


POLICIES = ("warm_start_only", "adaptive_only", "full_replay")
ARCHITECTURES = ("small", "medium", "deep")
PRE_KD_KEYS = (
    "client_ids", "local_training_order_sha256", "local_losses",
    "upload_diagnostics", "initial_detection", "initial_detector_flagged_counts",
    "calibration_rerun", "final_contamination", "final_detection", "vote_counts",
    "rejected_client_ids", "accepted_count", "retained_previous_model",
    "accepted_sample_counts", "fedavg_coefficients", "pre_kd_validation",
)
COMMON_KEYS = (
    "matched_experiment_id", "initial_state_sha256", "seed", "planned_rounds",
    "training_settings", "execution_environment", "source_sha256",
    "client_manifest_sha256", "master_weights_sha256", "models_and_kd_sha256",
    "attack_operator_sha256", "compromised_selection_sha256", "attack_protocol",
    "kd_rows_used", "aggregation", "ead_enabled", "kd_enabled", "mode", "arm",
)


def phase_for_round(policy, round_number, warm_rounds=3):
    if policy not in POLICIES:
        raise ValueError("Unknown KD control policy: " + str(policy))
    if round_number < 1 or warm_rounds < 1:
        raise ValueError("Round numbers and warm-start horizon must be positive.")
    if policy != "adaptive_only" and round_number <= warm_rounds:
        return "master_warm_start"
    return "no_kd" if policy == "warm_start_only" else "adaptive"


def exact_prefix_length(policy, rounds, warm_rounds=3):
    phase_for_round(policy, 1, warm_rounds)
    return rounds if policy == "full_replay" else (
        min(rounds, warm_rounds) if policy == "warm_start_only" else 0
    )


def original_directory(manifest, arm, ead="on", root=Path("outputs/development")):
    attack = "gaussian" if arm == "benign" else "targeted"
    return Path(root) / (
        f"matched_fedavg_{manifest['experiment_id'][:12]}_replication_predict3_"
        f"{attack}_sigma0p0_{arm}_original_ead_{ead}_kd_on_"
        f"seed{manifest['seed']}_rounds{manifest['rounds']}"
    )


def control_directory(manifest, policy, arm, ead="on", root=Path("outputs/controls")):
    phase_for_round(policy, 1)
    return Path(root) / (
        f"matched_fedavg_{manifest['experiment_id'][:12]}_kd_schedule_{policy}_"
        f"{arm}_ead_{ead}_seed{manifest['seed']}_rounds{manifest['rounds']}_v1"
    )


def validate_reference(report, manifest, arm, ead, original_runner_hash):
    expected = {
        "status": "completed", "configuration_id": "matched_replication_predict3_v1",
        "matched_experiment_id": manifest["experiment_id"],
        "seed": manifest["seed"], "planned_rounds": manifest["rounds"],
        "training_settings": manifest["training_settings"], "mode": "original",
        "arm": arm, "ead_enabled": ead == "on", "kd_enabled": True,
        "aggregation": "sample_weighted_fedavg", "script_sha256": original_runner_hash,
        "test_evaluated": False, "final_protocol_frozen": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError("Original reference differs: " + key)
    records = report.get("rounds", [])
    if [r["round"] for r in records] != list(range(1, manifest["rounds"] + 1)):
        raise ValueError("Original reference rounds are incomplete or unordered.")
    if arm == "benign":
        if (report["attack_protocol"]["attack"] != "untargeted_additive_gaussian_weight_poisoning"
                or report["attack_protocol"]["sigma"] != 0):
            raise ValueError("Expected the shared Gaussian-runner benign reference.")
    elif not (report["attack_protocol"].get("attack") == "targeted_label_flipping"
              and report["attack_protocol"].get("source_class") == "Malware"
              and report["attack_protocol"].get("destination_class") == "Normal"):
        raise ValueError("Expected Malware-to-Normal targeted reference.")


def verify_common_inputs(current, reference):
    missing = [key for key in COMMON_KEYS if key not in current or key not in reference]
    if missing:
        raise ValueError("Missing original/control input metadata: " + ", ".join(missing))
    differences = [key for key in COMMON_KEYS if current.get(key) != reference.get(key)]
    if differences:
        raise ValueError("Original reference input mismatch: " + ", ".join(differences))


def verify_first_pre_kd(current_round, reference_round):
    """Before the first intervention, every policy must reproduce local updates/EAD."""
    differences = []
    for architecture in ARCHITECTURES:
        current = current_round["clusters"][architecture]
        reference = reference_round["clusters"][architecture]
        differences.extend(architecture + "/" + key for key in PRE_KD_KEYS
                           if current.get(key) != reference.get(key))
    if current_round["participation"] != reference_round["participation"]:
        differences.append("participation")
    if differences:
        raise ValueError("Round-1 pre-KD replay differs: " + ", ".join(differences))


def verify_exact_prefix(current_round, reference_round):
    """Exact records in a shared-policy prefix; checkpoint tensors checked by runner."""
    keys = ("round", "phase", "teacher", "teacher_tie_breaking", "participation",
            "participation_sha256", "clusters")
    differences = [key for key in keys if current_round[key] != reference_round[key]]
    if differences:
        raise ValueError("Shared-policy prefix differs: " + ", ".join(differences))


def verify_policy_record(record, policy):
    expected_phase = phase_for_round(policy, record["round"])
    if record["phase"] != expected_phase:
        raise ValueError("Recorded KD phase does not match control policy.")
    teacher = record["teacher"]
    if expected_phase == "master_warm_start" and teacher != "master":
        raise ValueError("Warm-start must use the saved master.")
    if expected_phase == "no_kd" and teacher is not None:
        raise ValueError("Warm-start-only must have no subsequent teacher.")
    if expected_phase == "adaptive" and teacher not in (*ARCHITECTURES, None):
        raise ValueError("Adaptive-only must not use the master teacher.")
    for architecture, cluster in record["clusters"].items():
        kd = cluster["kd"]
        if (not kd["performed"]
                and cluster["post_kd_validation"] != cluster["pre_kd_validation"]):
            raise ValueError("Skipped KD changed recorded metrics.")
        if expected_phase == "no_kd":
            if kd != {"performed": False, "reason": "kd_schedule_disabled"}:
                raise ValueError("KD was not disabled after the warm-start horizon.")
            if cluster["post_kd_validation"] != cluster["pre_kd_validation"]:
                raise ValueError("Disabled KD changed recorded metrics.")
        elif cluster["retained_previous_model"]:
            if kd != {"performed": False, "reason": "no_accepted_uploads"}:
                raise ValueError("No-upload fallback must skip KD.")
        elif teacher is None:
            if kd != {"performed": False, "reason": "no_eligible_teacher"}:
                raise ValueError("No eligible teacher must skip KD.")
        elif architecture == teacher:
            if kd != {"performed": False, "reason": "teacher_self_distillation"}:
                raise ValueError("Adaptive teacher must skip self-distillation.")
        else:
            if not kd["performed"]:
                raise ValueError("Scheduled eligible KD was not performed.")
            pre = cluster["pre_kd_validation"]["accuracy"]
            candidate = kd["candidate_validation"]["accuracy"]
            unconditional = expected_phase == "master_warm_start"
            expected_acceptance = unconditional or candidate >= pre
            if kd["accepted"] != expected_acceptance:
                raise ValueError("Control acceptance differs from original accuracy policy.")
            expected_metrics = kd["candidate_validation"] if expected_acceptance else cluster["pre_kd_validation"]
            if cluster["post_kd_validation"] != expected_metrics:
                raise ValueError("Committed metrics do not match the KD decision.")


def paired_summary(benign, attack):
    """Descriptive within-policy comparisons; rounds are not replications."""
    if benign["arm"] != "benign" or attack["arm"] != "attack":
        raise ValueError("Require benign and attack reports in that order.")
    keys = ("matched_experiment_id", "seed", "planned_rounds", "kd_policy", "ead_enabled")
    if any(benign.get(k) != attack.get(k) for k in keys):
        raise ValueError("Cannot pair different KD policies or matched inputs.")
    if benign["status"] != "completed" or attack["status"] != "completed":
        raise ValueError("Cannot summarise incomplete reports.")
    if len(benign["rounds"]) != benign["planned_rounds"] or len(attack["rounds"]) != attack["planned_rounds"]:
        raise ValueError("Cannot summarise incomplete rounds.")
    rows = []
    for architecture in ARCHITECTURES:
        excess, kd_performed, kd_accepted = [], 0, 0
        for b, a in zip(benign["rounds"], attack["rounds"]):
            if b["round"] != a["round"]:
                raise ValueError("Paired round numbers differ.")
            bc, ac = b["clusters"][architecture], a["clusters"][architecture]
            excess.append(100 * (ac["post_kd_validation"]["targeted_misclassification_rate"]
                                 - bc["post_kd_validation"]["targeted_misclassification_rate"]))
            kd_performed += int(ac["kd"]["performed"])
            kd_accepted += int(ac["kd"].get("accepted", False))
        final_b = benign["rounds"][-1]["clusters"][architecture]["post_kd_validation"]
        final_a = attack["rounds"][-1]["clusters"][architecture]["post_kd_validation"]
        rows.append({
            "architecture": architecture,
            "benign_final_accuracy": final_b["accuracy"],
            "attack_final_accuracy": final_a["accuracy"],
            "benign_final_macro_f1": final_b["macro_f1"],
            "attack_final_macro_f1": final_a["macro_f1"],
            "attack_final_tmr": final_a["targeted_misclassification_rate"],
            "peak_positive_excess_tmr_pp": max(0.0, *excess),
            "attack_minus_benign_tmr_pp_by_round": excess,
            "attack_kd_phases_performed": kd_performed,
            "attack_kd_candidates_accepted": kd_accepted,
        })
    return rows
