# SCM Procurement Module - Database Schema Documentation

## 1. Overview

This document describes the database table structure for the `scm_procurement` Odoo module, based on the provided SQL creation scripts. It details the core tables, relational tables, wizard tables, and potential issues identified in the schema definition.

## 2. Core Data Tables

### 2.1. `scm_pr_consolidation_session`

**Purpose**: Represents a session for consolidating Purchase Requests (PRs) over a specific period, managing the overall workflow from creation through inventory validation to PO generation.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `user_id`                 | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL    | Responsible User             |
| `company_id`              | integer                     | FOREIGN KEY (res_company) ON DELETE SET NULL  | Company                      |
| `warehouse_id`            | integer                     | NOT NULL, FOREIGN KEY (stock_warehouse) ...   | Warehouse for inventory      |
| `inventory_validated_by`  | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL    | User who validated inventory |
| `total_stockout_items`    | integer                     |                                               | Computed: Stockout Items     |
| `total_below_safety`      | integer                     |                                               | Computed: Below Safety Stock |
| `total_below_reorder`     | integer                     |                                               | Computed: Below Reorder Point|
| `create_uid`              | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL    | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL    | Last Updated by User         |
| `name`                    | character varying           | NOT NULL                                      | Reference Name               |
| `state`                   | character varying           |                                               | Status of the session        |
| `inventory_status`        | character varying           |                                               | Overall Inventory Status     |
| `date_from`               | date                        | NOT NULL                                      | Start Date for PR collection |
| `date_to`                 | date                        | NOT NULL                                      | End Date for PR collection   |
| `notes`                   | text                        |                                               | General Notes                |
| `inventory_validation_notes`| text                        |                                               | Notes from inventory validation|
| `inventory_validated`     | boolean                     |                                               | Flag: Inventory Validated    |
| `has_inventory_issues`    | boolean                     |                                               | Computed: Has Issues?        |
| `has_critical_shortages`  | boolean                     |                                               | Computed: Has Critical?      |
| `pending_approval`        | boolean                     |                                               | Flag: Awaiting Inv. Approval |
| `creation_date`           | timestamp without time zone |                                               | Date Session Created         |
| `validation_date`         | timestamp without time zone |                                               | Date Lines Validated         |
| `po_creation_date`        | timestamp without time zone |                                               | Date POs Created             |
| `inventory_validation_date`| timestamp without time zone |                                               | Date Inventory Validated     |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |
| `total_amount`            | double precision            |                                               | Computed: Total Value        |
| `purchase_order_ids`      | One2many                    | Inverse: consolidation_id on purchase.order   | Related Purchase Orders      |

**Relationships**:
*   Many-to-One with `res_users` (responsible, creator, updater, validator).
*   Many-to-One with `res_company`.
*   Many-to-One with `stock_warehouse`.
*   One-to-Many with `scm_consolidated_pr_line`.
*   Many-to-Many with `purchase_request` via `scm_pr_consolidation_request_rel`.
*   *Note: Assumed Many-to-Many relationships with `hr_department` and `product_category` exist based on Odoo model structure, but corresponding relation tables (`scm_consolidation_department_rel`, `scm_consolidation_category_rel`) are missing from the provided script.*

**State Field Values**:

| Value                     | Description                                                |
|---------------------------|------------------------------------------------------------|
| `draft`                   | Initial state, session is being created                    |
| `selecting_lines`         | User is selecting PR lines to consolidate                  |
| `in_progress`             | Lines have been selected, consolidation in progress        |
| `validated`               | Consolidation has been validated                          |
| `inventory_validation`    | Inventory validation is in progress                       |
| `po_creation`             | Ready for PO creation                                      |
| `po_created`              | POs have been created                                      |
| `done`                    | Process is complete                                        |
| `cancelled`               | Process has been cancelled                                 |

### 2.2. `scm_consolidated_pr_line`

**Purpose**: Represents the aggregated demand for a specific product within a consolidation session.

**Columns**:

