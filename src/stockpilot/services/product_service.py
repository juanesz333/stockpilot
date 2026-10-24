from decimal import Decimal

import psycopg
from psycopg import Connection

from stockpilot.models.product import Product
from stockpilot.repositories import product_repository as repo


class ProductError(Exception):
    """Se rompió una regla de negocio de los productos."""


def create_product(
    conn: Connection,
    category_id: int,
    sku: str,
    name: str,
    price: Decimal,
    min_stock: int = 0,
) -> Product:
    """Valida y crea un producto nuevo con stock 0."""
    sku = sku.strip().upper()  # " bev-004 " se guarda como "BEV-004"
    name = name.strip()

    if not sku:
        raise ProductError("El SKU es obligatorio")
    if not name:
        raise ProductError("El nombre es obligatorio")
    if price < 0:
        raise ProductError("El precio no puede ser negativo")
    if min_stock < 0:
        raise ProductError("El stock mínimo no puede ser negativo")

    try:
        with conn.transaction():
            return repo.create(conn, category_id, sku, name, price, min_stock)
    except psycopg.errors.UniqueViolation as exc:
        raise ProductError(f"Ya existe un producto con el SKU {sku}") from exc