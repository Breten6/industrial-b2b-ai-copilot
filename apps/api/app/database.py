import os

import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "copilot"),
        user=os.getenv("POSTGRES_USER", "copilot"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connect_timeout=3,
        options="-c statement_timeout=5000",
        row_factory=dict_row,
    )
