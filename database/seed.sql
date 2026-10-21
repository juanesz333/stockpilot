--Datos de prueba 
TRUNCATE inventory_movements, sale_items, sales, customers, products, categories
    RESTART IDENTITY CASCADE;

INSERT INTO categories (name, description) VALUES
('bebidas', 'agua, gaseosas y jugos'),
('Snacks', 'Papas, galletas y dulces'),
('Aseo', 'Productos de limpieza y cuidado personal'),
('Papeleria', 'Cuadernos, laíceros y útiles');

INSERT INTO products (category_id, sku, name, price, stock, min_stock)
SELECT c.id, v.sku, v.name, v.price, 0, v.min_stock
FROM (VALUES
    ('bebidas',   'BEB-001', 'Agua en botella 600 ml',  2000, 20),
    ('bebidas',   'BEB-002', 'Gaseosa 1.5 L',           6500, 12),
    ('bebidas',   'BEB-003', 'Jugo de naranja 1 L',     5500, 10),
    ('Snacks',    'SNK-001', 'Papas fritas',            3000, 15),
    ('Snacks',    'SNK-002', 'Galletas de vainilla',    2500, 15),
    ('Snacks',    'SNK-003', 'Chocolatina',             2000, 20),
    ('Aseo',      'ASE-001', 'Jabón de baño',           3500, 10),
    ('Aseo',      'ASE-002', 'Detergente 1 kg',        12000,  5),
    ('Aseo',      'ASE-003', 'Papel higiénico x4',      8000,  8),
    ('Papeleria', 'PAP-001', 'Cuaderno 100 hojas',      6000, 10),
    ('Papeleria', 'PAP-002', 'Lapicero azul',           1500, 25),
    ('Papeleria', 'PAP-003', 'Resaltador',              3500,  8)
) AS v(cat, sku, name, price, min_stock)
JOIN categories c ON c.name = v.cat;

INSERT INTO customers (name, email) VALUES
    ('Ana Torres', 'ana.torres@example.com'),
    ('Carlos Gómez', 'carlos.gomez@example.com'),
    ('Laura Martínez', 'laura.martinez@example.com');

-- Inventario inicial, registrado como movimientos de entrada
INSERT INTO inventory_movements (product_id, movement_type, quantity, reason)
SELECT p.id, 'IN', v.qty, 'Inventario inicial'
FROM (VALUES
    ('BEB-001', 60), ('BEB-002', 30), ('BEB-003', 20),
    ('SNK-001', 40), ('SNK-002', 35), ('SNK-003', 50),
    ('ASE-001', 25), ('ASE-002',  8), ('ASE-003', 20),
    ('PAP-001', 30), ('PAP-002', 80), ('PAP-003', 15)
) AS v(sku, qty)
JOIN products p ON p.sku = v.sku;

-- Ventas (una sin cliente)
INSERT INTO sales (customer_id, sale_date)
SELECT c.id, v.sale_date::timestamptz
FROM (VALUES
    ('ana.torres@example.com',     '2026-10-05 10:15:00-05'),
    (NULL,                         '2026-10-06 15:40:00-05'),
    ('carlos.gomez@example.com',   '2026-10-08 09:05:00-05'),
    ('laura.martinez@example.com', '2026-10-12 17:30:00-05'),
    ('ana.torres@example.com',     '2026-10-15 11:20:00-05')
) AS v(email, sale_date)
LEFT JOIN customers c ON c.email = v.email
ORDER BY v.sale_date;

-- Detalle de cada venta; el precio se copia del producto
INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
SELECT v.sale_id, p.id, v.qty, p.price
FROM (VALUES
    (1, 'BEB-002',  2), (1, 'SNK-001', 3), (1, 'SNK-003',  5),
    (2, 'ASE-002',  4), (2, 'ASE-003', 2), (2, 'ASE-001',  3),
    (3, 'PAP-001',  5), (3, 'PAP-002', 20), (3, 'PAP-003', 4),
    (4, 'BEB-001', 12), (4, 'BEB-003', 6), (4, 'SNK-002',  8),
    (5, 'ASE-002',  2), (5, 'BEB-002', 3), (5, 'PAP-002', 10)
) AS v(sale_id, sku, qty)
JOIN products p ON p.sku = v.sku;

-- Total de cada venta
UPDATE sales s
SET total = (SELECT SUM(si.quantity * si.unit_price)
             FROM sale_items si WHERE si.sale_id = s.id);

-- Salidas de inventario generadas por las ventas
INSERT INTO inventory_movements
    (product_id, sale_id, movement_type, quantity, reason, movement_date)
SELECT si.product_id, si.sale_id, 'OUT', -si.quantity, 'Venta', s.sale_date
FROM sale_items si
JOIN sales s ON s.id = si.sale_id;

-- El stock actual es la suma de los movimientos
UPDATE products p
SET stock = COALESCE((SELECT SUM(m.quantity)
                      FROM inventory_movements m
                      WHERE m.product_id = p.id), 0);