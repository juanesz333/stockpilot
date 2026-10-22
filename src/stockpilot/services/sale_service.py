from collections import defaultdict
from decimal import Decimal

from psycopg import Connection

from stockpilot.services.inventory_service import InventoryError, register_movement


class SaleError(InventoryError):
    """Se rompió una regla de negocio de las ventas.

    Hereda de InventoryError para que la interfaz pueda atrapar ambos
    errores con un solo except.
    """


def create_sale(
    conn: Connection,
    items: list[tuple[str, int]],
    customer_id: int | None = None,
) -> tuple[int, Decimal]:
    """Registra una venta completa y devuelve (id de la venta, total).

    items es una lista de (sku, cantidad). Todo se guarda en una sola
    transacción: si algo falla, no queda nada guardado.
    """
    # 1. Validaciones que no necesitan la base de datos
    if not items:
        raise SaleError("La venta debe tener al menos un producto")

    merged: dict[str, int] = defaultdict(int)
    for sku, quantity in items:
        if quantity <= 0:
            raise SaleError(f"Cantidad no válida para {sku}: {quantity}")
        merged[sku] += quantity  # si un SKU se repite, se suman las cantidades

    # 2. Todo lo que sigue es una sola transacción
    with conn.transaction():
        if customer_id is not None:
            exists = conn.execute(
                "SELECT 1 FROM customers WHERE id = %s", (customer_id,)
            ).fetchone()
            if exists is None:
                raise SaleError(f"No existe el cliente {customer_id}")

        sale_id = conn.execute(
            "INSERT INTO sales (customer_id) VALUES (%s) RETURNING id",
            (customer_id,),
        ).fetchone()[0]

        total = Decimal("0")
        for sku in sorted(merged):  # orden fijo: evita bloqueos cruzados
            quantity = merged[sku]

            # Descuenta el stock aplicando las reglas del inventario
            register_movement(
                conn, sku, "OUT", quantity, f"Venta #{sale_id}", sale_id=sale_id
            )

            # El precio se copia en este momento y queda guardado
            product_id, price = conn.execute(
                "SELECT id, price FROM products WHERE sku = %s", (sku,)
            ).fetchone()
            conn.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s)",
                (sale_id, product_id, quantity, price),
            )
            total += price * quantity

        conn.execute("UPDATE sales SET total = %s WHERE id = %s", (total, sale_id))

    return sale_id, total