| Column Name                 | Data Type                   | Constraints                                      | Description                  |
|-----------------------------|-----------------------------|--------------------------------------------------|------------------------------|
| `id`                        | integer                     | PRIMARY KEY, DEFAULT nextval(...)                | Unique identifier            |
| `consolidation_id`          | integer                     | NOT NULL, FOREIGN KEY (...) ON DELETE CASCADE    | Link to Session              |
| `product_id`                | integer                     | NOT NULL, FOREIGN KEY (product_product) ...      | Product being consolidated   |
| `product_uom_id`            | integer                     | NOT NULL, FOREIGN KEY (uom_uom) ...              | Unit of Measure              |
| `suggested_vendor_id`       | integer                     | FOREIGN KEY (res_partner) ON DELETE SET NULL     | Suggested Vendor             |
| `purchase_suggestion_id`    | integer                     | *Likely FK to a missing purchase suggestion table* | Related Purchase Suggestion  |
| `company_id`                | integer                     | FOREIGN KEY (res_company) ON DELETE SET NULL     | Company                      |
| `exception_approved_by`     | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL       | User who approved exception  |
| `warehouse_id`              | integer                     | FOREIGN KEY (stock_warehouse) ON DELETE SET NULL | Warehouse                    |
| `create_uid`                | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL       | Created by User              |
| `write_uid`                 | integer                     | FOREIGN KEY (res_users) ON DELETE SET NULL       | Last Updated by User         |
| `state`                     | character varying           | NOT NULL                                         | Status of the line           |
| `priority`                  | character varying           |                                                  | Priority Level               |
| `inventory_status`          | character varying           |                                                  | Inventory Check Result       |
| `procurement_recommendation`| character varying           |                                                  | System Recommendation        |
| `earliest_date_required`    | date                        |                                                  | Earliest Need Date           |
| `last_purchase_date`        | date                        |                                                  | Date of Last Purchase        |
| `notes`                     | text                        |                                                  | General Notes                |
| `inventory_notes`           | text                        |                                                  | Inventory-specific Notes     |
| `total_quantity`            | numeric                     | NOT NULL                                         | Aggregated Quantity          |
| `available_quantity`        | numeric                     |                                                  | Computed: Stock Available    |
| `quantity_to_purchase`      | numeric                     |                                                  | Quantity to Buy              |
| `purchase_price`            | numeric                     |                                                  | Estimated Purchase Price     |
| `subtotal`                  | numeric                     |                                                  | Computed: Line Value         |
| `turnover_rate`             | numeric                     |                                                  | Computed: Turnover           |
| `quantity`                  | numeric                     |                                                  | *Seems redundant?*           |
| `last_purchase_price`       | numeric                     |                                                  | Price from Last Purchase     |
| `avg_monthly_usage`         | numeric                     |                                                  | Computed: Usage Rate         |
| `inventory_exception`       | boolean                     |                                                  | Flag: Has Inventory Exception|
| `exception_approval_date`   | timestamp without time zone |                                                  | Date Exception Approved      |
| `create_date`               | timestamp without time zone |                                                  | Odoo: Record Creation Date   |
| `write_date`                | timestamp without time zone |                                                  | Odoo: Record Update Date     |
| `stock_coverage`            | double precision            |                                                  | Computed: Stock Coverage     |

**Constraints**:
*   `UNIQUE (consolidation_id, product_id)`: Ensures a product appears only once per session.

**Relationships**:
*   Many-to-One with `scm_pr_consolidation_session`.
*   Many-to-One with `product_product`.
*   Many-to-One with `uom_uom`.
*   Many-to-One with `res_partner` (suggested vendor).
*   Many-to-One with `res_company`.
*   Many-to-One with `res_users` (creator, updater, approver).
*   Many-to-One with `stock_warehouse`.
*   *Note: Assumed Many-to-Many relationship with `purchase_request_line` exists based on Odoo model structure, but the corresponding relation table (`scm_consolidated_pr_line_purchase_request_line_rel`) is missing from the provided script.*

**Indexes**:
*   `scm_consolidated_pr_line__consolidation_id_index` on `consolidation_id`.

### 2.3. `scm_inventory_rule`

**Purpose**: Defines inventory parameters like safety stock and reorder points for products or categories.

**Columns**:

