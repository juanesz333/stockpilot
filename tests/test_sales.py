#Es para verificar que la venta se haya registrado correctamente y 
# que el total sea el esperado.
from decimal import Decimal

import pytest

from stockpilot.repositories import product_repository as repo
from stockpilot.services.inventory_service import InventoryError, register_movement
from stockpilot.services.sale_service import SaleError, create_sale


@pytest.fixture
def products(conn, category_id):
    """Dos productos de prueba con 10 unidades cada uno."""
    repo.create(conn, category_id, "TST-S1", "Producto 1", Decimal("1000"))
    repo.create(conn, category_id, "TST-S2", "Producto 2", Decimal("2500"))
    register_movement(conn, "TST-S1", "IN", 10)
    register_movement(conn, "TST-S2", "IN", 10)


def count(conn, query, params=()):
    return conn.execute(query, params).fetchone()[0]


def test_sale_calculates_total_and_reduces_stock(conn, products):
    sale_id, total = create_sale(conn, [("TST-S1", 2), ("TST-S2", 3)])

    assert total == Decimal("9500")  # 2 x 1000 + 3 x 2500
    assert repo.get_by_sku(conn, "TST-S1").stock == 8
    assert repo.get_by_sku(conn, "TST-S2").stock == 7
    assert count(conn, "SELECT total FROM sales WHERE id = %s", (sale_id,)) == total
    assert count(conn, "SELECT count(*) FROM sale_items WHERE sale_id = %s", (sale_id,)) == 2
    assert count(
        conn,
        "SELECT count(*) FROM inventory_movements "
        "WHERE sale_id = %s AND movement_type = 'OUT'",
        (sale_id,),
    ) == 2


def test_sale_keeps_price_at_sale_time(conn, products):
    sale_id, _ = create_sale(conn, [("TST-S1", 1)])
    repo.update_price(conn, "TST-S1", Decimal("9999"))

    unit_price = count(
        conn, "SELECT unit_price FROM sale_items WHERE sale_id = %s", (sale_id,)
    )
    assert unit_price == Decimal("1000")


def test_failed_sale_saves_nothing(conn, products):
    sales_before = count(conn, "SELECT count(*) FROM sales")

    with pytest.raises(InventoryError):
        # El primer producto alcanza, el segundo no
        create_sale(conn, [("TST-S1", 2), ("TST-S2", 50)])

    assert repo.get_by_sku(conn, "TST-S1").stock == 10
    assert repo.get_by_sku(conn, "TST-S2").stock == 10
    assert count(conn, "SELECT count(*) FROM sales") == sales_before


def test_empty_sale_is_rejected(conn):
    with pytest.raises(SaleError):
        create_sale(conn, [])


def test_repeated_sku_is_merged(conn, products):
    sale_id, total = create_sale(conn, [("TST-S1", 2), ("TST-S1", 3)])

    assert total == Decimal("5000")
    assert repo.get_by_sku(conn, "TST-S1").stock == 5
    assert count(conn, "SELECT count(*) FROM sale_items WHERE sale_id = %s", (sale_id,)) == 1