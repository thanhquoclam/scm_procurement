# Functional Requirements Document: SCM Procurement Module (Phase 1, 2 & 3)

**Version:** 1.1
**Date:** 2025-04-10

**1. Introduction**

*   **1.1 Purpose:** This document defines the functional requirements for Phase 1 (Purchase Request Consolidation), Phase 2 (Inventory Validation), and Phase 3 (Purchase Order Creation) of the SCM Procurement Odoo Module. It details the expected behavior, user interactions, data handling, and business logic necessary to achieve the module's objectives for these phases.
*   **1.2 Scope:**
    *   **In Scope:**
        *   Creation and management of PR Consolidation Sessions.
        *   Automated collection and aggregation of approved Purchase Requests based on session criteria.
        *   Review and validation of consolidated data.
        *   Automated inventory level checking against consolidated demand.
        *   Identification and categorization of inventory statuses (sufficient, shortages, etc.).
        *   Workflow for reviewing and handling inventory exceptions.
        *   Final approval of the inventory validation stage.
        *   Creation of purchase orders from validated consolidation lines.
        *   Vendor assignment and grouping for purchase orders.
        *   Application of pricing rules and vendor pricelists.
        *   Tracking of PO creation status and history.
    *   **Out of Scope:**
        *   Detailed reporting and analytics capabilities (beyond basic computed fields/counts).
        *   Module configuration settings (e.g., setting up approval rules, defining inventory rule parameters - although the *use* of these rules is in scope).
        *   Administration and user role management.
        *   Data migration from legacy systems.
*   **1.3 Audience:** This document is intended for:
    *   Business Analysts: To understand and verify functional scope.
    *   Odoo Developers: To guide the implementation and coding.
    *   Quality Assurance Testers: To create test cases and scenarios.
    *   Project Managers & Stakeholders: To understand module capabilities.
*   **1.4 Definitions & Glossary:**
    *   **PR:** Purchase Request.
    *   **PO:** Purchase Order.
    *   **SCM:** Supply Chain Management.
    *   **Consolidation Session:** A specific instance (`scm_pr_consolidation_session`) used to group PRs for processing.
    *   **Consolidated Line:** A record (`scm_consolidated_pr_line`) representing the total demand for a single product within a session.
    *   **Inventory Status:** The classification of a product's stock level relative to demand and rules (e.g., Sufficient, Stockout, Below Safety Stock).

**2. Overall Description**

*   **2.1 System Overview:** The SCM Procurement module streamlines the procurement process within Odoo by automating the consolidation of purchase needs, validating inventory availability, and preparing data for efficient purchasing. Phase 1 focuses on gathering and organizing demand, while Phase 2 assesses the supply situation based on current inventory.
*   **2.2 User Characteristics:**
    *   **Procurement Officer:** Primary user, responsible for creating sessions, initiating consolidation, reviewing data, and managing the process flow through inventory validation.
    *   **Inventory Manager:** Reviews inventory exceptions, approves critical shortages, potentially configures inventory rules.
    *   *(Other roles like Department Manager, PR Submitter may have view access or involvement in related approvals not detailed in this scope).*
*   **2.3 Assumptions:**
    *   The module is deployed within a functional Odoo 17 environment.
    *   Dependent Odoo modules (Stock, Purchase, Purchase Request, Mail, Product, Base) are installed and configured.
    *   Necessary master data (Products, Warehouses, Users, Departments, Categories, UoM) is available and correctly configured.
    *   Purchase Requests follow a standard Odoo workflow where they reach an 'approved' state.
*   **2.4 Dependencies:**
    *   Odoo Base Framework
    *   `product`: For product data.
    *   `stock`: For inventory levels, warehouses, UoM.
    *   `purchase`: Base purchasing concepts.
    *   `purchase_request`: Source of purchase requests (likely OCA module).
    *   `mail`: For notifications and activity tracking.
    *   `hr` (Implicit): For `hr.department` if department filtering is used.
*   **2.5 Constraints:**
    *   The module must integrate with existing Odoo modules (Stock, Purchase, Purchase Request).
    *   The module must follow Odoo's standard UI/UX patterns.
    *   The module must handle large volumes of data efficiently.
    *   The module must support multi-company environments.

**3. Functional Requirements**

## Phase 1: PR Consolidation

**3.1. PR Consolidation (Phase 1)**

