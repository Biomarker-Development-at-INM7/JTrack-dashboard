import logging
import os
import shlex
import subprocess
import threading

from django.conf import settings

from jdash.config import runtime_config as config

logger = logging.getLogger("django")

_PIPELINE_LOCK = threading.Lock()
_PIPELINE_IN_FLIGHT = set()
_SSH_RUNTIME_DIR = "/var/www/.ssh"


def data_per_day_candidates(study, sensor):
    return [
        os.path.join(config.analytics_storage_folder, study, f"Data_per_day_{sensor}_latest.csv"),
        os.path.join(
            config.analytics_storage_folder,
            study,
            config.analytics_outputs_folder,
            f"Data_per_day_{sensor}_latest.csv",
        ),
    ]


def has_any_data_per_day_file(study):
    study_dir = os.path.join(config.analytics_storage_folder, study)
    outputs_dir = os.path.join(study_dir, config.analytics_outputs_folder)
    candidate_dirs = [study_dir, outputs_dir]

    for directory in candidate_dirs:
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if filename.lower().startswith("data_per_day_") and filename.lower().endswith(".csv"):
                return True
    return False


def _build_pipeline_command(study):
    study_dir = os.path.join(config.analytics_storage_folder, study)
    outputs_dir = os.path.join(study_dir, config.analytics_outputs_folder)

    raw_command = getattr(settings, "ANALYTICS_PIPELINE_COMMAND", None) or os.getenv(
        "ANALYTICS_PIPELINE_COMMAND", ""
    )
    if raw_command:
        try:
            formatted = raw_command.format(
                study=study,
                study_dir=study_dir,
                outputs_dir=outputs_dir,
                studies_root=config.analytics_storage_folder,
            )
        except KeyError:
            formatted = raw_command
        logger.info("Resolved analytics pipeline custom command for study=%s", study)
        return shlex.split(formatted)

    remote_script = getattr(settings, "ANALYTICS_PIPELINE_REMOTE_SCRIPT", None)
        

    remote_host = getattr(settings, "JUSELESS_SERVER", None) or os.getenv("JUSELESS_SERVER", "")
    remote_user = getattr(settings, "REMOTE_USERNAME", None) or os.getenv("REMOTE_USERNAME", "")
    if remote_host and remote_user and remote_script:
        os.makedirs(_SSH_RUNTIME_DIR, exist_ok=True)
        known_hosts_path = os.path.join(_SSH_RUNTIME_DIR, "known_hosts")
        ssh_key_path = getattr(settings, "ANALYTICS_PIPELINE_SSH_KEY", None) or os.getenv(
            "ANALYTICS_PIPELINE_SSH_KEY",
            "",
        )
        if not ssh_key_path:
            ssh_key_path = "/var/www/.ssh/id_ed25519_pipeline"
        logger.info(
            "Resolved analytics pipeline remote command for study=%s host=%s user=%s script=%s ssh_key=%s",
            study,
            remote_host,
            remote_user,
            remote_script,
            ssh_key_path,
        )
        command = [
            "ssh",
            "-o",
            f"UserKnownHostsFile={known_hosts_path}",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
        ]
        if ssh_key_path:
            command.extend(
                [
                    "-o",
                    "IdentitiesOnly=yes",
                    "-i",
                    ssh_key_path,
                ]
            )
        command.extend(
            [
            f"{remote_user}@{remote_host}",
            "python3",
            remote_script,
            "--study",
            study,
            ]
        )
        return command
    return []


def _run_pipeline(study, command):
    logger.info("Starting analytics pipeline for study=%s", study)
    logger.info("Executing analytics pipeline command for study=%s command=%s", study, command)
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "HOME": _SSH_RUNTIME_DIR},
        )
        output_lines = []
        if process.stdout is not None:
            for line in process.stdout:
                message = line.rstrip()
                output_lines.append(message)
        return_code = process.wait()
        combined_output = "\n".join(output_lines)
        if return_code == 0:
            logger.info(
                "Analytics pipeline finished successfully for study=%s stdout=%s",
                study,
                combined_output[-1000:],
            )
        else:
            logger.warning(
                "Analytics pipeline failed for study=%s returncode=%s stdout=%s",
                study,
                return_code,
                combined_output[-1000:],
            )
    except Exception:
        logger.exception("Analytics pipeline crashed for study=%s", study)
    finally:
        with _PIPELINE_LOCK:
            _PIPELINE_IN_FLIGHT.discard(study)
        logger.info("Cleared analytics pipeline in-flight state for study=%s", study)


def trigger_pipeline_if_needed(study, sensor=None):
    if not study:
        logger.info("Skipping analytics pipeline trigger because study is empty.")
        return False

    if sensor:
        if any(os.path.exists(path) for path in data_per_day_candidates(study, sensor)):
            logger.info(
                "Skipping analytics pipeline for study=%s sensor=%s because data_per_day file already exists.",
                study,
                sensor,
            )
            return False
    elif has_any_data_per_day_file(study):
        logger.info(
            "Skipping analytics pipeline for study=%s because at least one data_per_day file already exists.",
            study,
        )
        return False

    command = _build_pipeline_command(study)
    if not command:
        logger.warning(
            "Analytics pipeline was requested for study=%s but no command/script could be resolved.",
            study,
        )
        return False

    with _PIPELINE_LOCK:
        if study in _PIPELINE_IN_FLIGHT:
            logger.info("Analytics pipeline already in flight for study=%s", study)
            return False
        _PIPELINE_IN_FLIGHT.add(study)
        logger.info("Marked analytics pipeline as in flight for study=%s", study)

    thread = threading.Thread(target=_run_pipeline, args=(study, command), daemon=True)
    thread.start()
    logger.info("Analytics pipeline thread started for study=%s", study)
    return True

