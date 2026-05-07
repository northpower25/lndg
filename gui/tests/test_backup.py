"""Tests for BackupLog model and the backup job."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from gui.models import BackupLog


class BackupLogModelTests(TestCase):
    def test_backup_log_defaults(self):
        log = BackupLog.objects.create(
            backup_type=BackupLog.TYPE_SETTINGS,
            actor="manual",
        )
        self.assertEqual(log.status, BackupLog.STATUS_OK)
        self.assertEqual(log.file_size_bytes, 0)
        self.assertEqual(log.checksum, "")
        self.assertEqual(log.actor, "manual")

    def test_backup_log_type_choices(self):
        self.assertEqual(BackupLog.TYPE_SETTINGS, "settings")
        self.assertEqual(BackupLog.TYPE_DATABASE, "database")


class BackupJobTests(TestCase):
    def test_settings_backup_creates_log_record(self):
        """run_backup('settings') should create a BackupLog with status=ok."""
        from gui.jobs.backup import run_backup

        log = run_backup(backup_type="settings", actor="test")

        self.assertIsNotNone(log.pk)
        self.assertEqual(log.backup_type, "settings")
        self.assertEqual(log.status, BackupLog.STATUS_OK)
        self.assertGreater(log.file_size_bytes, 0)
        self.assertNotEqual(log.checksum, "")
        # Cleanup
        Path(log.file_path).unlink(missing_ok=True)

    def test_backup_creates_file_with_restricted_permissions(self):
        """Backup files must be created with mode 0o600 (R-SEC-2)."""
        from gui.jobs.backup import run_backup

        log = run_backup(backup_type="settings", actor="test")
        path = Path(log.file_path)
        mode = oct(path.stat().st_mode & 0o777)
        self.assertEqual(mode, "0o600")
        path.unlink(missing_ok=True)

    def test_failed_backup_creates_failed_log_record(self):
        """If backup fails, a BackupLog with status=failed is saved."""
        from gui.jobs.backup import run_backup

        with patch("gui.jobs.backup._backup_settings", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                run_backup(backup_type="settings", actor="test")

        log = BackupLog.objects.filter(status=BackupLog.STATUS_FAILED).first()
        self.assertIsNotNone(log)
        self.assertIn("disk full", log.error_message)