*   **FR-PR-001:** The system shall allow users to create a consolidation session with a date range and optional filters.
*   **FR-PR-002:** The system shall automatically collect all approved PRs within the specified date range and filters.
*   **FR-PR-003:** The system shall aggregate quantities by product, creating consolidated lines.
*   **FR-PR-004:** The system shall allow users to review and adjust consolidated lines.
*   **FR-PR-005:** The system shall allow users to confirm the consolidation, making it ready for inventory validation.

**Implementation Status (April 2025):**

*   **FR-INV-001 to FR-INV-006:** These requirements have been implemented with the `validate.inventory.wizard`. The wizard displays all consolidated lines with their current stock, required quantity, and available quantity. Users can filter to view only critical items, and the system calculates the quantity to purchase. After validation, users can proceed to PO creation.

*   **FR-INV-007:** The system is set up to handle inventory exceptions, but the approval workflow is still being refined. The system can request manager approval for critical inventory issues, but the notification system is still being tested.

*   **FR-INV-008:** The system can update safety stock levels based on validation, but the calculation logic is still being refined.

## Phase 2: Inventory Validation

**3.2. Inventory Validation (Phase 2)**

*   **FR-INV-001:** The system shall check current inventory levels for all products in a confirmed consolidation.
*   **FR-INV-002:** The system shall compare demand (from consolidated lines) with available stock.
*   **FR-INV-003:** The system shall categorize inventory status as sufficient, partial, insufficient, or stockout.
*   **FR-INV-004:** The system shall calculate the quantity to purchase based on the difference between required quantity and available quantity.
*   **FR-INV-005:** The system shall allow users to review and adjust inventory validation decisions.
*   **FR-INV-006:** The system shall allow users to confirm inventory validation, making it ready for PO creation.
*   **FR-INV-007:** The system shall handle inventory exceptions, requiring approval for critical shortages.
*   **FR-INV-008:** The system shall update safety stock levels based on validation decisions.

**Implementation Status (April 2025):**

*   **FR-INV-001 to FR-INV-006:** These requirements have been implemented with the `validate.inventory.wizard`. The wizard displays all consolidated lines with their current stock, required quantity, and available quantity. Users can filter to view only critical items, and the system calculates the quantity to purchase. After validation, users can proceed to PO creation.

*   **FR-INV-007:** The system is set up to handle inventory exceptions, but the approval workflow is still being refined. The system can request manager approval for critical inventory issues, but the notification system is still being tested.

*   **FR-INV-008:** The system can update safety stock levels based on validation, but the calculation logic is still being refined.

## Phase 3: Purchase Order Creation

**3.3. Purchase Order Creation (Phase 3)**

*   **FR-PO-001: Create Purchase Orders from Validated Lines**

    *   **Source:** High-Level Req. Phase 3.1
    *   **Priority:** High
    *   **Description:** The system shall allow users to create purchase orders from validated and approved consolidation lines, grouping products by vendor and applying appropriate pricing.
    *   **User Interface (UI) Description:**
        *   A button "Create Purchase Orders" shall be visible on the consolidation session form when state is 'po_creation'
        *   Clicking the button opens the `create.po.wizard` that allows:
            *   Selection of vendor for the PO
            *   Setting the order date
            *   Adding optional notes
            *   Selecting blanket orders (if available)
            *   Reviewing and adjusting line quantities
        *   The wizard displays a list of products with their quantities to purchase, prices, and other relevant information
    *   **Business Rules/Logic:**
        *   Only lines with `quantity_to_purchase > 0` are included in the PO
        *   Products are grouped by vendor if multiple vendors are involved
        *   Standard prices from the product or vendor pricelist are used
        *   The PO is linked to the consolidation session via `consolidation_id`
        *   If a blanket order is selected:
            *   Use blanket order pricing
            *   Validate quantities against blanket order limits
            *   Link the PO to the blanket order
    *   **Data Handling:**
        *   Input: Selected vendor, order date, notes, blanket order (optional), and line quantities
        *   Processing: 
            *   Create PO with vendor and date information
            *   Create PO lines with quantities and prices
            *   Apply blanket order pricing if selected
            *   Link PO to consolidation session
        *   Output: New `purchase.order` record with corresponding `purchase.order.line` records
    *   **Preconditions:**
        *   The consolidation session exists and its state is 'po_creation'
        *   At least one line has a positive `quantity_to_purchase`
        *   User has permission to create purchase orders
    *   **Postconditions:**
        *   A new purchase order is created with the specified vendor and lines
        *   The PO is linked to the consolidation session
        *   The session's state is updated to 'po_created'
        *   PO creation date and creator are recorded
    *   **Error Handling/Alternative Flows:**
        *   Handle cases where no validated lines exist for the selected vendor
        *   Validate blanket order quantities and dates
        *   Provide option to mark lines as "No PO Needed" if required

