-- 1. Ventas por día
SELECT sale_date::date AS dia,
       COUNT(*) AS ventas,
       SUM(total) AS total_vendido
FROM sales
GROUP BY sale_date::date
ORDER BY dia;

-- 2. Productos más vendidos
SELECT p.sku, p.name,
       SUM(si.quantity) AS unidades,
       SUM(si.quantity * si.unit_price) AS ingresos
FROM sale_items si
JOIN products p ON p.id = si.product_id
GROUP BY p.id, p.sku, p.name
ORDER BY unidades DESC
LIMIT 5;

-- 3. Valor del inventario por categoría (a precio de venta)
SELECT c.name AS categoria,
       SUM(p.stock) AS unidades,
       SUM(p.stock * p.price) AS valor
FROM products p
JOIN categories c ON c.id = p.category_id
GROUP BY c.name
ORDER BY valor DESC;

-- 4. Productos con stock bajo
SELECT sku, name, stock, min_stock
FROM products
WHERE stock < min_stock
ORDER BY sku;

-- 5. Ventas por cliente (incluye las ventas sin cliente)
SELECT COALESCE(c.name, 'Sin cliente') AS cliente,
       COUNT(s.id) AS ventas,
       SUM(s.total) AS total
FROM sales s
LEFT JOIN customers c ON c.id = s.customer_id
GROUP BY c.name
ORDER BY total DESC;