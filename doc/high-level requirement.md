Supply Chain Management Module Workflows
Overview
This document outlines the business processes and user workflows for an Odoo 17 module designed for Supply Chain Management. The module consolidates Purchase Requests (PRs), validates inventory levels, suggests Purchase Orders (POs) based on Purchase Agreements, and tracks PR fulfillment.
Table of Contents
1.	PR Consolidation Process
2.	Inventory Validation Process
3.	PO Creation Process
4.	Change Management Process
5.	PR Fulfillment Process
PR Consolidation Process
flowchart TD
    A[Start] --> B[Create Consolidation Session]
    B --> C[Select Date Range and Filters]
    C --> D[System Aggregates PRs]
    D --> E[Review Consolidated Data]
    E --> F{Adjustments Needed?}
    F -- Yes --> G[Make Manual Adjustments]
    G --> E
    F -- No --> H[Confirm Consolidation]
    H --> I[End]
Description:
1.	Create Consolidation Session: The Supply Chain user initiates a new consolidation session from the dashboard.
2.	Select Date Range and Filters: User defines the time period for PR collection and optional filters (departments, categories).
3.	System Aggregates PRs: The system automatically collects all approved PRs and aggregates quantities by product.
4.	Review Consolidated Data: User reviews the consolidated information showing total demand per product.
5.	Adjustments: If necessary, the user can make manual adjustments to the consolidated data.
6.	Confirm Consolidation: User approves the consolidated view, making it ready for inventory validation.
Inventory Validation Process
flowchart TD
    A[Start] --> B[Select Confirmed Consolidation]
    B --> C[System Checks Current Inventory]
    C --> D[Compare Demand vs. Available Stock]
    D --> E[Review Shortages/Surpluses]
    E --> F{Manual Overrides?}
    F -- Yes --> G[Adjust Purchasing Decisions]
    G --> E
    F -- No --> H[Confirm Purchase Needs]
    H --> I[End]
Description:
1.	Select Confirmed Consolidation: User selects a previously confirmed consolidation session.
2.	System Checks Inventory: The system automatically checks current stock levels for all products in the consolidation.
3.	Compare Demand vs. Available: The system identifies which products have sufficient stock and which need to be purchased.
4.	Review Shortages/Surpluses: User reviews the system's assessment of inventory status.
5.	Manual Overrides: User can override system decisions if needed (e.g., reserving stock for other purposes).
6.	Confirm Purchase Needs: User confirms the final list of products that need to be purchased.

**Implementation Status (April 2025):**
- The inventory validation process has been implemented with the `validate.inventory.wizard`.
- The wizard displays all consolidated lines with their current stock, required quantity, and available quantity.
- Users can filter to view only critical items (those with inventory status 'stockout' or 'insufficient').
- The system calculates the quantity to purchase based on the difference between required quantity and available quantity.
- After validation, users can proceed to PO creation.
- The consolidation session workflow has been updated to include the inventory validation state.
- Purchase orders created from the consolidation are linked to the session and visible in a dedicated tab.
PO Creation Process
flowchart TD
    A[Start] --> B[View Purchase Suggestions]
    B --> C[System Groups by Vendor]
    C --> D[Review Vendor Groupings]
    D --> E{Multiple Vendors Available?}
    E -- Yes --> F[Select Preferred Vendor]
    F --> G[Review Purchase Quantities]
    E -- No --> G
    G --> H{Adjustments Needed?}
    H -- Yes --> I[Modify Quantities/Terms]
    I --> G
    H -- No --> J[Preview Draft POs]
    J --> K[Create Draft POs]
    K --> L[Link POs to Original PRs]
    L --> M[End]