*   **FR-PO-002: Group Products by Vendor**

    *   **Source:** High-Level Req. Phase 3.2
    *   **Priority:** High
    *   **Description:** The system shall group products by vendor when creating purchase orders from consolidation lines.
    *   **User Interface (UI) Description:**
        *   The PO creation wizard shall:
            *   Show products grouped by vendor
            *   Allow selecting a specific vendor
            *   Display vendor-specific information
        *   The consolidation session form shall show:
            *   Number of POs created per vendor
            *   Total amount per vendor
    *   **Business Rules/Logic:**
        *   Products must be assigned to vendors before PO creation
        *   Create separate POs for each vendor
        *   Maintain proper links between POs and consolidation
        *   Handle vendor-specific requirements and pricing
    *   **Data Handling:**
        *   Input: Product-vendor assignments from consolidation lines
        *   Processing: Group products by vendor and create POs
        *   Output: Set of linked POs, one per vendor
    *   **Preconditions:**
        *   Products are assigned to vendors
        *   User has permission to create multiple POs
    *   **Postconditions:**
        *   Multiple POs are created as needed
        *   All POs are properly linked to the consolidation
        *   Vendor-specific information is maintained

*   **FR-PO-003: Apply Pricing Rules**

    *   **Source:** High-Level Req. Phase 3.3
    *   **Priority:** High
    *   **Description:** The system shall apply appropriate pricing rules when creating purchase orders.
    *   **User Interface (UI) Description:**
        *   The PO creation wizard shall show:
            *   Standard product prices
            *   Vendor-specific prices
            *   Blanket order prices (if available)
        *   Allow manual price adjustments if needed
    *   **Business Rules/Logic:**
        *   First check for blanket order prices
        *   If no blanket order, use vendor-specific prices
        *   Fall back to product standard price
        *   Allow manual price adjustments with proper authorization
    *   **Data Handling:**
        *   Input: Product and vendor information
        *   Processing: Apply pricing rules in order of priority
        *   Output: Final prices for PO lines
    *   **Preconditions:**
        *   Product and vendor information is available
        *   Pricing rules are properly configured
    *   **Postconditions:**
        *   Correct prices are applied to PO lines
        *   Price history is maintained

*   **FR-PO-004: Track PO Creation Status**

    *   **Source:** High-Level Req. Phase 3.4
    *   **Priority:** Medium
    *   **Description:** The system shall maintain the status of purchase order creation within the consolidation session.
    *   **User Interface (UI) Description:**
        *   The consolidation session form view shall show:
            *   Number of POs created
            *   Status of each PO
            *   Links to created POs
            *   PO creation date and creator
        *   A dedicated tab for PO tracking
    *   **Business Rules/Logic:**
        *   Track PO creation status per line
        *   Maintain links between POs and consolidation lines
        *   Update session state based on PO status
        *   Record PO creation history
    *   **Data Handling:**
        *   Input: PO creation events
        *   Processing: Update tracking information
        *   Output: Updated status and links
    *   **Preconditions:**
        *   POs are being created
        *   Tracking fields are properly configured
    *   **Postconditions:**
        *   PO status is accurately tracked
        *   Links between POs and consolidation are maintained
        *   Creation history is recorded

*   **FR-PO-005: Handle Multiple Vendors**

    *   **Source:** High-Level Req. Phase 3.5
    *   **Priority:** Medium
    *   **Description:** The system shall support creating multiple purchase orders for different vendors.
    *   **User Interface (UI) Description:**
        *   The PO creation wizard shall:
            *   Show products grouped by vendor
            *   Allow creating multiple POs in one action
            *   Provide a summary of POs to be created
        *   Users can review and modify vendor assignments
    *   **Business Rules/Logic:**
        *   Create separate POs for each vendor
        *   Maintain proper links between POs and consolidation
        *   Handle vendor-specific requirements
        *   Support different pricing rules per vendor
    *   **Data Handling:**
        *   Input: Product-vendor assignments
        *   Processing: Create multiple POs as needed
        *   Output: Set of linked POs
    *   **Preconditions:**
        *   Products are assigned to vendors
        *   User has permission to create multiple POs
    *   **Postconditions:**
        *   Multiple POs are created as needed
        *   All POs are properly linked to the consolidation
        *   Vendor-specific information is maintained

