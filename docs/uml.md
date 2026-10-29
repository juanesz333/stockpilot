# StockPilot: documentación UML

Diagramas del proyecto, de lo más general a lo más detallado. Se dibujan con [Mermaid](https://mermaid.js.org/), que GitHub muestra directamente.

**Convenciones:** Python usa módulos con funciones en lugar de clases para los servicios y repositorios. Aquí aparecen como clases con el estereotipo `<<module>>`, y sus funciones como métodos. Las clases de Qt llevan `<<PySide6>>`.

## Contenido

1. [Vista de paquetes](#1-vista-de-paquetes)
2. [Modelo de dominio](#2-modelo-de-dominio)
3. [Modelo físico de datos](#3-modelo-físico-de-datos)
4. [Clases: infraestructura y acceso a datos](#4-clases-infraestructura-y-acceso-a-datos)
5. [Clases: servicios y excepciones](#5-clases-servicios-y-excepciones)
6. [Clases: interfaz de usuario](#6-clases-interfaz-de-usuario)
7. [Casos de uso](#7-casos-de-uso)
8. [Diagramas de secuencia](#8-diagramas-de-secuencia)
9. [Diagrama de actividad: registrar un movimiento](#9-diagrama-de-actividad-registrar-un-movimiento)
10. [Diagrama de estados: producto](#10-diagrama-de-estados-producto)
11. [Diagrama de despliegue](#11-diagrama-de-despliegue)

## 1. Vista de paquetes

Muestra qué módulo usa a cuál. La interfaz nunca consulta la base de datos directamente: pasa por servicios y repositorios.

```mermaid
flowchart TB
    subgraph ui["ui/ Interfaz (PySide6)"]
        main["main.py"]
        MW["main_window"]
        PV["products_view"]
        SV["sales_view"]
        RV["reports_view"]
        PD["product_dialog"]
        MD["movement_dialog"]
    end

    subgraph services["services/ Reglas de negocio"]
        PS["product_service"]
        IS["inventory_service"]
        SS["sale_service"]
    end

    subgraph repositories["repositories/ Acceso a datos"]
        PR["product_repository"]
        CR["category_repository"]
        CUR["customer_repository"]
        RR["report_repository"]
    end

    subgraph models["models/"]
        PM["product (Product)"]
    end

    subgraph core["Infraestructura"]
        CONN["database/connection"]
        CFG["config"]
    end

    ENV[".env"]
    DB[("PostgreSQL")]

    main --> MW
    MW --> PV & SV & RV
    PV --> PD & MD
    PV --> PR
    PD --> PS & CR
    MD --> IS
    SV --> SS & PR & CUR
    RV --> RR
    PS --> PR
    SS --> IS
    PS --> PM
    PR --> PM
    PV & SV & RV & PD & MD -.->|"get_connection()"| CONN
    CONN --> CFG
    CFG --> ENV
    PR & CR & CUR & RR --> DB
    IS & SS --> DB
```

Los servicios de inventario y ventas ejecutan sus propias consultas porque deben leer, validar y escribir dentro de una misma transacción, con la fila del producto bloqueada.

## 2. Modelo de dominio

Las entidades del negocio y sus asociaciones, en notación UML de clases. Es un modelo conceptual: las claves foráneas no aparecen como atributos porque las expresan las asociaciones (el modelo físico está en la sección 3).

```mermaid
classDiagram
    direction LR

    class Category {
        +int id
        +str name
        +str description
    }

    class Product {
        +int id
        +str sku
        +str name
        +Decimal price
        +int stock
        +int min_stock
        +bool active
        +datetime created_at
    }

    class Customer {
        +int id
        +str name
        +str email
    }

    class Sale {
        +int id
        +datetime sale_date
        +Decimal total
    }

    class SaleItem {
        +int quantity
        +Decimal unit_price
    }

    class InventoryMovement {
        +int id
        +MovementType movement_type
        +int quantity
        +str reason
        +datetime movement_date
    }

    class MovementType {
        <<enumeration>>
        IN
        OUT
        ADJUST
    }

    Category "1" -- "0..*" Product : clasifica
    Customer "0..1" -- "0..*" Sale : realiza
    Sale "1" *-- "1..*" SaleItem : contiene
    Product "1" -- "0..*" SaleItem : se vende en
    Product "1" -- "0..*" InventoryMovement : tiene historial
    Sale "0..1" -- "0..*" InventoryMovement : origina salidas
    InventoryMovement ..> MovementType : tipo
```

- `SaleItem` es la clase asociativa entre `Sale` y `Product`: una venta incluye varios productos y un producto aparece en varias ventas. No puede haber dos líneas del mismo producto en una venta.
- `SaleItem.unit_price` guarda el precio del momento de la venta.
- El `stock` de un `Product` es la suma de las cantidades de sus `InventoryMovement`: las entradas son positivas y las salidas negativas.
- Una venta puede no tener cliente (`0..1`), y un movimiento puede no venir de una venta (`0..1`), como las entradas y los ajustes.
- La clase `Product` del código (`models/product.py`) no incluye `created_at`: el repositorio no lo lee.

## 3. Modelo físico de datos

Las seis tablas de PostgreSQL, con tipos, claves y restricciones. Mermaid no admite coma dentro del tipo, así que la precisión de `NUMERIC(12,2)` va en el comentario.

```mermaid
erDiagram
    categories ||--o{ products : "clasifica"
    customers |o--o{ sales : "realiza"
    sales ||--|{ sale_items : "contiene"
    products ||--o{ sale_items : "se vende en"
    products ||--o{ inventory_movements : "tiene historial"
    sales |o--o{ inventory_movements : "origina salidas"

    categories {
        integer id PK "identity"
        varchar(100) name UK "NOT NULL"
        text description
    }

    products {
        integer id PK "identity"
        integer category_id FK "NOT NULL"
        varchar(50) sku UK "NOT NULL"
        varchar(150) name "NOT NULL"
        numeric price "NUMERIC(12,2), no negativo"
        integer stock "DEFAULT 0, no negativo"
        integer min_stock "DEFAULT 0, no negativo"
        boolean active "DEFAULT TRUE"
        timestamptz created_at "DEFAULT now()"
    }

    customers {
        integer id PK "identity"
        varchar(150) name "NOT NULL"
        varchar(150) email UK "admite NULL"
    }

    sales {
        integer id PK "identity"
        integer customer_id FK "NULL = sin cliente"
        timestamptz sale_date "DEFAULT now()"
        numeric total "NUMERIC(12,2), DEFAULT 0, no negativo"
    }

    sale_items {
        integer sale_id PK, FK
        integer product_id PK, FK
        integer quantity "mayor que 0"
        numeric unit_price "NUMERIC(12,2), precio al vender"
    }

    inventory_movements {
        integer id PK "identity"
        integer product_id FK "NOT NULL"
        integer sale_id FK "NULL si no viene de una venta"
        varchar(10) movement_type "IN, OUT o ADJUST"
        integer quantity "con signo"
        varchar(200) reason
        timestamptz movement_date "DEFAULT now()"
    }
```

### Relaciones y claves foráneas

| Relación | Cardinalidad | Clave foránea | ¿Obligatoria? |
|---|---|---|---|
| `categories` → `products` | 1 : N | `products.category_id` | Sí |
| `customers` → `sales` | 0..1 : N | `sales.customer_id` | No |
| `sales` → `sale_items` | 1 : N | `sale_items.sale_id` | Sí |
| `products` → `sale_items` | 1 : N | `sale_items.product_id` | Sí |
| `products` → `inventory_movements` | 1 : N | `inventory_movements.product_id` | Sí |
| `sales` → `inventory_movements` | 0..1 : N | `inventory_movements.sale_id` | No |

Ninguna clave foránea usa `ON DELETE CASCADE`: la base no permite borrar un producto o una venta que tengan registros relacionados.

### Restricciones de integridad

| Tabla | Restricción |
|---|---|
| `categories` | `name` único |
| `products` | `sku` único; `price >= 0`; `stock >= 0`; `min_stock >= 0` |
| `customers` | `email` único (admite `NULL`) |
| `sales` | `total >= 0` |
| `sale_items` | `quantity > 0`; `unit_price >= 0`; clave primaria compuesta `(sale_id, product_id)` |
| `inventory_movements` | `movement_type` en (`IN`, `OUT`, `ADJUST`); cantidad positiva en `IN`, negativa en `OUT` y distinta de cero en `ADJUST` |

### Índices

| Índice | Columna | Para qué sirve |
|---|---|---|
| `idx_products_category` | `products.category_id` | Reportes por categoría |
| `idx_sales_date` | `sales.sale_date` | Reporte de ventas por día |
| `idx_sale_items_product` | `sale_items.product_id` | Productos más vendidos |
| `idx_movements_product` | `inventory_movements.product_id` | Historial de un producto |

## 4. Clases: infraestructura y acceso a datos

```mermaid
classDiagram
    direction TB

    class DatabaseConfig {
        <<dataclass>>
        +str host
        +int port
        +str name
        +str user
        +str password
    }

    class ConfigModule {
        <<module>>
        +load_database_config() DatabaseConfig
    }

    class ConnectionModule {
        <<module>>
        +get_connection() Connection
    }

    class Product {
        <<dataclass>>
        +int id
        +int category_id
        +str sku
        +str name
        +Decimal price
        +int stock
        +int min_stock
        +bool active
    }

    class ProductRepository {
        <<module>>
        +list_products(conn, only_active) list~Product~
        +get_by_sku(conn, sku) Product
        +search(conn, text) list~Product~
        +list_low_stock(conn) list~Product~
        +create(conn, category_id, sku, name, price, min_stock) Product
        +update_price(conn, sku, price) bool
        +set_active(conn, sku, active) bool
    }

    class CategoryRepository {
        <<module>>
        +list_categories(conn) list
    }

    class CustomerRepository {
        <<module>>
        +list_customers(conn) list
    }

    class Report {
        <<dataclass>>
        +str key
        +str title
        +str sql
    }

    class ReportRepository {
        <<module>>
        +list REPORTS
        +dict REPORTS_BY_KEY
        +run_report(conn, key) tuple
    }

    ConnectionModule ..> ConfigModule : usa
    ConfigModule ..> DatabaseConfig : crea
    ProductRepository ..> Product : crea y devuelve
    ReportRepository "1" *-- "5" Report : REPORTS
```

- `DatabaseConfig` y `Report` son `dataclass` inmutables (`frozen=True`).
- Todas las funciones de los repositorios reciben una conexión de psycopg y **no hacen `commit`**: quien las llama decide qué operaciones forman una transacción.
- `update_price` y `set_active` existen en la capa de datos, pero la interfaz aún no tiene botones para ellas.

## 5. Clases: servicios y excepciones

```mermaid
classDiagram
    direction LR

    class Exception {
        <<Python>>
    }

    class ProductError {
        <<exception>>
    }

    class InventoryError {
        <<exception>>
    }

    class SaleError {
        <<exception>>
    }

    class ProductService {
        <<module>>
        +create_product(conn, category_id, sku, name, price, min_stock) Product
    }

    class InventoryService {
        <<module>>
        +tuple MOVEMENT_TYPES
        +register_movement(conn, sku, movement_type, quantity, reason, sale_id) int
    }

    class SaleService {
        <<module>>
        +create_sale(conn, items, customer_id) tuple
    }

    class ProductRepository {
        <<module>>
        +create(conn, category_id, sku, name, price, min_stock) Product
    }

    ProductError --|> Exception
    InventoryError --|> Exception
    SaleError --|> InventoryError
    ProductService ..> ProductRepository : usa
    ProductService ..> ProductError : lanza
    InventoryService ..> InventoryError : lanza
    SaleService ..> InventoryService : reutiliza register_movement
    SaleService ..> SaleError : lanza
```

- `SaleError` hereda de `InventoryError`: la interfaz atrapa ambos con un solo `except InventoryError`.
- `create_sale` devuelve una tupla `(sale_id, total)`, y `register_movement` devuelve el stock resultante.
- `register_movement` y `create_sale` abren una transacción (`with conn.transaction()`), y bloquean los productos con `SELECT ... FOR UPDATE`.

## 6. Clases: interfaz de usuario

```mermaid
classDiagram
    direction TB

    class QMainWindow {
        <<PySide6>>
    }
    class QWidget {
        <<PySide6>>
    }
    class QDialog {
        <<PySide6>>
    }

    class Main {
        <<module>>
        +main() int
    }

    class MainWindow {
        +on_tab_changed(index)
    }

    class ProductsView {
        +QLineEdit search_box
        +QPushButton new_button
        +QPushButton movement_button
        +QPushButton refresh_button
        +QTableWidget table
        +QLabel status
        +open_product_dialog()
        +open_movement_dialog()
        +load_products()
    }

    class SalesView {
        +dict cart
        +dict products
        +QComboBox product_combo
        +QSpinBox quantity_input
        +QPushButton add_button
        +QPushButton remove_button
        +QTableWidget table
        +QComboBox customer_combo
        +QLabel total_label
        +QPushButton confirm_button
        +reload_data()
        +add_to_cart()
        +remove_selected()
        +refresh_cart()
        +confirm_sale()
    }

    class ReportsView {
        +QComboBox report_combo
        +QPushButton refresh_button
        +QTableWidget table
        +QLabel status
        +load_report()
    }

    class ProductDialog {
        +QComboBox category_combo
        +QLineEdit sku_input
        +QLineEdit name_input
        +QDoubleSpinBox price_input
        +QSpinBox min_stock_input
        -_load_categories()
        +accept()
    }

    class MovementDialog {
        +str sku
        +QComboBox type_combo
        +QSpinBox quantity_input
        +QLineEdit reason_input
        -_update_range()
        +accept()
    }

    class ProductRepository {
        <<module>>
    }
    class CategoryRepository {
        <<module>>
    }
    class CustomerRepository {
        <<module>>
    }
    class ReportRepository {
        <<module>>
    }
    class ProductService {
        <<module>>
    }
    class InventoryService {
        <<module>>
    }
    class SaleService {
        <<module>>
    }

    Main ..> MainWindow : crea y muestra
    MainWindow --|> QMainWindow
    ProductsView --|> QWidget
    SalesView --|> QWidget
    ReportsView --|> QWidget
    ProductDialog --|> QDialog
    MovementDialog --|> QDialog

    MainWindow *-- ProductsView : products_view
    MainWindow *-- SalesView : sales_view
    MainWindow *-- ReportsView : reports_view
    ProductsView ..> ProductDialog : abre
    ProductsView ..> MovementDialog : abre

    ProductsView ..> ProductRepository
    SalesView ..> ProductRepository
    SalesView ..> CustomerRepository
    SalesView ..> SaleService
    ReportsView ..> ReportRepository
    ProductDialog ..> CategoryRepository
    ProductDialog ..> ProductService
    MovementDialog ..> InventoryService
```

- Los atributos son los widgets que cada pantalla guarda; los métodos son los *slots* conectados a señales (`clicked`, `textChanged`, `currentChanged`).
- `MovementDialog` recibe `sku`, `name` y `stock` al crearse, para mostrar el producto seleccionado.
- `SalesView.cart` es un diccionario `sku → [producto, cantidad]` que vive en memoria hasta confirmar la venta.
- `sales_view.py` define la función auxiliar `money()` y `reports_view.py` la función `format_value()`, ambas a nivel de módulo.
- Ninguna clase de interfaz contiene SQL ni reglas de negocio.

## 7. Casos de uso

```mermaid
flowchart LR
    U(["👤 Usuario<br/>encargado de inventario"])

    subgraph SYS["StockPilot"]
        UC1([Consultar y buscar productos])
        UC2([Crear producto])
        UC3([Registrar entrada, salida o ajuste])
        UC4([Realizar venta])
        UC5([Consultar reportes])
        UC6([Validar stock disponible])
        UC7([Descontar stock y registrar movimiento])
        UC8([Elegir cliente])
    end

    U --- UC1
    U --- UC2
    U --- UC3
    U --- UC4
    U --- UC5
    UC3 -.->|"«include»"| UC6
    UC3 -.->|"«include»"| UC7
    UC4 -.->|"«include»"| UC6
    UC4 -.->|"«include»"| UC7
    UC8 -.->|"«extend»"| UC4
```

Mermaid no tiene diagrama de casos de uso propio, así que este se dibuja con un diagrama de flujo que imita la notación: el actor a la izquierda, los casos de uso dentro del sistema y las relaciones `include` y `extend` con líneas punteadas.

| ID | Caso de uso | Precondición | Flujo principal | Errores y alternativas |
|---|---|---|---|---|
| CU-01 | Consultar y buscar productos | Ninguna | Abrir la pestaña Productos y escribir en la caja de búsqueda | Si la base no responde, se muestra un aviso. Los productos bajo su mínimo salen en rojo |
| CU-02 | Crear producto | Existe al menos una categoría | Pulsar Nuevo producto, completar categoría, SKU, nombre, precio y mínimo, y aceptar | SKU repetido, nombre vacío o precio negativo: aviso y el formulario sigue abierto. El SKU se guarda en mayúsculas y el stock empieza en 0 |
| CU-03 | Registrar entrada, salida o ajuste | Hay un producto seleccionado | Pulsar Registrar movimiento, elegir tipo, cantidad y motivo, y aceptar | Sin selección, cantidad inválida, producto desactivado o stock insuficiente: aviso y no cambia nada |
| CU-04 | Realizar venta | Hay productos con stock | Elegir producto y cantidad, agregar al carrito, opcionalmente elegir cliente y confirmar | Carrito vacío o stock insuficiente: aviso y el carrito se conserva. Si algo falla, no se guarda nada |
| CU-05 | Consultar reportes | Ninguna | Elegir un reporte en la lista; la tabla se actualiza | Si la base no responde, se muestra un aviso |

## 8. Diagramas de secuencia

### 8.1 Crear un producto

```mermaid
sequenceDiagram
    actor U as Usuario
    participant PV as ProductsView
    participant PD as ProductDialog
    participant CR as category_repository
    participant PS as product_service
    participant PR as product_repository
    participant DB as PostgreSQL

    U->>PV: Clic en Nuevo producto
    PV->>PD: abrir el formulario
    PD->>CR: list_categories(conn)
    CR->>DB: SELECT id, name FROM categories
    DB-->>CR: filas
    CR-->>PD: categorías para la lista desplegable
    U->>PD: Completa los datos y pulsa OK
    PD->>PS: create_product(conn, categoría, sku, nombre, precio, mínimo)
    PS->>PS: Normalizar el SKU y validar las reglas
    alt Datos inválidos
        PS-->>PD: ProductError
        PD-->>U: Aviso, el formulario sigue abierto
    else Datos válidos
        PS->>PR: create(conn, ...)
        PR->>DB: INSERT INTO products ... RETURNING
        alt SKU repetido
            DB-->>PS: UniqueViolation
            PS-->>PD: ProductError, el SKU ya existe
            PD-->>U: Aviso, el formulario sigue abierto
        else Se guardó
            DB-->>PR: producto creado
            PR-->>PS: Product
            PS-->>PD: Product
            PD-->>PV: aceptado, se cierra el formulario
            PV->>PV: load_products()
        end
    end
```

### 8.2 Registrar un movimiento de inventario

```mermaid
sequenceDiagram
    actor U as Usuario
    participant PV as ProductsView
    participant MD as MovementDialog
    participant IS as inventory_service
    participant DB as PostgreSQL

    U->>PV: Selecciona un producto y pulsa Registrar movimiento
    PV->>MD: abrir el formulario con sku, nombre y stock
    U->>MD: Elige tipo, cantidad y motivo, y pulsa OK
    MD->>IS: register_movement(conn, sku, tipo, cantidad, motivo)
    IS->>IS: Validar tipo y cantidad, calcular delta
    alt Tipo o cantidad no válidos
        IS-->>MD: InventoryError
        MD-->>U: Aviso, el formulario sigue abierto
    else Datos válidos
        IS->>DB: BEGIN y SELECT ... FOR UPDATE del producto
        alt No existe, está desactivado o el stock no alcanza
            IS->>DB: ROLLBACK
            IS-->>MD: InventoryError
            MD-->>U: Aviso, el formulario sigue abierto
        else Movimiento permitido
            IS->>DB: INSERT en inventory_movements
            IS->>DB: UPDATE del stock del producto
            IS->>DB: COMMIT
            IS-->>MD: stock resultante
            MD-->>PV: aceptado, se cierra el formulario
            PV->>PV: load_products()
        end
    end
```

### 8.3 Confirmar una venta

```mermaid
sequenceDiagram
    actor U as Usuario
    participant SV as SalesView
    participant SS as sale_service
    participant IS as inventory_service
    participant DB as PostgreSQL

    U->>SV: Confirmar venta
    SV->>SS: create_sale(conn, items, customer_id)
    SS->>SS: Validar carrito y sumar SKU repetidos
    SS->>DB: BEGIN
    opt Si se eligió un cliente
        SS->>DB: Verificar que el cliente exista
    end
    SS->>DB: INSERT INTO sales
    loop Por cada producto, en orden alfabético de SKU
        SS->>IS: register_movement(sku, OUT, cantidad, sale_id)
        IS->>DB: SELECT con FOR UPDATE, bloquea el producto
        break Se rompe una regla (no existe, está desactivado o no alcanza el stock)
            IS-->>SS: InventoryError
            SS->>DB: ROLLBACK, se deshace todo
            SS-->>SV: InventoryError
            SV-->>U: Aviso con el motivo, el carrito se conserva
        end
        IS->>DB: INSERT en inventory_movements y UPDATE del stock
        IS-->>SS: stock resultante
        SS->>DB: Leer el precio actual e INSERT en sale_items
    end
    SS->>DB: UPDATE del total de la venta
    SS->>DB: COMMIT
    SS-->>SV: sale_id y total
    SV-->>U: Venta registrada
```

> Las validaciones previas (carrito vacío, cantidad no válida) y la verificación del cliente también cancelan la venta con `SaleError`, que hereda de `InventoryError`. Las instrucciones `BEGIN`, `COMMIT` y `ROLLBACK` las emite `conn.transaction()`; se dibujan como mensajes de `sale_service` por claridad.

### 8.4 Consultar un reporte

```mermaid
sequenceDiagram
    actor U as Usuario
    participant RV as ReportsView
    participant RR as report_repository
    participant DB as PostgreSQL

    U->>RV: Elige un reporte en la lista
    RV->>RR: run_report(conn, key)
    RR->>RR: Buscar la consulta en REPORTS_BY_KEY
    RR->>DB: Ejecutar el SQL del reporte
    DB-->>RR: filas y descripción de columnas
    RR-->>RV: nombres de columnas y filas
    RV->>RV: Dar formato a los valores y llenar la tabla
    RV-->>U: Tabla del reporte
```

## 9. Diagrama de actividad: registrar un movimiento

La lógica de decisión de `register_movement`. Los errores posteriores a `BEGIN` deshacen la transacción.

```mermaid
flowchart TD
    A([Inicio: register_movement]) --> B{"¿Tipo válido?<br/>IN, OUT o ADJUST"}
    B -- No --> E1[/"InventoryError: tipo no válido"/]
    B -- Sí --> C{"¿Es un ajuste?"}
    C -- Sí --> D{"¿Cantidad distinta de 0?"}
    D -- No --> E2[/"InventoryError: el ajuste no puede ser 0"/]
    D -- Sí --> F["delta = cantidad, con su signo"]
    C -- No --> G{"¿Cantidad mayor que 0?"}
    G -- No --> E3[/"InventoryError: cantidad no válida"/]
    G -- Sí --> H["delta = +cantidad si es IN, -cantidad si es OUT"]
    F --> I
    H --> I["BEGIN y SELECT ... FOR UPDATE del producto"]
    I --> J{"¿Existe el producto?"}
    J -- No --> E4[/"InventoryError: no existe, ROLLBACK"/]
    J -- Sí --> K{"¿Está activo?"}
    K -- No --> E5[/"InventoryError: desactivado, ROLLBACK"/]
    K -- Sí --> L{"¿stock + delta es menor que 0?"}
    L -- Sí --> E6[/"InventoryError: stock insuficiente, ROLLBACK"/]
    L -- No --> M["INSERT en inventory_movements"]
    M --> N["UPDATE products SET stock = stock + delta"]
    N --> O["COMMIT"]
    O --> P([Fin: devuelve el stock resultante])
```

## 10. Diagrama de estados: producto

Ciclo de vida de un producto, con el estado de su stock mientras está activo.

```mermaid
stateDiagram-v2
    [*] --> Activo : create_product con stock 0

    state Activo {
        StockNormal --> StockBajo : el stock queda por debajo del mínimo
        StockBajo --> StockNormal : una entrada deja el stock igual o mayor al mínimo
    }

    Activo --> Desactivado : set_active con False
    Desactivado --> Activo : set_active con True
```

- Un producto recién creado tiene stock 0. Queda en `StockBajo` si su mínimo es mayor que 0, y en `StockNormal` si el mínimo es 0.
- En `StockBajo` el producto aparece en rojo en la pantalla de productos y en el reporte de stock bajo.
- Un producto `Desactivado` no aparece en los listados ni acepta movimientos ni ventas (regla RN-03).
- `set_active` existe en el repositorio, pero la interfaz aún no tiene el botón.

## 11. Diagrama de despliegue

```mermaid
flowchart TB
    subgraph PC["Computador del usuario (Windows)"]
        subgraph PY["Python (entorno virtual .venv)"]
            APP["StockPilot<br/>PySide6 + psycopg 3"]
            TEST["pytest<br/>pruebas con rollback"]
        end
        DBE["DBeaver<br/>administración y consultas"]
        ENV[".env<br/>credenciales locales"]
        PG[("PostgreSQL 18<br/>base stockpilot<br/>rol stockpilot_app")]
    end

    PY -- "lee la configuración" --> ENV
    PY -- "TCP 5432" --> PG
    DBE -- "TCP 5432" --> PG
```

Por defecto todo corre en el mismo computador (`localhost`). Si PostgreSQL estuviera en otro servidor, solo cambiaría `DB_HOST` en el `.env`.