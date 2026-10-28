#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Netresearch DTT GmbH
"""Offline evidence controls; no model calls or TYPO3 conformance claim.

Run with python3 tests/test_crash_evidence.py. CI's tests/*.py glob includes it.
"""

import importlib.util
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "audited_writer.py"
SPEC = importlib.util.spec_from_file_location("audited_writer", FIXTURE)
assert SPEC is not None and SPEC.loader is not None
writer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(writer)


class CrashEvidenceTest(unittest.TestCase):
    def database(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database = Path(directory.name) / "audit.sqlite"
        writer.initialize(database)
        return database

    def kill_after_write(self, database, atomic):
        marker = database.with_suffix(".ready")
        with subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(FIXTURE),
                str(database),
                str(marker),
                "atomic" if atomic else "legacy",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            try:
                deadline = time.monotonic() + 5
                while not marker.exists():
                    self.assertIsNone(
                        process.poll(), "worker failed before the write boundary"
                    )
                    self.assertLess(
                        time.monotonic(), deadline, "write barrier timed out"
                    )
                    time.sleep(0.01)
                self.assertEqual(marker.read_text(encoding="utf-8"), "version-written")
                self.assertIsNone(process.poll(), "worker exited before termination")
                process.kill()
                process.wait(timeout=5)
                if os.name == "posix":
                    self.assertEqual(process.returncode, -signal.SIGKILL)
                else:
                    self.assertNotEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)

    def test_handled_exception_compensation_passes_without_crash_safety(self):
        database = self.database()

        def interrupted():
            raise RuntimeError("audit interrupted")

        with self.assertRaisesRegex(RuntimeError, "audit interrupted"):
            writer.save(database, "A", checkpoint=interrupted)
        self.assertEqual(writer.snapshot(database), ([], set()))

    def test_legacy_crash_leaves_history_gap_behind_audited_current_version(self):
        database = self.database()
        self.kill_after_write(database, atomic=False)
        writer.save(database, "B", atomic=True)
        versions, audit = writer.snapshot(database)
        self.assertEqual(versions[-1], "B")
        self.assertIn("B", audit)
        self.assertEqual(set(versions) - audit, {"A"})

    def test_real_transaction_prevents_gap_at_the_same_crash_boundary(self):
        database = self.database()
        self.kill_after_write(database, atomic=True)
        writer.save(database, "B", atomic=True)
        self.assertEqual(writer.snapshot(database), (["B"], {"B"}))


if __name__ == "__main__":
    unittest.main()