*   **FR-PO-006: Handle Blanket Orders**

    *   **Source:** Business Requirements Document
    *   **Priority:** High
    *   **Description:** The system must check for blanket orders when creating purchase orders from validated consolidation lines.
    *   **User Interface:**
        *   The PO creation wizard must display:
            *   Available blanket orders for the vendor (if any)
            *   Standard PO creation options (if no blanket orders)
        *   For blanket orders, show:
            *   Reference number
            *   Validity period
            *   Product-specific pricing
            *   Minimum and maximum quantities
    *   **Business Rules:**
        1. Blanket Order Check:
            *   System first checks for active blanket orders for the vendor
            *   Only considers orders within their validity period
            *   If no valid blanket orders exist, proceed with standard PO creation

        2. When Blanket Orders Exist:
            *   Use blanket order pricing and terms
            *   Validate quantities against blanket order limits
            *   Create PO with reference to blanket order
            *   Track blanket order usage

        3. When No Blanket Orders:
            *   Proceed with standard PO creation process
            *   Use vendor's standard pricing
            *   Create single PO for all products
    *   **Data Handling:**
        1. Input:
            *   Consolidation line data
            *   Vendor information
            *   Required quantities
            *   Blanket order selection (if available)

        2. Processing:
            *   Check for active blanket orders
            *   If found: Apply blanket order rules
            *   If not found: Use standard PO creation
            *   Update blanket order usage

        3. Output:
            *   Created purchase order(s)
            *   Updated consolidation session status
            *   Updated blanket order usage
            *   Activity logs for tracking
    *   **Preconditions:**
        *   Valid consolidation session with approved lines
        *   Vendor information is available
        *   Blanket orders are properly configured (if used)
    *   **Postconditions:**
        *   PO is created with correct pricing
        *   Blanket order usage is updated
        *   All references are properly maintained

*   **FR-PO-007: Blanket Order Management**

    *   **Source:** Business Requirements Document
    *   **Priority:** High
    *   **Description:** The system must provide functionality to manage blanket orders for vendors.

    *   **User Interface:**
        *   Blanket order form view with:
            *   Basic information (reference, vendor, dates)
            *   Line items with products and pricing
            *   Status tracking
            *   History and notes

    *   **Business Rules:**
        1. Blanket Order Creation:
            *   Must specify vendor and validity period
            *   Must include at least one product line
            *   Must define minimum and maximum quantities
            *   Must specify unit prices

        2. Status Management:
            *   Draft: Initial state for new blanket orders
            *   Active: Available for PO creation
            *   Expired: Past end date
            *   Cancelled: Manually cancelled

        3. Quantity Management:
            *   Track remaining quantities against maximum
            *   Prevent exceeding maximum quantities
            *   Allow partial usage across multiple POs

        4. Pricing Rules:
            *   Fixed prices for specified products
            *   Price validity tied to blanket order period
            *   Support for different UoM conversions

    *   **Data Handling:**
        1. Input:
            *   Vendor information
            *   Product details
            *   Pricing information
            *   Quantity constraints
            *   Validity period

        2. Processing:
            *   Validate all required fields
            *   Check for overlapping periods
            *   Verify vendor status
            *   Calculate total values

        3. Output:
            *   Created blanket order record
            *   Generated reference number
            *   Status updates
            *   Activity logs

    *   **Preconditions:**
        *   Valid vendor with supplier status
        *   Products must exist in system
        *   No overlapping blanket orders for same products

    *   **Postconditions:**
        *   Blanket order created in system
        *   Available for PO creation
        *   Properly tracked in vendor history

    *   **Error Handling:**
        1. Validation Errors:
            *   Missing required fields
            *   Invalid dates
            *   Invalid quantities
            *   Invalid prices

        2. Business Rule Violations:
            *   Overlapping periods
            *   Duplicate products
            *   Invalid vendor status

        3. System Errors:
            *   Database constraints
            *   Reference generation failures
            *   Status transition errors