| Column Name           | Data Type         | Constraints                                 | Description             |
|-----------------------|-------------------|---------------------------------------------|-------------------------|
| `id`                  | integer           | PRIMARY KEY, DEFAULT nextval(...)           | Unique identifier       |
| `company_id`          | integer           | NOT NULL, FOREIGN KEY (res_company) ...     | Company                 |
| `product_id`          | integer           | FOREIGN KEY (product_product) ...           | Specific Product        |
| `product_category_id` | integer           | FOREIGN KEY (product_category) ...          | Product Category        |
| `lead_time`           | integer           |                                             | Lead Time (Days)        |
| `warehouse_id`        | integer           | FOREIGN KEY (stock_warehouse) ...           | Warehouse               |
| `create_uid`          | integer           | FOREIGN KEY (res_users) ON DELETE SET NULL  | Created by User         |
| `write_uid`           | integer           | FOREIGN KEY (res_users) ON DELETE SET NULL  | Last Updated by User    |
| `name`                | character varying | NOT NULL                                    | Rule Name               |
| `priority`            | character varying |                                             | Priority                |
| `active`              | boolean           |                                             | Is Rule Active?         |
| `create_date`         | timestamp         |                                             | Odoo: Record Creation   |
| `write_date`          | timestamp         |                                             | Odoo: Record Update     |
| `safety_stock_qty`    | double precision  |                                             | Safety Stock Quantity   |
| `min_stock_qty`       | double precision  |                                             | Minimum Stock Quantity  |
| `reorder_point`       | double precision  |                                             | Reorder Point           |
| `max_stock_qty`       | double precision  |                                             | Maximum Stock Quantity  |
| `avg_daily_usage`     | double precision  |                                             | Average Daily Usage     |

**Relationships**:
*   Many-to-One with `res_company`.
*   Many-to-One with `product_product` (optional).
*   Many-to-One with `product_category` (optional).
*   Many-to-One with `stock_warehouse`.
*   Many-to-One with `res_users` (creator, updater).

### 2.4. `scm_forecast`

**Purpose**: Stores header information for inventory forecasts.

**Columns**:

| Column Name       | Data Type         | Constraints                               | Description          |
|-------------------|-------------------|-------------------------------------------|----------------------|
| `id`              | integer           | PRIMARY KEY, DEFAULT nextval(...)         | Unique identifier    |
| `company_id`      | integer           | NOT NULL, FOREIGN KEY (res_company) ... | Company              |
| `product_id`      | integer           | NOT NULL, FOREIGN KEY (product_product) ... | Product              |
| `warehouse_id`    | integer           | NOT NULL, FOREIGN KEY (stock_warehouse) ... | Warehouse            |
| `create_uid`      | integer           | FOREIGN KEY (res_users) ON DELETE SET NULL| Created by User      |
| `write_uid`       | integer           | FOREIGN KEY (res_users) ON DELETE SET NULL| Last Updated by User |
| `name`            | character varying | NOT NULL                                  | Reference Name       |
| `forecast_period` | character varying |                                           | Period (e.g., Month) |
| `state`           | character varying |                                           | Status               |
| `date`            | date              | NOT NULL                                  | Forecast Date        |
| `notes`           | text              |                                           | Notes                |
| `is_template`     | boolean           |                                           | Is Template?         |
| `create_date`     | timestamp         |                                           | Odoo: Record Creation|
| `write_date`      | timestamp         |                                           | Odoo: Record Update  |
| `forecast_qty`    | double precision  | NOT NULL                                  | Forecasted Quantity  |
| `actual_qty`      | double precision  |                                           | Actual Quantity      |
| `variance`        | double precision  |                                           | Computed Variance    |
| `variance_percent`| double precision  |                                           | Computed Variance %  |

**Relationships**:
*   Many-to-One with `res_company`.
*   Many-to-One with `product_product`.
*   Many-to-One with `stock_warehouse`.
*   Many-to-One with `res_users` (creator, updater).
*   One-to-Many with `scm_forecast_line`.

### 2.5. `scm_forecast_line`

**Purpose**: Stores detailed line information for an inventory forecast over time.

**Columns**:

