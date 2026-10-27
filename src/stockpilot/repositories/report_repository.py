from dataclasses import dataclass

from psycopg import Connection


@dataclass(frozen=True)
class Report:
    key: str    # nombre corto que usa el código, ej: "low_stock"
    title: str  # nombre que ve la persona en la lista
    sql: str    # la consulta


REPORTS = [
    Report(
        "sales_by_day",
        "Ventas por día",
        """
        SELECT s.sale_date::date AS dia,
               COUNT(*) AS ventas,
               SUM(s.total) AS total_vendido
        FROM sales s
        GROUP BY s.sale_date::date
        ORDER BY dia DESC
        """,
    ),
    Report(
        "top_products",
        "Productos más vendidos",
        """
        SELECT p.sku,
               p.name AS producto,
               SUM(si.quantity) AS unidades,
               SUM(si.quantity * si.unit_price) AS ingresos
        FROM sale_items si
        JOIN products p ON p.id = si.product_id
        GROUP BY p.id, p.sku, p.name
        ORDER BY unidades DESC, p.sku
        LIMIT 10
        """,
    ),
    Report(
        "inventory_value",
        "Valor del inventario por categoría",
        """
        SELECT c.name AS categoria,
               SUM(p.stock) AS unidades,
               SUM(p.stock * p.price) AS valor
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE p.active
        GROUP BY c.name
        ORDER BY valor DESC
        """,
    ),
    Report(
        "low_stock",
        "Productos con stock bajo",
        """
        SELECT sku,
               name AS producto,
               stock,
               min_stock AS stock_minimo,
               min_stock - stock AS faltan
        FROM products
        WHERE active AND stock < min_stock
        ORDER BY faltan DESC, sku
        """,
    ),
    Report(
        "sales_by_customer",
        "Ventas por cliente",
        """
        SELECT COALESCE(c.name, 'Sin cliente') AS cliente,
               COUNT(s.id) AS ventas,
               SUM(s.total) AS total
        FROM sales s
        LEFT JOIN customers c ON c.id = s.customer_id
        GROUP BY c.name
        ORDER BY total DESC
        """,
    ),
]

REPORTS_BY_KEY = {report.key: report for report in REPORTS}


def run_report(conn: Connection, key: str) -> tuple[list[str], list[tuple]]:
    """Ejecuta un reporte y devuelve (nombres de columnas, filas)."""
    report = REPORTS_BY_KEY.get(key)
    if report is None:
        raise ValueError(f"Reporte desconocido: {key}")
    cur = conn.execute(report.sql)
    columns = [col.name for col in cur.description]
    return columns, cur.fetchall()