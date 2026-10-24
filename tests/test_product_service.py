from decimal import Decimal

import pytest

from stockpilot.repositories import product_repository as repo
from stockpilot.services.product_service import ProductError, create_product


def test_create_product_normalizes_sku_and_name(conn, category_id):
    product = create_product(
        conn, category_id, "  tst-p1 ", "  Producto nuevo  ", Decimal("1500")
    )
    assert product.sku == "TST-P1"
    assert product.name == "Producto nuevo"
    assert repo.get_by_sku(conn, "TST-P1") is not None


def test_negative_price_is_rejected(conn, category_id):
    with pytest.raises(ProductError):
        create_product(conn, category_id, "TST-P2", "Negativo", Decimal("-1"))


def test_empty_name_is_rejected(conn, category_id):
    with pytest.raises(ProductError):
        create_product(conn, category_id, "TST-P3", "   ", Decimal("1000"))


def test_duplicate_sku_is_rejected_with_clear_message(conn, category_id):
    create_product(conn, category_id, "TST-P4", "Uno", Decimal("1000"))
    with pytest.raises(ProductError, match="TST-P4"):
        create_product(conn, category_id, "tst-p4", "Dos", Decimal("2000"))