from stockpilot.database.connection import get_connection


def test_connection_works():
    with get_connection() as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1


def test_schema_has_six_tables():
    with get_connection() as conn:
        count = conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ).fetchone()[0]
    assert count == 6