| Column Name          | Data Type         | Constraints                                | Description          |
|----------------------|-------------------|--------------------------------------------|----------------------|
| `id`                 | integer           | PRIMARY KEY, DEFAULT nextval(...)          | Unique identifier    |
| `forecast_id`        | integer           | NOT NULL, FOREIGN KEY (...) ON DELETE CASCADE | Link to Forecast Header|
| `product_id`         | integer           | NOT NULL, FOREIGN KEY (product_product) ...  | Product              |
| `warehouse_id`       | integer           | NOT NULL, FOREIGN KEY (stock_warehouse) ...  | Warehouse            |
| `create_uid`         | integer           | FOREIGN KEY (res_users) ON DELETE SET NULL | Created by User      |
| `write_uid`          | integer           | FOREIGN KEY (res_users) ON DELETE SET NULL | Last Updated by User |
| `state`              | character varying |                                            | Status               |
| `date`               | date              | NOT NULL                                   | Date for this line   |
| `notes`              | text              |                                            | Notes                |
| `create_date`        | timestamp         |                                            | Odoo: Record Creation|
| `write_date`         | timestamp         |                                            | Odoo: Record Update  |
| `forecast_qty`       | double precision  | NOT NULL                                   | Forecasted Quantity  |
| `actual_qty`         | double precision  |                                            | Actual Quantity      |
| `expected_inventory` | double precision  |                                            | Expected Stock Level |

**Relationships**:
*   Many-to-One with `scm_forecast`.
*   Many-to-One with `product_product`.
*   Many-to-One with `stock_warehouse`.
*   Many-to-One with `res_users` (creator, updater).

## 3. Relation Tables

### 3.1. `scm_pr_consolidation_request_rel`

**Purpose**: Manages the Many-to-Many relationship between `scm_pr_consolidation_session` and `purchase_request`.

**Columns**:

| Column Name        | Data Type | Constraints                                     | Description             |
|--------------------|-----------|-------------------------------------------------|-------------------------|
| `consolidation_id` | integer   | PRIMARY KEY (part 1), FOREIGN KEY (...) ON DELETE CASCADE | Link to Session         |
| `request_id`       | integer   | PRIMARY KEY (part 2), FOREIGN KEY (...) ON DELETE CASCADE | Link to Purchase Request|

**Indexes**:
*   `scm_pr_consolidation_request_re_request_id_consolidation_id_idx` on (`request_id`, `consolidation_id`).

## 4. Wizard Tables

### 4.1. `validate_inventory_wizard`

**Purpose**: Temporary table for the inventory validation wizard, allowing users to review and validate inventory levels for consolidated lines.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `consolidation_id`        | integer                     | FOREIGN KEY (scm_pr_consolidation_session)    | Related Consolidation Session|
| `warehouse_id`            | integer                     | FOREIGN KEY (stock_warehouse)                 | Warehouse for inventory      |
| `validation_notes`        | text                        |                                               | Notes from validation        |
| `include_critical_only`   | boolean                     | DEFAULT true                                  | Filter for critical items    |
| `auto_approve_non_critical`| boolean                    | DEFAULT true                                  | Auto-approve non-critical    |
| `request_manager_approval`| boolean                     | DEFAULT true                                  | Request manager approval     |
| `update_safety_stock`     | boolean                     | DEFAULT false                                 | Update safety stock          |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

**Implementation Status (April 2023):**
- The `validate_inventory_wizard` table has been implemented and is fully functional.
- The wizard displays all consolidated lines with their current stock, required quantity, and available quantity.
- Users can filter to view only critical items, and the system calculates the quantity to purchase.
- After validation, users can proceed to PO creation.

### 4.2. `validate_inventory_wizard_line`

**Purpose**: Temporary table for lines in the inventory validation wizard, representing individual products to be validated.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `wizard_id`               | integer                     | FOREIGN KEY (validate_inventory_wizard)       | Related Wizard               |
| `product_id`              | integer                     | FOREIGN KEY (product_product)                 | Product                      |
| `uom_id`                  | integer                     | FOREIGN KEY (uom_uom)                         | Unit of Measure              |
| `current_stock`           | numeric                     |                                               | Current stock level          |
| `required_qty`            | numeric                     |                                               | Required quantity            |
| `available_qty`           | numeric                     |                                               | Available quantity           |
| `quantity_to_purchase`    | numeric                     |                                               | Quantity to purchase         |
| `inventory_status`        | character varying           |                                               | Inventory status             |
| `notes`                   | text                        |                                               | Notes                        |
| `inventory_exception`     | boolean                     |                                               | Has inventory exception      |
| `exception_approved_by`   | integer                     | FOREIGN KEY (res_users)                       | Exception approved by        |
| `exception_approval_date` | timestamp without time zone |                                               | Exception approval date      |
| `inventory_notes`         | text                        |                                               | Inventory notes              |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

