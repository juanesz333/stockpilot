#Verifica que register_movement() cumple las reglas. 
from decimal import Decimal

import pytest

from stockpilot.repositories import product_repository as repo
from stockpilot.services.inventory_service import InventoryError, register_movement


@pytest.fixture
def product(conn, category_id):
    """Un producto de prueba con stock 0."""
    return repo.create(
        conn, category_id, "TST-INV", "Producto de inventario", Decimal("1000"), 5
    )


def test_entry_increases_stock(conn, product):
    assert register_movement(conn, "TST-INV", "IN", 10, "Compra") == 10
    assert repo.get_by_sku(conn, "TST-INV").stock == 10


def test_exit_decreases_stock(conn, product):
    register_movement(conn, "TST-INV", "IN", 10)
    assert register_movement(conn, "TST-INV", "OUT", 4) == 6


def test_exit_above_stock_is_rejected(conn, product):
    register_movement(conn, "TST-INV", "IN", 3)
    with pytest.raises(InventoryError):
        register_movement(conn, "TST-INV", "OUT", 5)
    assert repo.get_by_sku(conn, "TST-INV").stock == 3


def test_zero_quantity_is_rejected(conn, product):
    with pytest.raises(InventoryError):
        register_movement(conn, "TST-INV", "IN", 0)


def test_unknown_product_is_rejected(conn):
    with pytest.raises(InventoryError):
        register_movement(conn, "NO-EXISTE", "IN", 1)


def test_history_matches_stock(conn, product):
    register_movement(conn, "TST-INV", "IN", 10)
    register_movement(conn, "TST-INV", "OUT", 3)
    register_movement(conn, "TST-INV", "ADJUST", -2)
    total = conn.execute(
        "SELECT SUM(quantity) FROM inventory_movements WHERE product_id = %s",
        (product.id,),
    ).fetchone()[0]
    assert total == 5
    assert repo.get_by_sku(conn, "TST-INV").stock == 5