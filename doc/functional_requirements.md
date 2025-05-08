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

**3.1. PR Consolidation (Phase 1)**

*   **FR-PR-001:** The system shall allow users to create a consolidation session with a date range and optional filters.
*   **FR-PR-002:** The system shall automatically collect all approved PRs within the specified date range and filters.
*   **FR-PR-003:** The system shall aggregate quantities by product, creating consolidated lines.
*   **FR-PR-004:** The system shall allow users to review and adjust consolidated lines.
*   **FR-PR-005:** The system shall allow users to confirm the consolidation, making it ready for inventory validation.

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

**3.4. Change Management Process (Phase 4)**

*   **FR-CM-001: Detect Changes in PRs**

    *   **Source:** High-Level Req. Phase 4.1
    *   **Priority:** High
    *   **Description:** The system shall automatically detect changes in Purchase Requests that affect the current consolidation session.
    *   **User Interface (UI) Description:**
        *   A dedicated tab "Change Log" in the consolidation session form view
        *   Change log entries showing:
            *   Type of change (PR Added/Modified/Deleted)
            *   Date and time of change
            *   User who made the change
            *   Impact assessment
            *   Status of the change
        *   Filter options for change types and status
    *   **Business Rules/Logic:**
        *   Monitor PRs linked to the consolidation session
        *   Detect changes in:
            *   PR quantities
            *   PR status
            *   PR dates
            *   PR line additions/deletions
        *   Calculate impact on consolidation totals
        *   Update affected consolidated lines
    *   **Data Handling:**
        *   Input: Changes in PR data
        *   Processing: 
            *   Detect changes
            *   Calculate impact
            *   Create change log entry
            *   Update consolidation data
        *   Output: Updated consolidation data and change log entries
    *   **Preconditions:**
        *   Consolidation session exists
        *   PRs are linked to the session
        *   User has permission to view changes
    *   **Postconditions:**
        *   Change is logged
        *   Consolidation data is updated
        *   Impact is assessed
        *   Team is notified

*   **FR-CM-002: Detect Changes in Inventory**

    *   **Source:** High-Level Req. Phase 4.2
    *   **Priority:** High
    *   **Description:** The system shall monitor and detect changes in inventory levels that affect the current consolidation session.
    *   **User Interface (UI) Description:**
        *   Change log entries for inventory changes
        *   Visual indicators for critical stock changes
        *   Impact assessment view
        *   Options to revalidate inventory
    *   **Business Rules/Logic:**
        *   Monitor stock levels for products in consolidation
        *   Detect changes in:
            *   Available quantity
            *   Reserved quantity
            *   Incoming quantity
        *   Trigger revalidation if impact is significant
        *   Update inventory status of affected lines
    *   **Data Handling:**
        *   Input: Stock movement data
        *   Processing:
            *   Compare new stock levels
            *   Calculate impact
            *   Create change log
            *   Update inventory status
        *   Output: Updated inventory data and change log
    *   **Preconditions:**
        *   Consolidation session exists
        *   Products have stock information
        *   User has permission to view inventory
    *   **Postconditions:**
        *   Change is logged
        *   Inventory status is updated
        *   Impact is assessed
        *   Team is notified

*   **FR-CM-003: Detect Changes in Purchase Orders**

    *   **Source:** High-Level Req. Phase 4.3
    *   **Priority:** High
    *   **Description:** The system shall monitor changes in Purchase Orders created from the consolidation session.
    *   **User Interface (UI) Description:**
        *   Change log entries for PO changes
        *   PO status tracking
        *   Impact on PR fulfillment
        *   Options to update fulfillment plans
    *   **Business Rules/Logic:**
        *   Monitor POs linked to consolidation
        *   Detect changes in:
            *   PO status
            *   PO quantities
            *   Delivery dates
            *   PO cancellations
        *   Update PR fulfillment plans
        *   Recalculate delivery timelines
    *   **Data Handling:**
        *   Input: PO change data
        *   Processing:
            *   Detect PO changes
            *   Update fulfillment plans
            *   Create change log
            *   Recalculate timelines
        *   Output: Updated fulfillment data and change log
    *   **Preconditions:**
        *   Consolidation session exists
        *   POs are created from session
        *   User has permission to view POs
    *   **Postconditions:**
        *   Change is logged
        *   Fulfillment plans are updated
        *   Impact is assessed
        *   Team is notified

