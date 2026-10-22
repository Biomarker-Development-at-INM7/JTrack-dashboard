import os
import time
from pathlib import Path

from jdash.config import runtime_config as config


def request_study_csv_refresh(
    study_id: str,
    max_age_seconds: int = 30,
    timeout_seconds: int = 60,
    poll_interval_seconds: float = 0.25,
) -> bool:
    """
    Request a dashboard CSV refresh without blocking the page request.

    Returns True when the existing CSV is recent enough. Returns False after
    ensuring that a background refresh marker exists. ``timeout_seconds`` and
    ``poll_interval_seconds`` remain in the signature for caller compatibility
    but are intentionally unused: the details page must render immediately
    from the latest available CSV.
    """
    if not study_id or Path(study_id).name != study_id:
        raise ValueError("Invalid study ID")

    storage_folder = Path(config.storage_folder)
    study_folder = Path(config.studies_folder) / study_id
    request_folder = storage_folder / "csv_requests"
    request_path = request_folder / study_id
    csv_path = storage_folder / f"{config.csv_prefix}{study_id}.csv"

    if not study_folder.is_dir():
        raise FileNotFoundError(f"Unknown study: {study_id}")

    if not request_folder.is_dir():
        raise RuntimeError(
            f"CSV request directory does not exist: {request_folder}"
        )

    # Reuse a recently generated CSV.
    if csv_path.is_file():
        age_seconds = time.time() - csv_path.stat().st_mtime
        if age_seconds <= max_age_seconds:
            return True

    # Create the marker only if another request has not already done so.
    try:
        file_descriptor = os.open(
            request_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o664,
        )
        os.close(file_descriptor)
    except FileExistsError:
        # Another request is already waiting for the same study.
        pass

    return False
