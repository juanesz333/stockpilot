from psycopg import Connection


def list_customers(conn: Connection) -> list[tuple[int, str]]:
    """Devuelve (id, nombre) de todos los clientes, ordenados por nombre."""
    return conn.execute("SELECT id, name FROM customers ORDER BY name").fetchall()