Description:
1.	View Purchase Suggestions: User views the list of products needing purchase after inventory validation.
2.	System Groups by Vendor: The system automatically groups products by vendor based on purchase agreements.
3.	Review Vendor Groupings: User reviews the suggested vendor assignments.
4.	Multiple Vendors: For products with multiple possible vendors, user selects the preferred option.
5.	Review Purchase Quantities: User reviews the suggested purchase quantities.
6.	Adjustments: User can modify quantities or terms as needed (e.g., to meet minimum order quantities).
7.	Preview Draft POs: System generates a preview of the purchase orders that will be created.
8.	Create Draft POs: User confirms, and system creates draft purchase orders.
9.	Link POs to PRs: System creates links between the new POs and the original PRs for tracking.
Change Management Process
flowchart TD
    A[Start] --> B[Change Detected]
    B --> C{Type of Change?}
    C -- PR Added/Modified/Deleted --> D[Recalculate Affected Product Demand]
    C -- Inventory Level Changed --> E[Re-validate Stock Sufficiency]
    C -- PO Changed --> F[Update PR Fulfillment Plan]
    D --> G[Notify Supply Chain Team]
    E --> G
    F --> G
    G --> H[Review Impact Assessment]
    H --> I{Adjustments Required?}
    I -- Yes --> J[Adjust Consolidation/Orders]
    J --> K[Update Affected PRs]
    I -- No --> L[Record Change in Log]
    K --> L
    L --> M[End]
Description:
1.	Change Detected: System detects a change in PRs, inventory, or POs affecting the current consolidation.
2.	Type of Change: System identifies what type of change occurred.
3.	Recalculate/Re-validate: System automatically recalculates affected figures.
4.	Notify Team: Supply Chain team receives notification about the change and its impact.
5.	Review Impact: User reviews how the change affects current procurement plans.
6.	Adjustments: If needed, user makes adjustments to consolidation or orders.
7.	Update PRs: System updates affected PRs with new information.
8.	Record Change: All changes are logged for audit and tracking purposes.
PR Fulfillment Process
flowchart TD
    A[Start] --> B[PO Confirmed]
    B --> C[Update PR Timelines]
    C --> D[Track PO Status]
    D --> E[Products Received]
    E --> F[Create Internal Transfer Suggestions]
    F --> G[User Reviews Transfer Suggestions]
    G --> H{Modifications Needed?}
    H -- Yes --> I[Adjust Transfer Plans]
    I --> G
    H -- No --> J[Confirm Transfers]
    J --> K[Execute Internal Transfers]
    K --> L[Update PR Status]
    L --> M{All Items Delivered?}
    M -- Yes --> N[Close PR]
    M -- No --> O[Maintain Partial Fulfillment Status]
    N --> P[End]
    O --> P