*   **Implementation Status (April 2025):**

    *   **FR-PO-006: Handle Blanket Orders**
        *   **Current Status:** Not Implemented
        *   **Gaps:**
            1. Blanket Order Integration:
                *   No model for blanket orders exists
                *   No logic to check for blanket orders during PO creation
                *   Missing UI elements in PO creation wizard

            2. PO Creation Logic:
                *   Current implementation creates POs without checking blanket orders
                *   No handling of blanket order pricing
                *   No validation against blanket order quantities

            3. Data Model:
                *   Missing fields to link POs to blanket orders
                *   No tracking of blanket order usage
                *   No history of blanket order references

        *   **Next Steps:**
            1. Create blanket order models (FR-PO-007)
            2. Update PO creation wizard to check for blanket orders
            3. Implement blanket order pricing logic
            4. Add UI elements for blanket order selection
            5. Update PO model to reference blanket orders

    *   **FR-PO-007: Blanket Order Management**
        *   **Current Status:** Not Implemented
        *   **Gaps:**
            1. Data Model:
                *   No blanket order model exists
                *   Missing fields for tracking validity and quantities
                *   No relationship to vendors and products

            2. Business Logic:
                *   No status management
                *   No quantity tracking
                *   No pricing rules implementation

            3. User Interface:
                *   No forms or views for blanket orders
                *   Missing workflow buttons
                *   No reporting or tracking features

        *   **Next Steps:**
            1. Create blanket order models and fields
            2. Implement status management
            3. Add quantity tracking logic
            4. Create user interface elements
            5. Implement validation rules

## Phase 4: Fulfillment Tracking

### FR-FT-001: PR Fulfillment Plan Model
- **Source:** High-Level Req. Phase 4.1
- **Priority:** High
- **Description:**
  The system shall implement a PR Fulfillment Plan model to track the fulfillment of each purchase request line, including links to fulfillment actions such as purchase orders and internal transfers.
- **User Interface (UI) Description:**
  - A new model `scm.pr.fulfillment.plan` is accessible from the PR and PR line forms (as a tab or stat button).
  - The fulfillment plan form shows:
    - Linked PR line(s)
    - Fulfillment method (PO, internal transfer, etc.)
    - Status (pending, in progress, fulfilled, exception)
    - Linked PO(s) or transfer(s)
    - Quantities planned, fulfilled, remaining
    - Timeline and notes
- **Business Rules/Logic:**
  - Each PR line can have one or more fulfillment plan records.
  - Each fulfillment plan must specify a fulfillment method and link to the relevant action (PO, transfer, etc.).
  - Status is computed based on fulfillment progress.
- **Data Handling:**
  - Input: PR line, fulfillment method, quantities, linked actions.
  - Processing: Create/update fulfillment plan records as actions are taken.
  - Output: Updated fulfillment plan records, status, and links.
- **Preconditions:**
  - PR lines exist and are ready for fulfillment.
  - User has permission to create/update fulfillment plans.
- **Postconditions:**
  - Fulfillment plan records are created and linked to PR lines and actions.
  - Status is updated as fulfillment progresses.
- **Error Handling/Alternative Flows:**
  - If a fulfillment plan cannot be created (e.g., missing data), display a validation error.
  - If a fulfillment action fails (e.g., PO cancelled), update the plan status and notify the user.

### FR-FT-002: Integration with PO Receipts
- **Source:** High-Level Req. Phase 4.2
- **Priority:** High
- **Description:**
  The system shall automatically update the fulfillment status of PR lines and fulfillment plans based on the receipt of goods in related purchase orders.
- **User Interface (UI) Description:**
  - When a PO receipt is validated, the related PR fulfillment plan and PR line status are updated.
  - The PR and fulfillment plan forms show received quantities and fulfillment progress.
- **Business Rules/Logic:**
  - When a PO receipt is validated, update the linked fulfillment plan and PR line with the received quantity.
  - If the received quantity fulfills the plan, mark it as fulfilled; otherwise, update as partially fulfilled.
- **Data Handling:**
  - Input: PO receipt validation event.
  - Processing: Update fulfillment plan and PR line status and quantities.
  - Output: Updated status and quantities on fulfillment plan and PR line.
- **Preconditions:**
  - PO is linked to a fulfillment plan and PR line.
  - PO receipt is validated.
- **Postconditions:**
  - Fulfillment plan and PR line status/quantities are updated.
