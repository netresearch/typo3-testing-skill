# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Netresearch DTT GmbH
"""Small SQLite evidence fixture, not a TYPO3 implementation or model."""

import sqlite3
import sys
import time
from contextlib import closing
from pathlib import Path


def initialize(database):
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            "CREATE TABLE versions (seq INTEGER PRIMARY KEY, request TEXT UNIQUE);"
            "CREATE TABLE audit (request TEXT PRIMARY KEY);"
        )


def save(database, request, atomic=False, checkpoint=lambda: None):
    with closing(sqlite3.connect(database, isolation_level=None)) as connection:
        if atomic:
            connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("INSERT INTO versions(request) VALUES (?)", (request,))
            checkpoint()
            connection.execute("INSERT INTO audit VALUES (?)", (request,))
            if atomic:
                connection.commit()
        except Exception:
            if atomic:
                connection.rollback()
            else:
                connection.execute("DELETE FROM versions WHERE request = ?", (request,))
            raise


def snapshot(database):
    with closing(sqlite3.connect(database)) as connection:
        versions = [
            row[0]
            for row in connection.execute("SELECT request FROM versions ORDER BY seq")
        ]
        audit = {row[0] for row in connection.execute("SELECT request FROM audit")}
        return versions, audit


if __name__ == "__main__":
    database, marker, mode = sys.argv[1:]

    def ready():
        temporary = Path(marker).with_suffix(".tmp")
        temporary.write_text("version-written", encoding="utf-8")
        temporary.replace(marker)
        while True:
            time.sleep(0.01)

    save(database, "A", atomic=mode == "atomic", checkpoint=ready)
