import psycopg

from stockpilot.config import load_database_config


def get_connection() -> psycopg.Connection:
    cfg = load_database_config()
    return psycopg.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.name,
        user=cfg.user,
        password=cfg.password,
    )