- **Error Handling/Alternative Flows:**
  - If the PO is not linked to a fulfillment plan, log a warning and skip update.
  - If received quantity exceeds planned, flag as exception.

### FR-FT-003: Internal Transfer Suggestions
- **Source:** High-Level Req. Phase 4.3
- **Priority:** Medium
- **Description:**
  The system shall suggest internal transfers for PR lines that can be fulfilled from available stock in other locations/warehouses.
- **User Interface (UI) Description:**
  - In the fulfillment plan or PR line view, a button or suggestion appears if internal transfer is possible.
  - A wizard allows the user to review, accept, or reject the suggested transfer.
  - Accepted transfers create a stock transfer order linked to the fulfillment plan.
- **Business Rules/Logic:**
  - The system checks available stock in other locations/warehouses.
  - If sufficient stock exists, suggest an internal transfer.
  - User can accept (creates transfer) or reject (removes suggestion).
- **Data Handling:**
  - Input: PR line, stock levels in all locations.
  - Processing: Suggest transfer if possible, create transfer order if accepted.
  - Output: Internal transfer order, updated fulfillment plan.
- **Preconditions:**
  - PR line exists and is not yet fulfilled.
  - Stock is available in other locations.
- **Postconditions:**
  - Internal transfer order is created and linked to fulfillment plan if accepted.
  - PR line and fulfillment plan status are updated.
- **Error Handling/Alternative Flows:**
  - If stock is no longer available when user accepts, show error and do not create transfer.
  - If user rejects, log the decision.

### FR-FT-004: PR Status Updates
- **Source:** High-Level Req. Phase 4.4
- **Priority:** High
- **Description:**
  The system shall automatically update the status of each purchase request (PR) and PR line based on fulfillment progress (e.g., pending, in progress, partially fulfilled, fulfilled).
- **User Interface (UI) Description:**
  - PR and PR line forms and list views display current fulfillment status.
  - Status is updated in real time as fulfillment actions are completed.
- **Business Rules/Logic:**
  - Status is computed based on linked fulfillment plans and their progress.
  - Statuses include: pending, in progress, partially fulfilled, fulfilled, exception.
- **Data Handling:**
  - Input: Fulfillment plan and action status.
  - Processing: Compute and update PR/PR line status.
  - Output: Updated status fields on PR and PR line.
- **Preconditions:**
  - PR and PR lines exist and are linked to fulfillment plans.
- **Postconditions:**
  - Status fields on PR and PR lines reflect current fulfillment progress.
- **Error Handling/Alternative Flows:**
  - If fulfillment plan is deleted or unlinked, recalculate status.
  - If conflicting statuses exist (e.g., one plan fulfilled, one pending), show as partially fulfilled.

## Phase 5: Change Management & Optimization

### FR-CM-001: Change Log Implementation
- **Source:** High-Level Req. Phase 5.1
- **Priority:** High
- **Description:**
  The system shall maintain a change log for key actions and modifications related to PRs, POs, fulfillment plans, and inventory transfers.
- **User Interface (UI) Description:**
  - A "Change Log" tab or stat button is available on PR, PO, and fulfillment plan forms.
  - The change log view lists:
    - Date/time of change
    - User who made the change
    - Action type (create, update, delete, status change, etc.)
    - Affected fields and their old/new values
    - Related record links
- **Business Rules/Logic:**
  - All create, update, and delete actions on tracked models are logged.
  - Only users with appropriate permissions can view the full change log.
  - The log is immutable (cannot be edited or deleted).
- **Data Handling:**
  - Input: Model changes (PR, PO, fulfillment plan, inventory transfer)
  - Processing: Automatically create a change log entry for each tracked action.
  - Output: Change log records linked to the relevant business objects.
- **Preconditions:**
  - User performs an action on a tracked model.
- **Postconditions:**
  - A new change log entry is created and visible in the UI.
- **Error Handling/Alternative Flows:**
  - If logging fails, display a warning and continue the main transaction (do not block business process).

### FR-CM-002: Change Detection and Impact Assessment
- **Source:** High-Level Req. Phase 5.2
- **Priority:** High
- **Description:**
  The system shall detect changes to PRs, POs, fulfillment plans, and inventory transfers, and assess the impact of each change on related records and processes.
- **User Interface (UI) Description:**
  - When a significant change is detected (e.g., PR quantity change, PO cancellation), a notification or banner is shown on affected records.
  - An "Impact Analysis" button or section displays affected downstream records (e.g., which POs or fulfillment plans are impacted by a PR change).
