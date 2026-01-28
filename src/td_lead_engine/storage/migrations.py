"""Simple migration system for SQLite."""

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_applied_migrations(conn: sqlite3.Connection) -> set:
    """Get list of already-applied migrations."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}


def run_migrations(db_path: str):
    """Run all pending migrations."""
    conn = sqlite3.connect(db_path)
    applied = get_applied_migrations(conn)

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    applied_count = 0
    for migration_file in migration_files:
        version = migration_file.stem
        if version not in applied:
            print(f"Applying migration: {version}")
            sql = migration_file.read_text()
            # Execute each statement separately to handle ALTER TABLE
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(statement)
                    except sqlite3.OperationalError as e:
                        # Skip "duplicate column" errors from re-running ALTER TABLE
                        if "duplicate column" not in str(e).lower():
                            raise
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
            conn.commit()
            applied_count += 1
            print(f"  Applied {version}")

    conn.close()
    return applied_count
