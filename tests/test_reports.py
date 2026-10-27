from decimal import Decimal

import pytest

from stockpilot.repositories import product_repository as repo
from stockpilot.repositories.report_repository import REPORTS, run_report
from stockpilot.services.inventory_service import register_movement
from stockpilot.services.sale_service import create_sale

EXPECTED_COLUMNS = {
    "sales_by_day": ["dia", "ventas", "total_vendido"],
    "top_products": ["sku", "producto", "unidades", "ingresos"],
    "inventory_value": ["categoria", "unidades", "valor"],
    "low_stock": ["sku", "producto", "stock", "stock_minimo", "faltan"],
    "sales_by_customer": ["cliente", "ventas", "total"],
}


@pytest.mark.parametrize("report", REPORTS, ids=lambda r: r.key)
def test_every_report_runs(conn, report):
    columns, rows = run_report(conn, report.key)
    assert columns == EXPECTED_COLUMNS[report.key]
    assert isinstance(rows, list)


def test_unknown_report_is_rejected(conn):
    with pytest.raises(ValueError):
        run_report(conn, "no_existe")


def test_low_stock_report_includes_new_product(conn, category_id):
    # Un producto nuevo tiene stock 0, así que con mínimo 5 está en stock bajo
    repo.create(conn, category_id, "TST-R1", "Producto de reporte", Decimal("1000"), 5)
    _, rows = run_report(conn, "low_stock")
    assert "TST-R1" in [row[0] for row in rows]


def test_sale_appears_in_sales_by_customer(conn, category_id):
    repo.create(conn, category_id, "TST-R2", "Producto de venta", Decimal("1000"))
    register_movement(conn, "TST-R2", "IN", 10)
    _, sale_total = create_sale(conn, [("TST-R2", 2)])  # venta sin cliente

    _, rows = run_report(conn, "sales_by_customer")
    totals = {row[0]: row[2] for row in rows}
    assert totals["Sin cliente"] >= sale_total