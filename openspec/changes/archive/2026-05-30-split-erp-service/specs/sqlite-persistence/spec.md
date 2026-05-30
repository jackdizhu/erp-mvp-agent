## Purpose

Define the SQLite persistence layer that replaces the in-memory dictionary data store from mock_erp.py, providing durable storage for orders, inventory, and suppliers.

## ADDED Requirements

### Requirement: SQLite database initialization
The system SHALL create and manage a SQLite database file at a configurable path (default: `data/erp.db`), with connection pooling and automatic table creation on first access.

#### Scenario: Database created on first startup
- **WHEN** the application starts for the first time
- **THEN** a SQLite database file is created at the configured path with all required tables

#### Scenario: Database path configurable via environment variable
- **WHEN** `ERP_DB_PATH` environment variable is set to a custom path
- **THEN** the database is created at the specified path

#### Scenario: Tables created only if not exist
- **WHEN** the application starts with an existing database
- **THEN** no data is overwritten and existing tables are preserved (using IF NOT EXISTS)

### Requirement: Orders table with normalized structure
The system SHALL store orders in a `orders` table with columns: order_id (TEXT PK), type (TEXT), status (TEXT), customer (TEXT), total (REAL), address (TEXT), supplier (TEXT), created_at (TEXT), updated_at (TEXT), estimated_delivery (TEXT), cancel_reason (TEXT), notes (TEXT).

#### Scenario: Order stored in database
- **WHEN** a new sales order is created
- **THEN** a row is inserted into the orders table with all fields populated

#### Scenario: Order query by ID
- **WHEN** querying an order by order_id
- **THEN** the system returns the full order record from the orders table joined with order_items

### Requirement: Order items as separate table
The system SHALL store order line items in an `order_items` table with columns: id (INTEGER PK), order_id (TEXT FK → orders.order_id), sku (TEXT), name (TEXT), qty (INTEGER), price (REAL).

#### Scenario: Order items stored separately
- **WHEN** create_order is called with 2 items
- **THEN** 2 rows are inserted into order_items with the same order_id

#### Scenario: Query returns enriched items
- **WHEN** querying an order
- **THEN** the result includes items from order_items joined back to the parent order

### Requirement: Inventory table with computed available quantity
The system SHALL store inventory in an `inventory` table with columns: sku (TEXT PK), name (TEXT), qty (INTEGER), reserved (INTEGER), unit (TEXT), unit_price (REAL), location (TEXT), reorder_point (INTEGER), updated_at (TEXT). The `available` field SHALL be computed as `qty - reserved` at query time.

#### Scenario: Available quantity computed
- **WHEN** inventory for "iPhone-15" has qty=60 and reserved=20
- **THEN** available is computed as 40 at query time

#### Scenario: Inventory query by SKU
- **WHEN** querying inventory for a valid SKU
- **THEN** the system returns the inventory record with computed available quantity

### Requirement: Suppliers table with junction for items
The system SHALL store suppliers in a `suppliers` table (supplier_id TEXT PK, name TEXT, contact TEXT, phone TEXT, lead_time_days INTEGER, status TEXT) and supplier-SKU mappings in a `supplier_items` junction table (id INTEGER PK, supplier_id TEXT FK, sku TEXT FK).

#### Scenario: Supplier with items stored
- **WHEN** supplier SUP-A supplies iPhone-15 and MacBook-Pro
- **THEN** one row in suppliers and two rows in supplier_items are created

#### Scenario: Supplier query returns items list
- **WHEN** querying supplier SUP-A
- **THEN** the result includes items=["iPhone-15", "MacBook-Pro"] from supplier_items

### Requirement: Seed data initialization
The system SHALL initialize the database with the same demonstration data that currently exists in mock_erp.py: 3 sample orders (123: shipping, 124: pending, 125: purchase/pending), 2 inventory items (iPhone-15, MacBook-Pro), and 2 suppliers (SUP-A, SUP-B).

#### Scenario: Seed data loaded on first run
- **WHEN** the application starts with an empty database
- **THEN** seed data is inserted: 3 orders, 2 inventory records, 2 suppliers

#### Scenario: Seed data not reloaded on subsequent runs
- **WHEN** the application starts with an existing database containing orders
- **THEN** no duplicate seed data is inserted

### Requirement: CRUD helpers for all entities
The system SHALL provide helper functions in `db.py` for: create_order, query_order, query_orders_batch, update_order, cancel_order, delete_order, query_inventory, update_inventory, query_supplier, query_supplier_with_items, create_supplier_items.

#### Scenario: Query order returns enriched data
- **WHEN** `db.query_order("123")` is called
- **THEN** it returns order data with items list populated from order_items

#### Scenario: Batch query returns multiple orders
- **WHEN** `db.query_orders_batch(["123", "124", "125"])` is called
- **THEN** it returns a dict mapping order_ids to their status and type
