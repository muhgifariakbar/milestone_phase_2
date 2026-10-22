"""Adapts a psycopg connection to the find()/find_one() interface that
src/repository.py and tests/fakes.py already speak, so repository.py stays
completely backend-agnostic (approved by the instructor to run against
Postgres instead of MongoDB; the env var names MONGODB_URI/MONGODB_DATABASE
are kept as-is because compose.yaml already bakes them in and is not ours
to edit).
"""

from urllib.parse import urlsplit, urlunsplit


def resolve_dsn(uri: str, database: str | None) -> str:
    """Appends MONGODB_DATABASE as the Postgres dbname only if MONGODB_URI
    doesn't already name one."""
    if not database:
        return uri
    parsed = urlsplit(uri)
    if parsed.path and parsed.path != "/":
        return uri
    return urlunsplit(parsed._replace(path=f"/{database}"))


class PostgresCollection:
    """Read-only, single-table equality-query adapter."""

    def __init__(self, connection, table: str):
        self.connection = connection
        self.table = table

    def _rows(self, query: dict) -> list[dict]:
        keys = list(query.keys())
        clauses = " AND ".join(f"{key} = %s" for key in keys)
        sql = f"SELECT * FROM {self.table}"  # noqa: S608 (table name is our own constant, not user input)
        if clauses:
            sql += f" WHERE {clauses}"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, [query[key] for key in keys])
            columns = [column.name for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def find(self, query: dict, projection: dict | None = None):
        return iter(self._rows(query))

    def find_one(self, query: dict, projection: dict | None = None):
        rows = self._rows(query)
        return rows[0] if rows else None