**Implementation Status (April 2023):**
- The `validate_inventory_wizard_line` table has been implemented and is fully functional.
- The wizard lines display current stock, required quantity, available quantity, and quantity to purchase.
- The inventory status is calculated based on current stock and required quantity.
- Users can add notes and mark exceptions for approval.

### 4.3. `create_po_wizard`

**Purpose**: Temporary table for the purchase order creation wizard, allowing users to create purchase orders from validated consolidated lines.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `consolidation_id`        | integer                     | FOREIGN KEY (scm_pr_consolidation_session)    | Related Consolidation Session|
| `warehouse_id`            | integer                     | FOREIGN KEY (stock_warehouse)                 | Warehouse for inventory      |
| `vendor_id`               | integer                     | FOREIGN KEY (res_partner)                     | Vendor for PO                |
| `date_order`              | date                        |                                               | Order date                   |
| `notes`                   | text                        |                                               | Notes                        |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

**Implementation Status (April 2023):**
- The `create_po_wizard` table has been implemented and is partially functional.
- The wizard allows users to select a vendor and create a PO with the validated quantities.
- The created PO is linked to the consolidation session and visible in a dedicated tab.
- Vendor suggestion and grouping by vendor are planned for future implementation.

### 4.4. `create_po_wizard_line`

**Purpose**: Temporary table for lines in the purchase order creation wizard, representing individual products to be purchased.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `wizard_id`               | integer                     | FOREIGN KEY (create_po_wizard)                | Related Wizard               |
| `product_id`              | integer                     | FOREIGN KEY (product_product)                 | Product                      |
| `product_uom_id`          | integer                     | FOREIGN KEY (uom_uom)                         | Unit of Measure              |
| `product_qty`             | numeric                     |                                               | Quantity to purchase         |
| `price_unit`              | numeric                     |                                               | Price per unit               |
| `price_subtotal`          | numeric                     |                                               | Price subtotal               |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

**Implementation Status (April 2023):**
- The `create_po_wizard_line` table has been implemented and is partially functional.
- The wizard lines display product, quantity, and price information.
- The lines are created from validated consolidated lines with positive quantity to purchase.

## 5. Problematic / Unknown Tables

The following tables were found in the script but seem incorrect or are likely artifacts of previous development/errors:

### 5.1. `_unknown_scm_create_consolidation_wizard_rel`
### 5.2. `_unknown_scm_pr_consolidation_session_rel`

**Purpose**: Unknown. These tables attempt to create a Many-to-Many relationship between `scm_create_consolidation_wizard` or `scm_pr_consolidation_session` and a non-existent table/model represented by `_unknown_id`.

**Columns**:
*   `scm_..._id`: Foreign key to the respective SCM table.
*   `_unknown_id`: Foreign key to a non-existent entity.

**Note**: These tables indicate a schema inconsistency or error. They should likely be dropped or corrected to reference valid tables/models if a relationship was intended. Their presence might be related to the Odoo ORM errors previously encountered.

## 6. Summary

The schema supports PR consolidation (`scm_pr_consolidation_session`, `scm_consolidated_pr_line`) linked to purchase requests (`purchase_request`). It includes functionality for inventory rules (`scm_inventory_rule`) and forecasting (`scm_forecast`, `scm_forecast_line`). Wizard tables aid in UI processes. Key relationships are established via foreign keys and dedicated relation tables. However, some expected relation tables seem missing, and the `_unknown_*` tables suggest schema errors that need addressing.

## 6. Phase 2 Implementation Updates (April 2023)

### 6.1. New Wizard Tables

#### 6.1.1. `validate_inventory_wizard`

