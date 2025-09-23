#!/usr/bin/env python3
"""
Database cleanup utility for youtube_library.db

- Converts relative video file paths to absolute paths based on current CWD
- Normalizes path separators (Windows/Unix) via os.path.normpath
- Optionally removes DB rows whose files no longer exist on disk
"""

import argparse
import os
import sqlite3
import sys
from typing import Tuple


def make_absolute_and_normalize(path: str) -> str:
    if not path:
        return path
    if os.path.isabs(path):
        return os.path.normpath(path)
    # Convert to absolute relative to current working directory
    return os.path.normpath(os.path.abspath(path))


def cleanup_database(db_path: str, delete_missing: bool = False) -> Tuple[int, int, int]:
    """
    Returns a tuple: (updated_paths, already_absolute_or_clean, deleted_rows)
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT rowid, id, file_path FROM videos")
    rows = cursor.fetchall()

    updated = 0
    unchanged = 0
    deleted = 0

    for row in rows:
        rowid = row["rowid"]
        file_path = row["file_path"]

        if not file_path:
            unchanged += 1
            continue

        new_path = make_absolute_and_normalize(file_path)

        if delete_missing and new_path and not os.path.exists(new_path):
            cursor.execute("DELETE FROM videos WHERE rowid = ?", (rowid,))
            deleted += 1
            continue

        if new_path != file_path:
            cursor.execute("UPDATE videos SET file_path = ? WHERE rowid = ?", (new_path, rowid))
            updated += 1
        else:
            unchanged += 1

    conn.commit()
    conn.close()

    return updated, unchanged, deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup youtube_library.db paths")
    parser.add_argument("--db", default="youtube_library.db", help="Path to the SQLite DB (default: youtube_library.db)")
    parser.add_argument("--delete-missing", action="store_true", help="Delete rows whose file_path does not exist on disk")
    args = parser.parse_args()

    try:
        updated, unchanged, deleted = cleanup_database(args.db, delete_missing=args.delete_missing)
        print(f"Updated paths: {updated}")
        print(f"Unchanged rows: {unchanged}")
        print(f"Deleted rows (missing files): {deleted}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


