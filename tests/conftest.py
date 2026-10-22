import pytest

from stockpilot.database.connection import get_connection


@pytest.fixture
def conn():
    """Conexión de prueba: todo lo que hagas se deshace al terminar."""
    connection = get_connection()
    try:
        yield connection          # aquí se ejecuta la prueba
    finally:
        connection.rollback()     # se deshace todo lo que hizo la prueba
        connection.close()


@pytest.fixture
def category_id(conn):
    """Un id de categoría existente, para crear productos de prueba."""
    return conn.execute("SELECT id FROM categories ORDER BY id LIMIT 1").fetchone()[0]