**Purpose**: Temporary table for the inventory validation wizard, allowing users to review and validate inventory levels for consolidated lines.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `consolidation_id`        | integer                     | FOREIGN KEY (scm_pr_consolidation_session)    | Related Consolidation Session|
| `warehouse_id`            | integer                     | FOREIGN KEY (stock_warehouse)                 | Warehouse for inventory      |
| `validation_notes`        | text                        |                                               | Notes from validation        |
| `include_critical_only`   | boolean                     | DEFAULT true                                  | Filter for critical items    |
| `auto_approve_non_critical`| boolean                    | DEFAULT true                                  | Auto-approve non-critical    |
| `request_manager_approval`| boolean                     | DEFAULT true                                  | Request manager approval     |
| `update_safety_stock`     | boolean                     | DEFAULT false                                 | Update safety stock          |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

#### 6.1.2. `validate_inventory_wizard_line`

**Purpose**: Temporary table for lines in the inventory validation wizard, representing individual products to be validated.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `wizard_id`               | integer                     | FOREIGN KEY (validate_inventory_wizard)       | Related Wizard               |
| `product_id`              | integer                     | FOREIGN KEY (product_product)                 | Product                      |
| `uom_id`                  | integer                     | FOREIGN KEY (uom_uom)                         | Unit of Measure              |
| `current_stock`           | numeric                     |                                               | Current stock level          |
| `required_qty`            | numeric                     |                                               | Required quantity            |
| `available_qty`           | numeric                     |                                               | Available quantity           |
| `quantity_to_purchase`    | numeric                     |                                               | Quantity to purchase         |
| `inventory_status`        | character varying           |                                               | Inventory status             |
| `notes`                   | text                        |                                               | Notes                        |
| `inventory_exception`     | boolean                     |                                               | Has inventory exception      |
| `exception_approved_by`   | integer                     | FOREIGN KEY (res_users)                       | Exception approved by        |
| `exception_approval_date` | timestamp without time zone |                                               | Exception approval date      |
| `inventory_notes`         | text                        |                                               | Inventory notes              |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

#### 6.1.3. `create_po_wizard`

**Purpose**: Temporary table for the purchase order creation wizard, allowing users to create purchase orders from validated consolidated lines.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `consolidation_id`        | integer                     | FOREIGN KEY (scm_pr_consolidation_session)    | Related Consolidation Session|
| `warehouse_id`            | integer                     | FOREIGN KEY (stock_warehouse)                 | Warehouse for inventory      |
| `vendor_id`               | integer                     | FOREIGN KEY (res_partner)                     | Vendor for PO                |
| `date_order`              | date                        |                                               | Order date                   |
| `notes`                   | text                        |                                               | Notes                        |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

#### 6.1.4. `create_po_wizard_line`

**Purpose**: Temporary table for lines in the purchase order creation wizard, representing individual products to be purchased.

**Columns**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `id`                      | integer                     | PRIMARY KEY, DEFAULT nextval(...)             | Unique identifier            |
| `wizard_id`               | integer                     | FOREIGN KEY (create_po_wizard)                | Related Wizard               |
| `product_id`              | integer                     | FOREIGN KEY (product_product)                 | Product                      |
| `product_uom_id`          | integer                     | FOREIGN KEY (uom_uom)                         | Unit of Measure              |
| `product_qty`             | numeric                     |                                               | Quantity to purchase         |
| `price_unit`              | numeric                     |                                               | Price per unit               |
| `price_subtotal`          | numeric                     |                                               | Price subtotal               |
| `create_uid`              | integer                     | FOREIGN KEY (res_users)                       | Created by User              |
| `write_uid`               | integer                     | FOREIGN KEY (res_users)                       | Last Updated by User         |
| `create_date`             | timestamp without time zone |                                               | Odoo: Record Creation Date   |
| `write_date`              | timestamp without time zone |                                               | Odoo: Record Update Date     |

### 6.2. Updates to Core Tables

#### 6.2.1. `scm_pr_consolidation_session`

**Updates**:

- Added `purchase_order_ids` field: One2many relationship with `purchase.order` model, linking purchase orders created from the consolidation session.
- Updated state field to include 'po_creation' and 'po_created' states.
- Added `po_creation_date` field to track when purchase orders were created.

**Columns Added**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `purchase_order_ids`      | One2many                    | Inverse: consolidation_id on purchase.order   | Related Purchase Orders      |
| `po_creation_date`        | timestamp without time zone |                                               | Date POs Created             |

**State Field Values**:

