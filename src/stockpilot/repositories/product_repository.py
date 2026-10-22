#concentra todo el SQL de la tabla products en un solo lugar

from decimal import Decimal

from psycopg import Connection
from psycopg.rows import class_row

from stockpilot.models.product import Product

# Las columnas que se piden siempre, en el mismo orden que los campos de Product
_COLUMNS = "id, category_id, sku, name, price, stock, min_stock, active"


def list_products(conn: Connection, only_active: bool = True) -> list[Product]:
    """Devuelve todos los productos, por defecto solo los activos."""
    query = f"SELECT {_COLUMNS} FROM products"
    if only_active:
        query += " WHERE active"
    query += " ORDER BY sku"
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(query).fetchall()


##%s con los valores aparte: psycopg manda el texto y los valores por separado 
# a PostgreSQL, que hace el escape de los valores y evita inyecciones SQL
def get_by_sku(conn: Connection, sku: str) -> Product | None:
    """Busca un producto por su SKU. Devuelve None si no existe."""
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(
            f"SELECT {_COLUMNS} FROM products WHERE sku = %s", (sku,)
        ).fetchone()


#class_row(Product) hace que cada fila devuelta por fetchone() o fetchall() sea un objeto
# ILIKE:es LIKE sin distinguir mayúsculas. Los % alrededor del texto significan “contiene”.
def search(conn: Connection, text: str) -> list[Product]:
    """Busca productos activos cuyo nombre o SKU contenga el texto."""
    pattern = f"%{text}%"
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(
            f"SELECT {_COLUMNS} FROM products "
            "WHERE active AND (name ILIKE %s OR sku ILIKE %s) ORDER BY sku",
            (pattern, pattern),
        ).fetchall()


def list_low_stock(conn: Connection) -> list[Product]:
    """Productos activos con menos stock del mínimo definido."""
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(
            f"SELECT {_COLUMNS} FROM products "
            "WHERE active AND stock < min_stock ORDER BY sku"
        ).fetchall()


def create(
    conn: Connection,
    category_id: int,
    sku: str,
    name: str,
    price: Decimal,
    min_stock: int = 0,
) -> Product:
    """Crea un producto nuevo (con stock 0) y lo devuelve."""
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(
            #RETURNING: el INSERT devuelve la fila recién creada, con el id 
            # que generó la base, sin necesidad de otra consulta.
            "INSERT INTO products (category_id, sku, name, price, min_stock) "
            f"VALUES (%s, %s, %s, %s, %s) RETURNING {_COLUMNS}",
            (category_id, sku, name, price, min_stock),
        ).fetchone()


def update_price(conn: Connection, sku: str, price: Decimal) -> bool:
    """Cambia el precio. Devuelve True si el producto existía."""
    cur = conn.execute("UPDATE products SET price = %s WHERE sku = %s", (price, sku))
    return cur.rowcount > 0

#set_active en vez de DELETE: desactivar conserva el historial. 
# Si borraras un producto con ventas, la base lo impediría por la clave foránea, 
# y además perderías información.
def set_active(conn: Connection, sku: str, active: bool) -> bool:
    """Activa o desactiva un producto (en vez de borrarlo)."""
    cur = conn.execute("UPDATE products SET active = %s WHERE sku = %s", (active, sku))
    return cur.rowcount > 0