*   **FR-CM-004: Impact Assessment**

    *   **Source:** High-Level Req. Phase 4.4
    *   **Priority:** High
    *   **Description:** The system shall assess and communicate the impact of changes on the consolidation session and related processes.
    *   **User Interface (UI) Description:**
        *   Impact assessment dashboard
        *   Visual indicators for impact severity
        *   Detailed impact reports
        *   Action recommendation panel
    *   **Business Rules/Logic:**
        *   Calculate impact on:
            *   Total quantities
            *   Delivery timelines
            *   Purchase costs
            *   PR fulfillment
        *   Categorize impact severity
        *   Generate action recommendations
        *   Prioritize required actions
    *   **Data Handling:**
        *   Input: Change data and current state
        *   Processing:
            *   Calculate impact metrics
            *   Generate recommendations
            *   Update impact assessment
            *   Create notifications
        *   Output: Impact assessment and recommendations
    *   **Preconditions:**
        *   Change is detected
        *   Current state is known
        *   User has permission to view impact
    *   **Postconditions:**
        *   Impact is assessed
        *   Recommendations are generated
        *   Team is notified
        *   Action plan is created

*   **FR-CM-005: Change Resolution**

    *   **Source:** High-Level Req. Phase 4.5
    *   **Priority:** High
    *   **Description:** The system shall provide tools and workflows for resolving detected changes and updating the consolidation session accordingly.
    *   **User Interface (UI) Description:**
        *   Change resolution wizard
        *   Action tracking interface
        *   Resolution status updates
        *   History of resolutions
    *   **Business Rules/Logic:**
        *   Guide users through resolution steps
        *   Track resolution progress
        *   Update consolidation data
        *   Maintain resolution history
        *   Close change records when resolved
    *   **Data Handling:**
        *   Input: Resolution actions
        *   Processing:
            *   Apply changes
            *   Update status
            *   Record actions
            *   Notify stakeholders
        *   Output: Updated consolidation data and resolution records
    *   **Preconditions:**
        *   Change is detected
        *   Impact is assessed
        *   User has permission to resolve changes
    *   **Postconditions:**
        *   Changes are resolved
        *   Consolidation is updated
        *   Resolution is documented
        *   Status is updated

*   **FR-CM-006: Change Notification System**

    *   **Source:** High-Level Req. Phase 4.6
    *   **Priority:** Medium
    *   **Description:** The system shall notify relevant stakeholders about detected changes and required actions.
    *   **User Interface (UI) Description:**
        *   Notification center
        *   Email notification settings
        *   In-app notification panel
        *   Notification history
    *   **Business Rules/Logic:**
        *   Define notification rules
        *   Determine notification recipients
        *   Set notification priorities
        *   Track notification status
        *   Allow notification preferences
    *   **Data Handling:**
        *   Input: Change data and user preferences
        *   Processing:
            *   Generate notifications
            *   Send to recipients
            *   Track delivery
            *   Record responses
        *   Output: Notifications and delivery status
    *   **Preconditions:**
        *   Change is detected
        *   Impact is assessed
        *   Notification rules are configured
    *   **Postconditions:**
        *   Notifications are sent
        *   Delivery is tracked
        *   Responses are recorded
        *   Status is updated

*   **FR-CM-007: Change History and Reporting**

    *   **Source:** High-Level Req. Phase 4.7
    *   **Priority:** Medium
    *   **Description:** The system shall maintain a comprehensive history of changes and provide reporting capabilities.
    *   **User Interface (UI) Description:**
        *   Change history view
        *   Reporting dashboard
        *   Export options
        *   Filter and search capabilities
    *   **Business Rules/Logic:**
        *   Record all changes
        *   Track resolution status
        *   Calculate change metrics
        *   Generate reports
        *   Support data export
    *   **Data Handling:**
        *   Input: Change and resolution data
        *   Processing:
            *   Aggregate history
            *   Calculate metrics
            *   Generate reports
            *   Prepare exports
        *   Output: History records and reports
    *   **Preconditions:**
        *   Changes are recorded
        *   User has permission to view history
    *   **Postconditions:**
        *   History is maintained
        *   Reports are generated
        *   Data is available for export
        *   Metrics are calculated

