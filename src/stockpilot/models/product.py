#es para representar un producto como un objeto 
from dataclasses import dataclass
from decimal import Decimal

#crea solo el constructor y la comparación
@dataclass
#los campos tienen el mismo nombre y orden que las columnas de la tabla
class Product:
    id: int
    category_id: int
    sku: str
    name: str
    price: Decimal
    stock: int
    min_stock: int
    active: bool