- **Business Rules/Logic:**
  - The system tracks dependencies between PRs, POs, fulfillment plans, and inventory transfers.
  - When a change occurs, the system identifies and flags all related records that may be affected.
- **Data Handling:**
  - Input: Change events on tracked models.
  - Processing: Analyze dependencies and flag affected records.
  - Output: Impact flags, notifications, and analysis reports.
- **Preconditions:**
  - A change is made to a tracked record.
- **Postconditions:**
  - All affected records are flagged and visible to users.
- **Error Handling/Alternative Flows:**
  - If dependency analysis fails, log the error and notify the system administrator.

### FR-CM-003: Change Resolution and Notification
- **Source:** High-Level Req. Phase 5.3
- **Priority:** High
- **Description:**
  The system shall provide mechanisms for users to resolve detected changes (e.g., approve, reject, or modify changes) and send notifications to relevant users when key events occur.
- **User Interface (UI) Description:**
  - When a change is detected, users see options to approve, reject, or modify the change.
  - Notification preferences are configurable per user or role.
  - Notifications are sent via Odoo's chatter, email, or in-app alerts.
- **Business Rules/Logic:**
  - Only authorized users can resolve changes.
  - All resolutions are logged in the change log.
  - Notifications are sent according to user preferences and business rules.
- **Data Handling:**
  - Input: User actions to resolve changes; notification triggers.
  - Processing: Update record status, log resolution, send notifications.
  - Output: Updated records, change log entries, sent notifications.
- **Preconditions:**
  - A change requiring resolution is detected.
- **Postconditions:**
  - The change is resolved and all relevant users are notified.
- **Error Handling/Alternative Flows:**
  - If notification delivery fails, log the error and retry or escalate.

### FR-CM-004: Performance Optimizations
- **Source:** High-Level Req. Phase 5.4
- **Priority:** Medium
- **Description:**
  The system shall be optimized to handle large volumes of PRs, POs, and fulfillment plans without significant performance degradation.
- **User Interface (UI) Description:**
  - No direct UI, but users experience fast response times even with large datasets.
- **Business Rules/Logic:**
  - Use batch processing for bulk operations.
  - Optimize database queries and use appropriate indexes.
  - Archive or purge old records as needed.
- **Data Handling:**
  - Input: Large datasets and batch operations.
  - Processing: Efficient queries, batch jobs, and background processing.
  - Output: Fast, reliable system performance.
- **Preconditions:**
  - Large volume of data or batch operation initiated.
- **Postconditions:**
  - Operation completes within acceptable time limits.
- **Error Handling/Alternative Flows:**
  - If an operation exceeds time limits, log and notify the administrator; provide user feedback.

### FR-CM-005: Advanced Reporting
- **Source:** High-Level Req. Phase 5.5
- **Priority:** Medium
- **Description:**
  The system shall provide advanced reporting capabilities for PR fulfillment, PO performance, inventory movements, and change history.
- **User Interface (UI) Description:**
  - Reports are accessible from a dedicated menu or dashboard.
  - Users can filter reports by date, product, vendor, status, and other criteria.
  - Reports can be exported to Excel, PDF, or other formats.
- **Business Rules/Logic:**
  - Only users with reporting permissions can access advanced reports.
  - Reports reflect real-time data and are updated as records change.
- **Data Handling:**
  - Input: User-selected filters and criteria.
  - Processing: Generate reports using efficient queries and aggregations.
  - Output: Displayed and exportable reports.
- **Preconditions:**
  - User has access to reporting features.
- **Postconditions:**
  - Reports are generated and available for review/export.
- **Error Handling/Alternative Flows:**
  - If report generation fails, display an error and allow the user to retry.

---

#### **FR-SCM-001: Create New Consolidation Session**

