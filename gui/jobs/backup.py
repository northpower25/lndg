"""Backup job – creates settings and database backups.

Usage::

    from gui.jobs.backup import run_backup

    log = run_backup(backup_type="settings", actor="manual")
    log = run_backup(backup_type="database", actor="policy:daily-backup")

Backup files are stored in the ``BACKUP_DIR`` directory (default:
``/tmp/lndg_backups/``).  The path can be overridden via
``settings.BACKUP_DIR``.

Security:
    Files are created with mode ``0o600`` so that only the process owner
    can read them (R-SEC-2).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Literal

from django.utils import timezone

logger = logging.getLogger(__name__)

BackupType = Literal["settings", "database"]


def _get_backup_dir() -> Path:
    try:
        from lndg import settings as _s
        backup_dir = Path(getattr(_s, "BACKUP_DIR", "/tmp/lndg_backups"))
    except Exception:
        backup_dir = Path("/tmp/lndg_backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup_settings() -> Path:
    """Write current LNDg settings to a JSON file and return the path."""
    from lndg import settings as _s

    safe_keys = [
        "LND_RPC_SERVER",
        "LND_MACAROON_PATH",
        "LND_TLS_PATH",
        "LND_MAX_MESSAGE",
        "LOGIN_REQUIRED",
        "ALLOWED_HOSTS",
        "DEBUG",
        "TIME_ZONE",
        "LANGUAGE_CODE",
    ]
    data: dict = {}
    for key in safe_keys:
        value = getattr(_s, key, None)
        data[key] = value

    backup_dir = _get_backup_dir()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = backup_dir / f"settings_{timestamp_str}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    os.chmod(out_path, 0o600)
    return out_path


def _backup_database() -> Path:
    """Create a SQLite database dump and return the path to the dump file.

    For non-SQLite databases a pg_dump / mysqldump style approach would be
    needed; this implementation covers the default SQLite setup.
    """
    from django.db import connection

    backup_dir = _get_backup_dir()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = backup_dir / f"db_dump_{timestamp_str}.sql"

    db_settings = connection.settings_dict
    db_engine = db_settings.get("ENGINE", "")

    if "sqlite3" in db_engine:
        db_path = db_settings.get("NAME", "")
        if db_path and Path(db_path).exists():
            result = subprocess.run(
                ["sqlite3", str(db_path), ".dump"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"sqlite3 dump failed: {result.stderr[:500]}")
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(result.stdout)
        else:
            # In-memory or missing DB – write empty dump
            out_path.write_text("-- empty --\n")
    else:
        # Generic fallback: Django's dumpdata
        result = subprocess.run(
            ["python", "manage.py", "dumpdata", "--indent=2"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dumpdata failed: {result.stderr[:500]}")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(result.stdout)

    os.chmod(out_path, 0o600)
    return out_path


def run_backup(
    *,
    backup_type: BackupType = "settings",
    actor: str = "manual",
) -> "BackupLog":  # type: ignore[name-defined]  # noqa: F821
    """Run a backup of the given type and persist a :class:`BackupLog` record.

    Args:
        backup_type: ``"settings"`` (JSON export) or ``"database"`` (SQL dump).
        actor:       Who/what triggered the backup (``"manual"``,
                     ``"policy:daily-backup"``, etc.).

    Returns:
        The saved :class:`~gui.models.BackupLog` instance.

    Raises:
        Exception: If the backup file cannot be created.  A ``BackupLog``
                   record with ``status="failed"`` is saved before re-raising.
    """
    from gui.models import BackupLog

    log = BackupLog(
        backup_type=backup_type,
        actor=actor,
        created_at=timezone.now(),
    )
    try:
        if backup_type == "settings":
            out_path = _backup_settings()
        else:
            out_path = _backup_database()

        log.file_path = str(out_path)
        log.file_size_bytes = out_path.stat().st_size
        log.checksum = _sha256(out_path)
        log.status = BackupLog.STATUS_OK
    except Exception as exc:
        log.status = BackupLog.STATUS_FAILED
        log.error_message = str(exc)[:500]
        log.save()
        logger.error("Backup of type '%s' failed: %s", backup_type, exc)
        raise

    log.save()
    logger.info("Backup '%s' created at %s (%d bytes)", backup_type, log.file_path, log.file_size_bytes)
    return log