Description:
1.	PO Confirmed: After a PO is confirmed, the process begins.
2.	Update PR Timelines: System updates the expected delivery dates in the original PRs.
3.	Track PO Status: System monitors the status of the PO (confirmed, shipped, received).
4.	Products Received: When products are received in the warehouse.
5.	Create Transfer Suggestions: System suggests internal transfers to fulfill specific PRs.
6.	User Reviews: Supply Chain user reviews the suggested transfers.
7.	Modifications: User can adjust transfer plans if needed.
8.	Confirm Transfers: User approves the transfer plans.
9.	Execute Transfers: System creates internal transfer orders.
10.	Update PR Status: System updates the fulfillment status of each PR.
11.	Fulfillment Complete: System marks PRs as fulfilled when all items are delivered.
Supply Chain Module Data Model
Overview
This document outlines the data model for the Odoo 17 Supply Chain Management module. The model is designed to support the consolidation of Purchase Requests (PRs), inventory validation, purchase order suggestion, and PR fulfillment tracking.
Core Models
1. PR Consolidation Session (scm.pr.consolidation.session)
Represents a consolidation session for Purchase Requests within a specific time period.
Field Name	Field Type	Description
name	Char	Name/reference of the consolidation session (e.g., "Q1 2025 IT Equipment")
date_from	Date	Start date of the period for PR collection
date_to	Date	End date of the period for PR collection
state	Selection	Status of the session: draft, in_progress, validated, po_created, done, cancelled
user_id	Many2one	User who created the session
department_ids	Many2many	Optional filter for specific departments
category_ids	Many2many	Optional filter for specific product categories
consolidated_line_ids	One2many	Relation to the consolidated PR lines
purchase_suggestion_ids	One2many	Relation to purchase suggestions generated
po_count	Integer (computed)	Count of POs generated from this session
total_amount	Float (computed)	Total estimated value of all consolidated PRs
creation_date	Datetime	When the consolidation was created
validation_date	Datetime	When inventory validation was completed
po_creation_date	Datetime	When POs were generated
notes	Text	Additional notes about the consolidation
company_id	Many2one	Company reference
2. Consolidated PR Line (scm.consolidated.pr.line)
Represents the aggregated demand for a specific product across multiple PRs.
Field Name	Field Type	Description
consolidation_id	Many2one	Reference to the consolidation session
product_id	Many2one	Product being consolidated
product_uom_id	Many2one	Unit of measure
total_quantity	Float	Total quantity requested across all PRs
available_quantity	Float (computed)	Current quantity available in stock
quantity_to_purchase	Float	Quantity that needs to be purchased
earliest_date_required	Date (computed)	Earliest date the product is needed
purchase_request_line_ids	Many2many	All PR lines related to this product
state	Selection	Status: draft, validated, po_suggested, po_created, fulfilled
priority	Selection	Priority level: low, normal, high, critical
suggested_vendor_id	Many2one	Suggested vendor based on purchase agreements
purchase_suggestion_id	Many2one	Related purchase suggestion
notes	Text	Additional notes about this consolidated line
purchase_price	Float (computed)	Estimated purchase price based on agreements
subtotal	Float (computed)	Total value (quantity × price)
inventory_status	Selection	Status after inventory check: sufficient, partial, insufficient
3. Purchase Suggestion (scm.purchase.suggestion)
Represents a suggestion to create a PO for a specific vendor based on consolidated PR lines.
Field Name	Field Type	Description
consolidation_id	Many2one	Reference to the consolidation session
vendor_id	Many2one	Suggested vendor
name	Char	Name/reference for the suggestion
state	Selection	Status: draft, reviewed, po_created, cancelled
suggestion_line_ids	One2many	Lines detailing products to order
purchase_order_id	Many2one	Created purchase order (if any)
total_amount	Float (computed)	Total estimated value
currency_id	Many2one	Currency for the amounts
user_id	Many2one	User who reviewed the suggestion
purchase_agreement_id	Many2one	Related purchase agreement (if applicable)
creation_date	Datetime	When the suggestion was created
approval_date	Datetime	When the suggestion was approved
po_creation_date	Datetime	When PO was generated
notes	Text	Additional notes about this suggestion
company_id	Many2one	Company reference
4. Purchase Suggestion Line (scm.purchase.suggestion.line)
Represents a line item in a purchase suggestion.
Field Name	Field Type	Description
suggestion_id	Many2one	Reference to the purchase suggestion
product_id	Many2one	Product to purchase
product_uom_id	Many2one	Unit of measure
quantity	Float	Quantity to purchase
price_unit	Float	Unit price from agreement or vendor history
subtotal	Float (computed)	Total value (quantity × price)
consolidated_line_id	Many2one	Reference to the consolidated PR line
purchase_order_line_id	Many2one	Created PO line (if any)
notes	Text	Additional notes about this line
state	Selection	Status: draft, po_created, cancelled
delivery_lead_time	Integer	Expected lead time in days
expected_arrival_date	Date (computed)	Expected date of arrival
purchase_agreement_line_id	Many2one	Related purchase agreement line (if applicable)
5. PR Fulfillment Plan (scm.pr.fulfillment.plan)
Tracks how each PR will be fulfilled based on POs created.
Field Name	Field Type	Description
consolidation_id	Many2one	Reference to the consolidation session
purchase_request_id	Many2one	Reference to the original PR
purchase_request_line_id	Many2one	Reference to the specific PR line
product_id	Many2one	Product requested
requested_quantity	Float	Quantity requested in PR
purchase_order_id	Many2one	PO that will fulfill this PR
purchase_order_line_id	Many2one	Specific PO line
expected_arrival_date	Date	Expected date of arrival based on PO
fulfilled_quantity	Float	Quantity already fulfilled
remaining_quantity	Float (computed)	Quantity still pending fulfillment
state	Selection	Status: pending, partially_fulfilled, fulfilled, cancelled
internal_transfer_id	Many2one	Related internal transfer (if created)
internal_transfer_line_id	Many2one	Specific internal transfer line
notes	Text	Additional notes about fulfillment
requester_id	Many2one	User who created the original PR
department_id	Many2one	Department that made the request
priority	Selection	Priority level inherited from PR
fulfillment_date	Datetime	When the PR was fulfilled (if applicable)
6. Change Log (scm.change.log)
Tracks changes that affect the consolidation and procurement process.
Field Name	Field Type	Description
name	Char	Name/reference of the change
consolidation_id	Many2one	Related consolidation session
change_type	Selection	Type: pr_change, inventory_change, po_change
change_date	Datetime	When the change occurred
user_id	Many2one	User who recorded or was notified of the change
description	Text	Description of the change
impact	Selection	Impact level: low, medium, high
affected_product_ids	Many2many	Products affected by the change
affected_pr_ids	Many2many	PRs affected by the change
affected_po_ids	Many2many	POs affected by the change
action_taken	Text	Description of action taken to address the change
resolution_date	Datetime	When the change was resolved
state	Selection	Status: open, in_progress, resolved
Relationships with Existing Odoo Models
Integration with Purchase Request Module
The module extends the Purchase Request model from the OCA module:
class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    
    consolidation_ids = fields.Many2many('scm.pr.consolidation.session', 
                                        string='Consolidation Sessions')
    fulfillment_plan_ids = fields.One2many('scm.pr.fulfillment.plan', 
                                           'purchase_request_id', 
                                           string='Fulfillment Plans')
    fulfillment_status = fields.Selection([
        ('not_included', 'Not Included'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('partially_fulfilled', 'Partially Fulfilled'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled')
    ], string='Fulfillment Status', compute='_compute_fulfillment_status', store=True)
    expected_fulfillment_date = fields.Date(string='Expected Fulfillment Date', 
                                            compute='_compute_expected_fulfillment_date')
Similarly, the Purchase Request Line model is extended:
class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'
    
    consolidated_line_ids = fields.Many2many('scm.consolidated.pr.line', 
                                            string='Consolidated Lines')
    fulfillment_plan_ids = fields.One2many('scm.pr.fulfillment.plan', 
                                           'purchase_request_line_id', 
                                           string='Fulfillment Plans')
    fulfillment_status = fields.Selection([
        ('not_included', 'Not Included'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('partially_fulfilled', 'Partially Fulfilled'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled')
    ], string='Fulfillment Status', compute='_compute_fulfillment_status', store=True)
    expected_fulfillment_date = fields.Date(string='Expected Fulfillment Date', 
                                            compute='_compute_expected_fulfillment_date')
Integration with Purchase Order Model
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    purchase_suggestion_id = fields.Many2one('scm.purchase.suggestion', 
                                            string='Purchase Suggestion')
    consolidation_id = fields.Many2one('scm.pr.consolidation.session',
                                      string='PR Consolidation', 
                                      related='purchase_suggestion_id.consolidation_id',
                                      store=True)
    fulfillment_plan_ids = fields.One2many('scm.pr.fulfillment.plan', 
                                           'purchase_order_id', 
                                           string='PR Fulfillment Plans')
    affected_pr_count = fields.Integer(string='Affected PRs', 
                                      compute='_compute_affected_pr_count')
Similarly for Purchase Order Line:
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    suggestion_line_id = fields.Many2one('scm.purchase.suggestion.line', 
                                        string='Suggestion Line')
    fulfillment_plan_ids = fields.One2many('scm.pr.fulfillment.plan', 
                                           'purchase_order_line_id', 
                                           string='PR Fulfillment Plans')
    pr_line_count = fields.Integer(string='PR Lines', 
                                  compute='_compute_pr_line_count')
Integration with Stock Module
For tracking internal transfers:
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    fulfillment_plan_ids = fields.Many2many('scm.pr.fulfillment.plan', 
                                           string='PR Fulfillment Plans')
    is_pr_fulfillment = fields.Boolean(string='Is PR Fulfillment', 
                                      compute='_compute_is_pr_fulfillment', store=True)
Indexes and Database Optimization
For performance reasons, the following indexes should be created:
# In scm.consolidated.pr.line model
_sql_constraints = [
    ('consolidation_product_uniq', 
     'unique(consolidation_id, product_id)', 
     'A product can only appear once in a consolidation session!')
]

# In scm.purchase.suggestion.line model
_sql_constraints = [
    ('suggestion_product_uniq', 
     'unique(suggestion_id, product_id)', 
     'A product can only appear once in a purchase suggestion!')
]

# Other indexes
_indexes = [
    ('consolidation_id', 'state'),  # For scm.consolidated.pr.line
    ('consolidation_id', 'vendor_id', 'state'),  # For scm.purchase.suggestion
    ('purchase_request_id', 'state'),  # For scm.pr.fulfillment.plan
    ('product_id', 'consolidation_id')  # For scm.consolidated.pr.line
]


Let's outline the next steps for implementing this Odoo 17 module:
Implementation Roadmap
1.	Module Setup 
o	Create the module directory structure (following Odoo conventions)
o	Define the module manifest (__manifest__.py)
o	Set up dependencies (OCA Purchase Request module, stock, purchase)
o	Create initial security configuration (access rights and rules)
2.	Core Data Models Implementation 
o	Implement the models defined in the data model document
o	Create the necessary fields, methods, and relationships
o	Set up computed fields and their dependencies
o	Implement business logic methods for each model
3.	Views & Interface Development 
o	Create form, list, and kanban views for each model
o	Develop the Consolidation Dashboard
o	Create wizards for the consolidation process, inventory validation, and PO suggestions
o	Implement search filters and custom grouping options
o	Set up action buttons for workflow transitions
4.	Workflow Implementation 
o	Implement the state management for each model
o	Create workflow transitions and state change methods
o	Develop validation rules for each workflow step
o	Implement the change management detection and notification system
5.	Reports Development 
o	Create PDF reports for consolidation sessions
o	Develop inventory validation reports
o	Implement purchase suggestion reports
o	Create fulfillment tracking reports
6.	Integration with Existing Modules 
o	Extend the Purchase Request views to show fulfillment status
o	Modify Purchase Order views to show related PR information
o	Integrate with inventory module for stock validation
o	Connect with internal transfers for fulfillment tracking
7.	Testing 
o	Develop unit tests for individual models and methods
o	Create integration tests for the entire workflow
o	Perform user acceptance testing with the Supply Chain team
o	Test with realistic data volumes to ensure performance
8.	Documentation & Training 
o	Create technical documentation for developers
o	Develop user documentation with workflow guides
o	Prepare training materials for Supply Chain users
o	Record tutorial videos for key workflows
Development Approach
I recommend implementing this module in phases:
Phase 1: Core Consolidation
•	PR Consolidation Session model and views
•	Consolidated PR Line model and views
•	Basic workflow for creating and reviewing consolidations
•	Minimal reporting
Phase 2: Inventory Validation
•	Integration with stock module
•	Inventory validation workflow
•	Stock shortage/surplus reporting
•	Change detection for inventory levels
Phase 3: Purchase Suggestions
•	Purchase Suggestion models
•	Integration with purchase agreements
•	PO creation workflow
•	Vendor selection logic
Phase 4: Fulfillment Tracking
•	PR Fulfillment Plan model
•	Integration with PO receipts
•	Internal transfer suggestions
•	PR status updates
Phase 5: Change Management & Optimization
•	Change log implementation
•	Notification system
•	Performance optimizations
•	Advanced reporting
Technical Considerations
1.	Performance: Consider database indexing and query optimization for larger datasets.
2.	Scalability: Design the module to handle large numbers of PRs and products.
3.	Concurrency: Implement proper locking mechanisms for concurrent sessions.
4.	User Experience: Make the interface intuitive with proper visual cues and guidance.
5.	Extensibility: Design with future enhancements in mind, using proper inheritance patterns.
6.	Upgradability: Follow Odoo's best practices to ensure smooth upgrades.
Would you like to focus on any specific aspect of the implementation to discuss in more detail?
