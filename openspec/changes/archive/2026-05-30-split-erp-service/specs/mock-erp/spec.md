## Purpose

Delta spec: Mock ERP data store transitions from in-memory Python dictionaries in `app/mock_erp.py` to SQLite persistent storage in `erp_app/db.py` with service layer in `erp_app/services/`.

## MODIFIED Requirements

### Requirement: Orders data with status state machine
The system SHALL maintain orders in a SQLite `orders` table (order_id, type, status, customer, total, address, supplier, created_at, updated_at, estimated_delivery, cancel_reason, notes) with line items in `order_items` table. Status transitions SHALL follow: pending→shipping→delivered, any→cancelled. The data SHALL be accessible via `erp_app/services/order_service.py` functions, not via direct dictionary access to `mock_erp.orders`.

#### Scenario: Order data structure
- **WHEN** seed data is initialized
- **THEN** orders table contains at least 3 sample orders (123: shipping, 124: pending, 125: purchase/pending) with items in order_items table

#### Scenario: Status transition pending to shipping
- **WHEN** order status is "pending" and shipping is triggered
- **THEN** status changes to "shipping" and updated_at is refreshed in the database

#### Scenario: Invalid status transition rejected
- **WHEN** attempting to change status from "delivered" to "shipping"
- **THEN** system returns DATA_CONFLICT error

### Requirement: Inventory data with available calculation
The system SHALL maintain inventory in a SQLite `inventory` table (sku, name, qty, reserved, unit, unit_price, location, reorder_point, updated_at). The `available` field SHALL be computed as `qty - reserved` at query time, not stored as a column. Inventory operations SHALL be accessible via `erp_app/services/inventory_service.py`.

#### Scenario: Available quantity calculated
- **WHEN** inventory for "iPhone-15" has qty=60 and reserved=20
- **THEN** available is computed as 40 at query time

#### Scenario: Inventory reservation on order creation
- **WHEN** create_order is called for 2 units of iPhone-15
- **THEN** reserved increases by 2 and available decreases (qty - reserved)

#### Scenario: Inventory release on order cancellation
- **WHEN** cancel_order is called for an order with 2 units of iPhone-15
- **THEN** reserved decreases by 2 and available increases

### Requirement: Suppliers data
The system SHALL maintain suppliers in a SQLite `suppliers` table (supplier_id, name, contact, phone, lead_time_days, status) with SKU mappings in `supplier_items` junction table. Supplier data SHALL be accessible via `erp_app/services/supplier_service.py`.

#### Scenario: Supplier data structure
- **WHEN** seed data is initialized
- **THEN** suppliers table contains at least 2 sample suppliers (SUP-A, SUP-B) with their items in supplier_items

#### Scenario: Supplier items reference valid SKUs
- **WHEN** supplier SUP-A has items=["iPhone-15", "MacBook-Pro"]
- **THEN** both SKUs exist in the inventory table

### Requirement: Order counter for auto-increment
The system SHALL maintain the next order ID in the database (either as a sequence table or derived from MAX(order_id)), auto-incrementing when a new order is created.

#### Scenario: Auto-increment on order creation
- **WHEN** create_order is called and the highest existing order_id is "125"
- **THEN** new order gets order_id="126" and the next counter increments

## REMOVED Requirements

### Requirement: Mock ERP in-memory data store
**Reason**: Replaced by SQLite persistent storage in erp_app
**Migration**: All mock_erp.orders/inventory/suppliers dictionary access replaced with db.py CRUD calls via service layer