**Implementation Status (April 2025):**

*   **FR-CM-001 to FR-CM-003:** These requirements have been implemented with the change detection system. The system can detect changes in PRs, inventory levels, and POs, and create appropriate change log entries.

*   **FR-CM-004:** The impact assessment functionality is implemented but needs refinement in the recommendation engine and impact calculation algorithms.

*   **FR-CM-005:** The change resolution workflow is implemented with basic functionality. Additional features for complex resolution scenarios are planned.

*   **FR-CM-006:** The notification system is implemented with basic email and in-app notifications. Advanced notification rules and preferences are still being developed.

*   **FR-CM-007:** Basic change history and reporting are implemented. Advanced reporting features and metrics are planned for future releases.

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
        *   Create new records in `scm_consolidated_pr_line` with calculated `total_quantity`, `earliest_date_required`, linked `product_id`, `product_uom_id` (product's default purchase UoM), and `consolidation_id`. Set line `state` to `'draft'` (or similar initial state).
        *   Create entries in `scm_pr_consolidation_request_rel` linking the session to found `purchase_request` records.
        *   Create entries in the M2M relation table linking `scm_consolidated_pr_line` to source `purchase_request_line` records.
        *   Update the `scm_pr_consolidation_session` record's `state` to `'in_progress'`.
*   **Preconditions:**
    *   The `scm_pr_consolidation_session` record exists and its `state` is 'Draft'.
    *   User has permission to execute the action/method.
    *   `purchase_request` module is installed and contains approved PRs.
*   **Postconditions:**
    *   The `scm_pr_consolidation_session` record's `state` is updated to 'In Progress'.
    *   `scm_consolidated_pr_line` records are created and linked to the session.
    *   The session is linked to the source `purchase_request` records.
    *   Consolidated lines are linked to source `purchase_request_line` records.
    *   If no PRs found, state remains 'Draft' and a message is shown.
*   **Error Handling/Alternative Flows:**
    *   If no matching approved PRs are found, display a notification and keep the session state as 'Draft'.
    *   Handle potential errors during data aggregation (e.g., missing product data, UoM issues) with appropriate logging and potentially user warnings.

---

#### **FR-SCM-003: Validate Consolidation Data**

*   **Source:** High-Level Req. Phase 1.3
*   **Priority:** High
*   **Description:** The system shall allow authorized users to review the generated consolidated lines and confirm their readiness for the next phase (Inventory Validation).
*   **User Interface (UI) Description:**
    *   A button (e.g., "Validate") shall be visible and enabled on the `scm_pr_consolidation_session` form view when the record `state` is 'In Progress'.
    *   Users review the lines in the `consolidated_line_ids` list/tree view.
    *   Clicking the "Validate" button triggers the state change.
    *   Upon successful completion, the `state` in the status bar changes to 'Validated'.
*   **Business Rules/Logic:**
    *   This action primarily serves as a workflow gate.
    *   The system must check if the current state is 'In Progress'.
    *   The system might optionally check if `consolidated_line_ids` exist before allowing validation.
*   **Data Handling:**
    *   Input: `scm_pr_consolidation_session` record ID.
    *   Processing: Verify current state.
    *   Output: Update the `scm_pr_consolidation_session` record's `state` to `'validated'`. Populate the `validation_date` field with the current timestamp.
*   **Preconditions:**
    *   The `scm_pr_consolidation_session` record exists and its `state` is 'In Progress'.
    *   Consolidated lines have been generated.
    *   User has permission to execute the validation action/method.
*   **Postconditions:**
    *   The `scm_pr_consolidation_session` record's `state` is updated to 'Validated'.
    *   The `validation_date` field is set.
*   **Error Handling/Alternative Flows:**
    *   If the state is not 'In Progress', the button should be disabled or display an error if clicked.
    *   If no consolidated lines exist, potentially display a warning before allowing validation or prevent it.

---

#### **FR-SCM-004: Perform Inventory Validation Check**

*   **Source:** High-Level Req. Phase 2.1
*   **Priority:** High
*   **Description:** Upon user initiation from a 'Validated' session, the system shall automatically analyze each consolidated line, comparing the required quantity (`total_quantity`) against the current available stock in the specified warehouse, considering inventory rules (safety stock, reorder points), and update each line with its calculated inventory status and quantity to purchase.
*   **User Interface (UI) Description:**
    *   A button (e.g., "Start Inventory Validation") shall be visible and enabled on the `scm_pr_consolidation_session` form view when the record `state` is 'Validated'.
    *   Clicking the button initiates the process. A visual indicator may display.
    *   Upon successful completion, the `state` in the status bar changes to 'Inventory Validation'.
    *   In the `consolidated_line_ids` list/tree view:
        *   The `inventory_status` column is populated (e.g., 'Sufficient', 'Below Safety', 'Stockout'). Visual cues (colors, icons) should represent the status.
        *   The `available_quantity` column shows the stock level at the time of checking.
        *   The `quantity_to_purchase` column shows the calculated quantity needed.
    *   Computed fields on the session header (e.g., `has_inventory_issues`, `total_stockout_items`) are updated.
*   **Business Rules/Logic:**
    *   Iterate through each `scm_consolidated_pr_line` linked to the session.
    *   For each line:
        *   Get `product_id` and `total_quantity`.
        *   Determine the relevant `warehouse_id` from the session.
        *   Fetch `available_quantity` (quantity on hand) for the product in the specific warehouse context.
        *   Fetch relevant inventory rule parameters (Safety Stock, Reorder Point) from `scm_inventory_rule` or standard `product.product` fields, considering warehouse/company context.
        *   Calculate `quantity_to_purchase = max(0, total_quantity - available_quantity)`.
        *   Determine `inventory_status`:
            *   If `available_quantity >= total_quantity`: 'Sufficient'.
            *   Else if `available_quantity <= 0`: 'Stockout'.
            *   Else if `available_quantity < safety_stock`: 'Below Safety'.
            *   Else if `available_quantity < reorder_point`: 'Below Reorder'.
            *   Else: 'Partial' (or other relevant status).
        *   Update the `scm_consolidated_pr_line` record.
    *   After processing all lines, update the `scm_pr_consolidation_session` state to `'inventory_validation'`.
    *   Trigger recomputation of related stored fields on the session based on updated line statuses.
*   **Data Handling:**
    *   Input: `scm_pr_consolidation_session` record ID, linked `scm_consolidated_pr_line` records. Access to `stock.quant`, `product.product`, `scm_inventory_rule` data.
    *   Processing: Inventory level lookups, comparison logic based on rules.
    *   Output: Update `available_quantity`, `quantity_to_purchase`, `inventory_status` on `scm_consolidated_pr_line` records. Update `state` on `scm_pr_consolidation_session`. Update computed fields like `has_inventory_issues` on the session.
*   **Preconditions:**
    *   The `scm_pr_consolidation_session` record exists and its `state` is 'Validated'.
    *   A valid `warehouse_id` is set on the session.
    *   Products on consolidated lines exist and have stock information available in Odoo.
    *   Inventory rules (if used) are configured.
    *   User has permission to execute the inventory check action/method.
*   **Postconditions:**
    *   The `scm_pr_consolidation_session` record's `state` is updated to 'Inventory Validation'.
    *   All linked `scm_consolidated_pr_line` records have their inventory-related fields (`available_quantity`, `quantity_to_purchase`, `inventory_status`) updated.
    *   Session-level computed fields reflecting inventory status are updated.
*   **Error Handling/Alternative Flows:**
    *   Handle cases where product stock information or inventory rules cannot be found (log errors, potentially set line status to 'Error').
    *   Ensure calculations handle zero or null values for stock/rules appropriately.

---

#### **FR-SCM-005: Review Inventory Status and Handle Exceptions**

*   **Source:** High-Level Req. Phase 2.2
*   **Priority:** High
*   **Description:** The system shall provide an interface for users (Procurement Officer, Inventory Manager) to review lines with non-sufficient inventory statuses, add notes, flag exceptions, and potentially trigger approval workflows for critical issues.
*   **User Interface (UI) Description:**
    *   Within the `scm_pr_consolidation_session` form view (state 'Inventory Validation'), the `consolidated_line_ids` list should allow filtering by `inventory_status`. Lines with issues should be visually distinct.
    *   A button (e.g., "Review Issues") might open a dedicated wizard or allow editing directly in the list/form view of the lines.
    *   For each line being reviewed, display: `product_id`, `total_quantity`, `available_quantity`, calculated `quantity_to_purchase`, current `inventory_status`.
    *   Editable fields should include:
        *   `inventory_notes` (Text): For user comments.
        *   `inventory_exception` (Boolean): Checkbox to flag manual review/override.
    *   Actions available might include:
        *   "Save Notes/Flag": Persist comments and exception flag.
        *   "Request Approval": (Visible for critical statuses like 'Stockout' or 'Below Safety', if workflow configured) Triggers notification/activity for Inventory Manager.
*   **Business Rules/Logic:**
    *   Users can add notes to explain decisions or context regarding inventory status.
    *   Flagging `inventory_exception` indicates manual intervention or override occurred.
    *   If an approval workflow is configured:
        *   Triggering "Request Approval" may set the `pending_approval` flag on the session or create activities assigned to the relevant approval role.
        *   The main "Approve Inventory" action (FR-SCM-006) might be blocked until `pending_approval` is false or specific approvals are logged.
*   **Data Handling:**
    *   Input: User comments, exception flags.
    *   Processing: Update corresponding fields on `scm_consolidated_pr_line`. Trigger notification/activity system if approval requested.
    *   Output: Updated `inventory_notes`, `inventory_exception` fields on `scm_consolidated_pr_line`. Potentially update `pending_approval` on `scm_pr_consolidation_session`. Creation of `mail.activity` records.
*   **Preconditions:**
    *   The `scm_pr_consolidation_session` record exists and its `state` is 'Inventory Validation'.
    *   Inventory check (FR-SCM-004) has been completed.
    *   User has permission to edit `scm_consolidated_pr_line` records or use the review interface.
*   **Postconditions:**
    *   Notes and exception flags are saved on relevant `scm_consolidated_pr_line` records.
    *   Approval requests are initiated if applicable.
*   **Error Handling/Alternative Flows:**
    *   Ensure concurrent edits are handled correctly if multiple users review simultaneously (standard Odoo locking).

---

#### **FR-SCM-006: Approve Inventory Validation**

*   **Source:** High-Level Req. Phase 2.2
*   **Priority:** High
*   **Description:** The system shall allow an authorized user to formally approve the inventory validation stage for a consolidation session, signifying that all checks are complete, exceptions handled (or approved), and the data is ready for purchase order generation (Phase 3).
*   **User Interface (UI) Description:**
    *   A button (e.g., "Approve Inventory") shall be visible and enabled on the `scm_pr_consolidation_session` form view when the record `state` is 'Inventory Validation'.
    *   This button might be conditionally visible/enabled based on user role (e.g., Inventory Manager if `pending_approval` is true) or always available to Procurement Officer if no critical issues required separate approval.
    *   Clicking the button triggers the final approval.
    *   Upon successful completion, the `state` in the status bar changes to 'Approved'.
*   **Business Rules/Logic:**
    *   The system must check if the current state is 'Inventory Validation'.
    *   The system may optionally check if `pending_approval` is false before allowing the final approval (if approval workflows are implemented).
*   **Data Handling:**
    *   Input: `scm_pr_consolidation_session` record ID.
    *   Processing: Verify current state and potentially approval status.
    *   Output: Update the `scm_pr_consolidation_session` record:
        *   Set `state` to `'approved'`.
        *   Set `inventory_validated` to `True`.
        *   Set `inventory_validation_date` to the current timestamp.
        *   Set `inventory_validated_by` to the current user's ID.
        *   Set `pending_approval` to `False`.
*   **Preconditions:**
    *   The `scm_pr_consolidation_session` record exists and its `state` is 'Inventory Validation'.
    *   All necessary exception reviews (FR-SCM-005) have been completed.
    *   Any required manager approvals for critical items have been granted.
    *   User has permission to execute the final inventory approval action/method.
*   **Postconditions:**
    *   The `scm_pr_consolidation_session` record's `state` is updated to 'Approved'.
    *   Inventory validation details (`inventory_validated`, `inventory_validation_date`, `inventory_validated_by`) are recorded.
    *   The session is now ready for Phase 3 (PO Generation).
*   **Error Handling/Alternative Flows:**
    *   If the state is not 'Inventory Validation', prevent the action.
    *   If pending approvals exist (and the workflow requires them), prevent the action and display a message indicating approvals are needed.

--- 