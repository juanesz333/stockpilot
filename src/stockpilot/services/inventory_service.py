#este archivo decide qué operaciones están permitidas 
from sre_constants import IN

from psycopg import Connection

#MOVEMENT_TYPES: lista los tres tipos permitidos: IN(entrada), OUT(salida) y 
# ADJUST(ajuste). Son los mismos que acepta la resticción CHECK de la tabla 
# inventory_movements.
MOVEMENT_TYPES = ("IN", "OUT", "ADJUST")

#InvetoryError: excepción que se lanza cuando se rompe una regla de negocio del inventario.
class InventoryError(Exception):
    """Se rompió una regla de negocio del inventario."""


def register_movement(
    conn: Connection,
    sku: str,
    movement_type: str,
    quantity: int,
    reason: str | None = None,
    sale_id: int | None = None,
) -> int:
    """Registra una entrada, salida o ajuste y devuelve el stock resultante.

    IN y OUT reciben la cantidad en positivo; ADJUST recibe la diferencia con signo.
    El movimiento y el cambio de stock se guardan juntos o no se guarda nada.
    """
    # 1. Validaciones que no necesitan consultar la base de datos
    if movement_type not in MOVEMENT_TYPES:
        raise InventoryError(f"Tipo de movimiento no válido: {movement_type}")

    if movement_type == "ADJUST":
        if quantity == 0:
            raise InventoryError("El ajuste no puede ser 0")
        delta = quantity
    else:
        if quantity <= 0:
            raise InventoryError("La cantidad debe ser mayor que cero")
        delta = quantity if movement_type == "IN" else -quantity

    # 2. Todo lo que sigue es una sola transacción
    with conn.transaction():
        row = conn.execute(
            "SELECT id, stock, active FROM products WHERE sku = %s FOR UPDATE",
            (sku,),
        ).fetchone()
        if row is None:
            raise InventoryError(f"No existe el producto {sku}")
        
        #El cálculo de delta convierte la operación en un número con signo:

        # IN de 10 → delta = +10
        # OUT de 4 → delta = -4
        # ADJUST de -2 → delta = -2
        product_id, stock, active = row
        if not active:
            raise InventoryError(f"El producto {sku} está desactivado")
        if stock + delta < 0:
            raise InventoryError(
                f"Stock insuficiente para {sku}: hay {stock} y se piden {-delta}"
            )

        conn.execute(
            "INSERT INTO inventory_movements "
            "(product_id, sale_id, movement_type, quantity, reason) "
            "VALUES (%s, %s, %s, %s, %s)",
            (product_id, sale_id, movement_type, delta, reason),
        )
        conn.execute(
            "UPDATE products SET stock = stock + %s WHERE id = %s",
            (delta, product_id),
        )
        return stock + delta