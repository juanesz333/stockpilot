from psycopg import Connection


def list_categories(conn: Connection) -> list[tuple[int, str]]:
    """Devuelve (id, nombre) de todas las categorías, ordenadas por nombre."""
    return conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()