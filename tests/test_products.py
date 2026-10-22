#Para qué es: Verficiar que el repositorio de productos hace lo que dice.
#Son pruebas de integración: usan la base de datos real, no una simulación.
from decimal import Decimal

import psycopg
import pytest

from stockpilot.repositories import product_repository as repo

#Hace que list_products() devuelva al menos los productos de prueba 
# que se cargan con seed_data.sql
def test_seed_products_are_listed(conn):
    assert len(repo.list_products(conn)) >= 12

#hace que un producto creado se pueda buscar por su SKU y que tenga stock 0
def test_create_and_get_product(conn, category_id):
    created = repo.create(
        conn, category_id, "TST-001", "Producto de prueba", Decimal("1500.00"), 3
    )
    found = repo.get_by_sku(conn, "TST-001")
    assert found.id == created.id
    assert found.stock == 0
    assert found.price == Decimal("1500.00")

#La base rechaza dos productos con el mismo SKU, y psycopg lanza una 
# excepción UniqueViolation.
def test_duplicate_sku_is_rejected(conn, category_id):
    repo.create(conn, category_id, "TST-002", "Uno", Decimal("1000"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.create(conn, category_id, "TST-002", "Dos", Decimal("2000"))

#cuando busco por nombre, devuelve los productos cuyo nombre o SKU contiene el texto, 
#sin distinguir mayúsculas con ILIKE 
def test_search_by_name(conn):
    results = repo.search(conn, "gaseosa")
    assert any(p.sku == "BEB-002" for p in results)

#que un producto desactivado no aparezca en la lista de productos activos
def test_deactivated_product_is_hidden(conn, category_id):
    repo.create(conn, category_id, "TST-003", "Temporal", Decimal("1000"))
    repo.set_active(conn, "TST-003", False)
    assert "TST-003" not in [p.sku for p in repo.list_products(conn)]