*   **Source:** High-Level Req. Phase 1.1
*   **Priority:** High
*   **Description:** The system shall allow authorized users to create a new Purchase Request Consolidation Session, defining the scope and parameters for collecting PRs.
*   **User Interface (UI) Description:**
    *   Accessible via a "Create" button in the "PR Consolidation Sessions" list view.
    *   A form view shall be presented containing the following input fields:
        *   `name` (Reference): Character field, potentially auto-generated on save (e.g., sequence `scm.pr.consolidation`) or user-input.
        *   `date_from`: Mandatory Date field, using Odoo's date picker widget.
        *   `date_to`: Mandatory Date field, using Odoo's date picker widget.
        *   `warehouse_id`: Mandatory Many2one selection field referencing `stock.warehouse`.
        *   `department_ids`: Optional Many2many selection field referencing `hr.department`, using a tags widget.
        *   `category_ids`: Optional Many2many selection field referencing `product.category`, using a tags widget.
        *   `notes`: Optional Text field.
        *   `user_id`: Many2one field referencing `res.users`, defaulting to the current user, read-only after creation.
        *   `company_id`: Many2one field referencing `res.company`, defaulting to the current user's company, read-only after creation.
    *   Standard "Save" and "Discard" buttons shall be present.
    *   The initial `state` displayed (e.g., via status bar widget) shall be 'Draft'.
*   **Business Rules/Logic:**
    *   `date_to` must be greater than or equal to `date_from`. Validation shall prevent saving if this condition is not met.
    *   The `state` shall default to `'draft'`.
    *   `user_id` and `company_id` default to the context user/company.
*   **Data Handling:**
    *   Input: User-provided dates, warehouse, optional filters, notes.
    *   Processing: Validate date range.
    *   Output: A new record is created in the `scm_pr_consolidation_session` table with the provided data and default values. Corresponding entries in relation tables (`scm_consolidation_department_rel`, `scm_consolidation_category_rel`) are created if filters are selected.
*   **Preconditions:**
    *   User has create permissions for the `scm.pr.consolidation.session` model.
    *   Warehouses, Departments, Categories exist for selection.
*   **Postconditions:**
    *   A new `scm_pr_consolidation_session` record exists in the database with `state = 'draft'`.
    *   The user is typically returned to the newly created record's form view or the list view.
*   **Error Handling/Alternative Flows:**
    *   If `date_to < date_from`, display a validation error and prevent saving.
    *   If mandatory fields (`date_from`, `date_to`, `warehouse_id`) are empty, display standard Odoo validation errors.

---

#### **FR-SCM-002: Collect and Consolidate Approved Purchase Requests**

*   **Source:** High-Level Req. Phase 1.1, 1.2
*   **Priority:** High
*   **Description:** Upon user initiation from a 'Draft' session, the system shall search for approved Purchase Requests matching the session's criteria (date range, warehouse context, optional filters), aggregate the quantities for identical products across selected PR lines, and populate the session with consolidated line items.
*   **User Interface (UI) Description:**
    *   A button (e.g., "Start Consolidation") shall be visible and enabled on the `scm_pr_consolidation_session` form view when the record `state` is 'Draft'.
    *   Clicking the button initiates the process. A visual indicator (e.g., spinner, message) may display during processing.
    *   Upon successful completion, the `state` in the status bar changes to 'In Progress'. The `consolidated_line_ids` list/tree view (likely within a notebook tab) is populated. A stat button or `purchase_request_ids` tab shows linked PRs.
    *   If no matching PRs are found, a user-friendly notification (e.g., Odoo warning banner) shall be displayed, and the state shall remain 'Draft'.
*   **Business Rules/Logic:**
    *   The system shall search the `purchase_request` model.
    *   Search criteria: `state = 'approved'`, `date_start >= session.date_from`, `date_start <= session.date_to`.
    *   If `session.department_ids` is set, filter PRs where `department_id` is in the selected list.
    *   If `session.category_ids` is set, filter PRs where at least one `line_ids.product_id.categ_id` is in the selected list.
    *   Only lines (`purchase_request_line`) linked to the selected PRs and having a `product_id` are considered.
    *   Lines are grouped by `product_id`.
    *   Within each product group, the `product_qty` is summed. (UoM conversion should be handled if lines have different UoMs for the same product, converting to the product's standard UoM).
    *   The earliest `date_required` among the lines for each product group is determined.
    *   A new `scm_consolidated_pr_line` record is created for each product group.
*   **Data Handling:**
    *   Input: `scm_pr_consolidation_session` record ID, `date_from`, `date_to`, `department_ids`, `category_ids`.
    *   Processing: Query `purchase_request` and `purchase_request_line`. Perform in-memory aggregation by product.
    *   Output:
        *   Create new records in `scm_consolidated_pr_line` with calculated `total_quantity`, `earliest_date_required`, linked `product_id`, `