| Value                     | Description                                                |
|---------------------------|------------------------------------------------------------|
| `draft`                   | Initial state, session is being created                    |
| `selecting_lines`         | User is selecting PR lines to consolidate                  |
| `in_progress`             | Lines have been selected, consolidation in progress        |
| `validated`               | Consolidation has been validated                          |
| `inventory_validation`    | Inventory validation is in progress                       |
| `po_creation`             | Ready for PO creation                                      |
| `po_created`              | POs have been created                                      |
| `done`                    | Process is complete                                        |
| `cancelled`               | Process has been cancelled                                 |

#### 6.2.2. `purchase_order`

**Updates**:

- Added `consolidation_id` field: Many2one relationship with `scm.pr.consolidation.session` model, linking the purchase order to the consolidation session that created it.
- Added `is_from_consolidation` field: Computed field indicating whether the purchase order was created from a consolidation session.

**Columns Added**:

| Column Name               | Data Type                   | Constraints                                   | Description                  |
|---------------------------|-----------------------------|-----------------------------------------------|------------------------------|
| `consolidation_id`        | integer                     | FOREIGN KEY (scm_pr_consolidation_session)    | Related Consolidation Session|
| `is_from_consolidation`   | boolean                     | Computed field                                | Created from consolidation   |

## 7. Summary

The schema supports PR consolidation (`scm_pr_consolidation_session`, `scm_consolidated_pr_line`) linked to purchase requests (`purchase_request`). It includes functionality for inventory rules (`scm_inventory_rule`) and forecasting (`scm_forecast`, `scm_forecast_line`). Wizard tables aid in UI processes. Key relationships are established via foreign keys and dedicated relation tables. However, some expected relation tables seem missing, and the `_unknown_*` tables suggest schema errors that need addressing.

# Phase 4: Fulfillment Process & Tracking – Database Schema

## scm_pr_fulfillment_plan

| Field                   | Type         | Description                                 |
|-------------------------|--------------|---------------------------------------------|
| id                      | Integer      | Primary key                                 |
| pr_line_id              | Many2one     | Linked PR line (`purchase.request.line`)    |
| pr_id                   | Many2one     | Linked PR (`purchase.request`) (related)    |
| consolidation_id        | Many2one     | PR Consolidation Session (related)          |
| source_type             | Selection    | stock / transfer / po                       |
| source_location_id      | Many2one     | Source location                             |
| destination_location_id | Many2one     | Destination location                        |
| planned_start_date      | DateTime     | Planned start date                          |
| planned_end_date        | DateTime     | Planned end date                            |
| actual_start_date       | DateTime     | Actual start date                           |
| actual_end_date         | DateTime     | Actual end date                             |
| responsible_id          | Many2one     | Responsible user/department                 |
| po_ids                  | One2many     | Linked Purchase Orders                      |
| transfer_ids            | One2many     | Linked Internal Transfers                   |
| stock_move_ids          | One2many     | Linked Stock Moves (on-hand fulfillment)    |
| status                  | Selection    | pending / in_progress / fulfilled / partial / exception |
| planned_qty             | Float        | Planned quantity                            |
| fulfilled_qty           | Float        | Fulfilled quantity                          |
| remaining_qty           | Float        | Remaining quantity                          |
| timeline                | Char         | Timeline/Notes                              |
| note                    | Text         | Notes                                       |
| create_date             | DateTime     | Created On                                  |
| write_date              | DateTime     | Last Updated                                |

## Related Models/Fields

- **purchase.request.line**: Add One2many to `scm_pr_fulfillment_plan` for traceability.
- **purchase.request**: Add One2many to `scm_pr_fulfillment_plan` (computed via PR lines).
- **scm_consolidation_session**: Add One2many to `scm_pr_fulfillment_plan` (computed via PR lines).
- **stock.picking**: Link to fulfillment plan via `transfer_ids`.
- **purchase.order**: Link to fulfillment plan via `po_ids`.
- **stock.move**: Link to fulfillment plan via `stock_move_ids`.

## Status Propagation

- Status fields on PR line, PR, and consolidation session should be computed based on the status of linked fulfillment plans.

## Audit & Traceability

- All user overrides, exceptions, and workflow actions should be logged (e.g., via chatter or a dedicated log model). 