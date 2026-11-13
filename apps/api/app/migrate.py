from pathlib import Path

from app.database import connect


def migrate() -> None:
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    with connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(1245057102)")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (filename text PRIMARY KEY)"
        )
        applied = {
            row["filename"] for row in connection.execute("SELECT filename FROM schema_migrations")
        }
        for migration in sorted(migrations.glob("[0-9][0-9][0-9]_*.sql")):
            if migration.name not in applied:
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (migration.name,)
                )


if __name__ == "__main__":
    migrate()
