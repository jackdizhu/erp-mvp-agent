## ADDED Requirements

### Requirement: Orders data with status state machine
The system SHALL maintain an orders dictionary with each order containing order_id, type (sales/purchase), status (pending/shipping/delivered/cancelled), customer, items, total, address, supplier, created_at, updated_at, estimated_delivery, cancel_reason, and notes. Status transitions SHALL follow: pending→shipping→delivered, any→cancelled.

#### Scenario: Order data structure
- **WHEN** mock ERP is initialized
- **THEN** orders contain at least 3 sample orders (123: shipping, 124: pending, 125: purchase/pending)

#### Scenario: Status transition pending to shipping
- **WHEN** order status is "pending" and shipping is triggered
- **THEN** status changes to "shipping" and updated_at is refreshed

#### Scenario: Invalid status transition rejected
- **WHEN** attempting to change status from "delivered" to "shipping"
- **THEN** system returns DATA_CONFLICT error

### Requirement: Inventory data with available calculation
The system SHALL maintain an inventory dictionary keyed by SKU, each containing sku, name, qty, reserved, available (calculated as qty - reserved), unit, unit_price, location, reorder_point, updated_at.

#### Scenario: Available quantity calculated
- **WHEN** inventory for "iPhone-15" has qty=60 and reserved=20
- **THEN** available is calculated as 40

#### Scenario: Inventory reservation on order creation
- **WHEN** create_order is called for 2 units of iPhone-15
- **THEN** reserved increases by 2 and available decreases by 2

#### Scenario: Inventory release on order cancellation
- **WHEN** cancel_order is called for an order with 2 units of iPhone-15
- **THEN** reserved decreases by 2 and available increases by 2

### Requirement: Suppliers data
The system SHALL maintain a suppliers dictionary keyed by supplier_id, each containing supplier_id, name, contact, phone, items (array of SKUs), lead_time_days, status.

#### Scenario: Supplier data structure
- **WHEN** mock ERP is initialized
- **THEN** suppliers contain at least 2 sample suppliers (SUP-A, SUP-B)

#### Scenario: Supplier items reference valid SKUs
- **WHEN** supplier SUP-A has items=["iPhone-15", "MacBook-Pro"]
- **THEN** both SKUs exist in the inventory dictionary

### Requirement: Order counter for auto-increment
The system SHALL maintain an order_counter with next_order_id that auto-increments when a new order is created.

#### Scenario: Auto-increment on order creation
- **WHEN** create_order is called and next_order_id is 126
- **THEN** new order gets order_id="126" and next_order_id becomes 127

### Requirement: Order status determines allowed operations
The system SHALL enforce that update and cancel operations are only allowed on orders in pending or shipping status, and delete is only allowed on cancelled orders.

#### Scenario: Update pending order allowed
- **WHEN** update_order is called on a pending order
- **THEN** operation proceeds normally

#### Scenario: Cancel delivered order rejected
- **WHEN** cancel_order is called on a delivered order
- **THEN** system returns DATA_CONFLICT error "订单已签收，无法取消"

#### Scenario: Delete non-cancelled order rejected
- **WHEN** delete_order is called on a shipping order
- **THEN** system returns DATA_CONFLICT error "仅可删除已取消的订单"
