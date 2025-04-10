# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date


class ConsolidatedPRLine(models.Model):
    _name = 'scm.consolidated.pr.line'
    _description = 'Consolidated Purchase Request Line'
    _order = 'priority desc, earliest_date_required, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_state_selection(self):
        return [
            ('draft', 'Draft'),
            ('validated', 'Validated'),
            ('po_suggested', 'PO Suggested'),
            ('po_created', 'PO Created'),
            ('fulfilled', 'Fulfilled')
        ]
    
    @api.model
    def _get_priority_selection(self):
        return [
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('critical', 'Critical')
        ]
    
    @api.model
    def _get_inventory_status_selection(self):
        return [
            ('stockout', 'Out of Stock'),
            ('below_safety', 'Below Safety Stock'),
            ('below_reorder', 'Below Reorder Point'),
            ('normal', 'Normal'),
            ('excess', 'Excess'),
            ('sufficient', 'Sufficient'),
            ('partial', 'Partially Available'),
            ('insufficient', 'Insufficient')
        ]

    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',
        string='Consolidation Session',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True
    )
    # Make sure the consolidation_id field matches the inverse_name in PRConsolidationSession
    # Add it to _sql_constraints if needed
    _sql_constraints = [
        ('consolidation_product_uniq',
         'unique(consolidation_id, product_id)',
         'A product can only appear once in a consolidation session!')
    ]
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    total_quantity = fields.Float(
        string='Total Quantity',
        digits='Product Unit of Measure',
        required=True
    )
    available_quantity = fields.Float(
        string='Available Quantity',
        digits='Product Unit of Measure',
        compute='_compute_available_quantity',
        store=True
    )
    quantity_to_purchase = fields.Float(
        string='Quantity to Purchase',
        digits='Product Unit of Measure',
        compute='_compute_quantity_to_purchase',
        store=True
    )
    earliest_date_required = fields.Date(
        string='Earliest Date Required'
    )
    purchase_request_line_ids = fields.Many2many(
        'purchase.request.line',
        string='Purchase Request Lines'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('po_suggested', 'PO Suggested'),
        ('po_created', 'PO Created'),
        ('fulfilled', 'Fulfilled')
    ],  string='Status', 
        default='draft',
        tracking=True,
        required=True)
    priority = fields.Selection(
        selection='_get_priority_selection',
        string='Priority', 
        default='normal'
    )
    suggested_vendor_id = fields.Many2one(
        'res.partner',
        string='Suggested Vendor',
        domain=[('supplier_rank', '>', 0)]
    )
    purchase_suggestion_id = fields.Many2one(
        'scm.purchase.suggestion',
        string='Purchase Suggestion'
    )
    notes = fields.Text(string='Notes')
    purchase_price = fields.Float(
        string='Estimated Price',
        digits='Product Price',
        compute='_compute_purchase_price',
        store=True
    )
    subtotal = fields.Float(
        string='Subtotal',
        digits='Account',
        compute='_compute_subtotal',
        store=True
    )
    inventory_status = fields.Selection(
        selection='_get_inventory_status_selection',
        string='Inventory Status', 
        compute='_compute_inventory_status', 
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='consolidation_id.company_id',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id'
    )
    pr_count = fields.Integer(
        string='PRs',
        compute='_compute_pr_count'
    )

    _sql_constraints = [
        ('consolidation_product_uniq',
         'unique(consolidation_id, product_id)',
         'A product can only appear once in a consolidation session!')
    ]

    @api.depends('product_id')
    def _compute_available_quantity(self):
        for line in self:
            if line.product_id:
                # More efficient stock calculation
                line.available_quantity = line.product_id.with_context(
                    location=self.env['stock.location'].search([('usage', '=', 'internal')]).ids
                ).qty_available
            else:
                line.available_quantity = 0.0

    @api.depends('total_quantity', 'available_quantity')
    def _compute_quantity_to_purchase(self):
        for line in self:
            if line.total_quantity > line.available_quantity:
                line.quantity_to_purchase = line.total_quantity - line.available_quantity
            else:
                line.quantity_to_purchase = 0.0

    @api.depends('onhand_qty', 'safety_stock_level', 'reorder_point', 'available_quantity', 'total_quantity')
    def _compute_inventory_status(self):
        """Determine inventory status based on stock levels"""
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                line.inventory_status = 'normal'
                continue
                
            if line.onhand_qty <= 0:
                line.inventory_status = 'stockout'
            elif line.onhand_qty < line.safety_stock_level:
                line.inventory_status = 'below_safety'
            elif line.onhand_qty < line.reorder_point:
                line.inventory_status = 'below_reorder'
            elif line.onhand_qty > line.reorder_point * 2:  # Simple definition of excess
                line.inventory_status = 'excess'
            else:
                # Check against requested quantity
                if line.available_quantity >= line.total_quantity:
                    line.inventory_status = 'sufficient'
                elif line.available_quantity > 0:
                    line.inventory_status = 'partial'
                else:
                    line.inventory_status = 'insufficient'

    @api.depends('product_id', 'company_id')
    def _compute_purchase_price(self):
        for line in self:
            if line.product_id:
                # Get the product supplierinfo with the lowest price
                supplierinfo = self.env['product.supplierinfo'].search([
                    '|', 
                    ('product_id', '=', line.product_id.id),
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                    ('company_id', 'in', [line.company_id.id, False])
                ], limit=1, order='price')
                
                if supplierinfo:
                    line.purchase_price = supplierinfo.price
                else:
                    line.purchase_price = line.product_id.standard_price
            else:
                line.purchase_price = 0.0

    @api.depends('quantity_to_purchase', 'purchase_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity_to_purchase * line.purchase_price

    def _compute_pr_count(self):
        for line in self:
            line.pr_count = len(line.purchase_request_line_ids.mapped('request_id'))

    def action_validate(self):
        self.ensure_one()
        self.write({'state': 'validated'})
        return True

    def action_view_stock(self):
        self.ensure_one()
        action = {
            'name': _('Product Stock'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.product_id.id), ('location_id.usage', '=', 'internal')],
            'context': {'search_default_internal_loc': 1}
        }
        return action

    def action_view_purchase_requests(self):
        self.ensure_one()
        purchase_requests = self.purchase_request_line_ids.mapped('request_id')
        action = {
            'name': _('Purchase Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_requests.ids)],
        }
        return action

    def action_suggest_vendors(self):
        self.ensure_one()
        
        if self.suggested_vendor_id:
            return True
            
        # Find vendors who supply this product
        supplierinfo = self.env['product.supplierinfo'].search([
            '|',
            ('product_id', '=', self.product_id.id),
            ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
            ('company_id', 'in', [self.company_id.id, False])
        ], order='price')
        
        if supplierinfo:
            self.suggested_vendor_id = supplierinfo[0].partner_id.id
        
        return True

    def refresh_inventory_data(self):
        self._compute_available_quantity()
        return True

# Phase 2: Add inventory fields to consolidated lines
    
    # Add inventory fields
    onhand_qty = fields.Float('On-Hand Quantity', compute='_compute_inventory_data', store=False)
    forecasted_stock = fields.Float('Forecasted Stock', compute='_compute_inventory_data', store=False)
    safety_stock_level = fields.Float('Safety Stock Level', compute='_compute_inventory_data', store=False)
    reorder_point = fields.Float('Reorder Point', compute='_compute_inventory_data', store=False)
    
    days_of_stock = fields.Float('Days of Stock', compute='_compute_inventory_data', store=False)
    stock_coverage = fields.Float('Stock Coverage (Days)', compute='_compute_stock_coverage', store=True)
    expected_receipt_date = fields.Date('Expected Receipt Date', compute='_compute_inventory_data', store=False)
    
    inventory_notes = fields.Text('Inventory Notes')
    inventory_exception = fields.Boolean('Inventory Exception', default=False)
    exception_approved_by = fields.Many2one('res.users', 'Exception Approved By', readonly=True)
    exception_approval_date = fields.Datetime('Exception Approval Date', readonly=True)
    
    lead_time = fields.Integer('Lead Time (Days)', compute='_compute_inventory_data', store=False)
    turnover_rate = fields.Float('Turnover Rate', compute='_compute_inventory_data', store=False)
    
    procurement_recommendation = fields.Selection([
        ('purchase', 'Purchase'),
        ('transfer', 'Transfer'),
        ('wait', 'Wait for Receipt'),
        ('none', 'No Action')
    ], string='Recommendation', compute='_compute_procurement_recommendation', store=True)

    # Add missing inventory-related fields
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        related='consolidation_id.warehouse_id',
        store=True
    )
    
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        compute='_compute_quantity',
        store=True
    )

    @api.depends('purchase_request_line_ids.product_qty')
    def _compute_quantity(self):
        for line in self:
            line.quantity = sum(line.purchase_request_line_ids.mapped('product_qty'))

    @api.depends('product_id', 'warehouse_id', 'quantity')
    def _compute_inventory_data(self):
        """Compute current inventory levels and related data"""
        for line in self:
            if not line.product_id:
                continue

            # Calculate date range for stock moves using relativedelta
            date_from = fields.Date.today() - relativedelta(days=90)
            date_to = fields.Date.today()

            # Get stock moves for consumption calculation
            domain = [
                ('product_id', '=', line.product_id.id),
                ('state', '=', 'done'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ]

            # Get outgoing moves (consumption)
            outgoing_moves = self.env['stock.move'].search(domain + [
                ('location_dest_id.usage', '=', 'customer')
            ])

            # Calculate average monthly consumption
            if outgoing_moves:
                total_qty = sum(move.product_uom_qty for move in outgoing_moves)
                months = 3.0  # 90 days = 3 months
                line.avg_monthly_consumption = total_qty / months
            else:
                line.avg_monthly_consumption = 0.0

            # Get current stock level
            line.onhand_qty = line.product_id.with_context(
                location=line.warehouse_id.lot_stock_id.id
            ).qty_available

            # Update inventory status
            line._compute_inventory_status()

            if line.product_id and line.product_id.type in ['product', 'consu'] and line.warehouse_id:
                # Get current stock
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.warehouse_id.lot_stock_id.id)
                ])
                
                line.onhand_qty = sum(stock_quant.mapped('quantity')) if stock_quant else 0.0
                
                # Get forecasted stock
                quant_with_forecast = stock_quant.filtered(lambda q: q.location_id.id == line.warehouse_id.lot_stock_id.id)
                
                # Use the forecasted_qty logic from the extended stock_quant
                if quant_with_forecast:
                    for quant in quant_with_forecast:
                        quant._compute_forecasted_qty()
                    line.forecasted_stock = sum(quant_with_forecast.mapped('forecasted_qty'))
                else:
                    line.forecasted_stock = 0.0
                
                # Get inventory rule data
                rule = self.env['scm.inventory.rule'].get_applicable_rule(line.product_id, line.warehouse_id)
                
                if rule:
                    line.safety_stock_level = rule.safety_stock_qty
                    line.reorder_point = rule.reorder_point
                    line.lead_time = rule.lead_time
                    
                    # Calculate days of stock if avg daily usage is available
                    if rule.avg_daily_usage > 0:
                        line.days_of_stock = line.onhand_qty / rule.avg_daily_usage
                    else:
                        line.days_of_stock = 0.0
                else:
                    line.safety_stock_level = 0.0
                    line.reorder_point = 0.0
                    line.lead_time = 0
                    line.days_of_stock = 0.0
                
                # Calculate turnover rate (if possible) using last 90 days data
                date_from = fields.Date.today() - relativedelta(days=90)  # Fixed usage
                domain = [
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'done'),
                    ('date', '>=', date_from)
                ]
                
                # Get outgoing moves (to customers or production)
                moves = self.env['stock.move'].search(domain + [
                    ('location_dest_id.usage', 'in', ['customer', 'production']),
                    ('location_id.warehouse_id', '=', line.warehouse_id.id)
                ])
                
                if moves:
                    total_qty = sum(move.product_qty for move in moves)
                    # Turnover rate = (Annual Sales / Average Inventory)
                    # Estimated by extrapolating 90-day sales to annual
                    annual_estimate = total_qty * (365 / 90)
                    if line.onhand_qty > 0:
                        line.turnover_rate = annual_estimate / line.onhand_qty
                    else:
                        line.turnover_rate = 0.0
                else:
                    line.turnover_rate = 0.0
                
                # Expected receipt date - get first scheduled incoming shipment
                incoming_domain = [
                    ('product_id', '=', line.product_id.id),
                    ('location_dest_id.warehouse_id', '=', line.warehouse_id.id),
                    ('location_dest_id.usage', '=', 'internal'),
                    ('state', 'in', ['assigned', 'partially_available']),
                    ('date', '>=', fields.Datetime.now())
                ]
                
                incoming_move = self.env['stock.move'].search(incoming_domain, order='date', limit=1)
                line.expected_receipt_date = incoming_move.date.date() if incoming_move else False
            else:
                # Not a stockable product or no warehouse defined
                line.onhand_qty = 0.0
                line.forecasted_stock = 0.0
                line.safety_stock_level = 0.0
                line.reorder_point = 0.0
                line.days_of_stock = 0.0
                line.lead_time = 0
                line.turnover_rate = 0.0
                line.expected_receipt_date = False
    
    @api.depends('quantity', 'onhand_qty', 'days_of_stock', 'lead_time')
    def _compute_stock_coverage(self):
        """Calculate stock coverage based on consolidation quantity"""
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                line.stock_coverage = 0.0
                continue
                
            # Get average daily usage from rule
            rule = self.env['scm.inventory.rule'].get_applicable_rule(line.product_id, line.warehouse_id)
            
            if rule and rule.avg_daily_usage > 0:
                # Calculate how many days the current stock will last against the requested quantity
                daily_usage = rule.avg_daily_usage
                
                # Adjust for consolidated line quantity if it represents usage
                if line.quantity > 0 and line.uom_id == line.product_id.uom_id:
                    # If the line represents a periodic order, adjust daily usage
                    if line.consolidation_id.frequency == 'weekly':
                        adjusted_daily = line.quantity / 7.0
                    elif line.consolidation_id.frequency == 'monthly':
                        adjusted_daily = line.quantity / 30.0
                    elif line.consolidation_id.frequency == 'quarterly':
                        adjusted_daily = line.quantity / 90.0
                    else:  # Daily or undefined
                        adjusted_daily = line.quantity
                    
                    # Use max between historical and current request
                    daily_usage = max(daily_usage, adjusted_daily)
                
                if daily_usage > 0:
                    line.stock_coverage = line.onhand_qty / daily_usage
                else:
                    line.stock_coverage = 0.0
            else:
                line.stock_coverage = 0.0
    
    @api.depends('inventory_status', 'expected_receipt_date', 'lead_time', 'onhand_qty', 'quantity')
    def _compute_procurement_recommendation(self):
        """Determine procurement recommendation based on inventory status"""
        for line in self:
            if line.product_id.type not in ['product', 'consu']:
                line.procurement_recommendation = 'none'
                continue
                
            # Check if there's an expected receipt soon
            has_expected_receipt = False
            days_until_receipt = 999
            
            if line.expected_receipt_date:
                days_until_receipt = (line.expected_receipt_date - fields.Date.today()).days
                has_expected_receipt = days_until_receipt <= 7  # Receipt expected within a week
            
            if line.inventory_status in ['stockout', 'below_safety']:
                # Critical situation - need immediate action
                if has_expected_receipt and days_until_receipt <= 3:
                    # Very close receipt, might be better to wait
                    line.procurement_recommendation = 'wait'
                else:
                    # Check if we have stock in other warehouses for transfer
                    other_warehouses = self.env['stock.warehouse'].search([
                        ('id', '!=', line.warehouse_id.id),
                        ('company_id', '=', line.company_id.id)
                    ])
                    
                    has_stock_elsewhere = False
                    if other_warehouses:
                        quants = self.env['stock.quant'].search([
                            ('product_id', '=', line.product_id.id),
                            ('location_id.warehouse_id', 'in', other_warehouses.ids),
                            ('location_id.usage', '=', 'internal'),
                            ('quantity', '>', line.safety_stock_level)
                        ])
                        
                        has_stock_elsewhere = bool(quants)
                    
                    if has_stock_elsewhere:
                        line.procurement_recommendation = 'transfer'
                    else:
                        line.procurement_recommendation = 'purchase'
            
            elif line.inventory_status == 'below_reorder':
                # Below reorder point but not critical
                if has_expected_receipt:
                    line.procurement_recommendation = 'wait'
                else:
                    line.procurement_recommendation = 'purchase'
            
            else:
                # Normal or excess stock
                line.procurement_recommendation = 'none'
    
    def action_view_product_stock(self):
        """Open stock quants for this product"""
        self.ensure_one()
        
        if not self.product_id or self.product_id.type not in ['product', 'consu']:
            raise UserError(_("This product is not stockable."))
        
        domain = [
            ('product_id', '=', self.product_id.id)
        ]
        
        if self.warehouse_id:
            domain.append(('location_id.warehouse_id', '=', self.warehouse_id.id))
        
        return {
            'name': _('Stock Quants'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': domain,
        }
    
    def action_create_inventory_rule(self):
        """Create inventory rule for this product"""
        self.ensure_one()
        
        if not self.product_id:
            raise UserError(_("No product defined for this line."))
        
        # Check if rule already exists
        existing_rule = self.env['scm.inventory.rule'].search([
            ('product_id', '=', self.product_id.id),
            ('warehouse_id', '=', self.warehouse_id.id)
        ], limit=1)
        
        if existing_rule:
            # Open existing rule
            return {
                'name': _('Inventory Rule'),
                'type': 'ir.actions.act_window',
                'res_model': 'scm.inventory.rule',
                'res_id': existing_rule.id,
                'view_mode': 'form',
            }
        else:
            # Create new rule
            return {
                'name': _('Create Inventory Rule'),
                'type': 'ir.actions.act_window',
                'res_model': 'scm.inventory.rule',
                'view_mode': 'form',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_warehouse_id': self.warehouse_id.id,
                    'default_name': self.product_id.name,
                }
            }
    
    def action_approve_inventory_exception(self):
        """Approve exception for inventory validation"""
        self.ensure_one()
        
        if not self.inventory_exception:
            # Set exception flag
            self.write({
                'inventory_exception': True,
                'exception_approved_by': self.env.user.id,
                'exception_approval_date': fields.Datetime.now()
            })
            
            # Log message in chatter
            self.consolidation_id.message_post(
                body=_("Inventory exception approved for product '%s' by %s") % (
                    self.product_id.name, self.env.user.name
                ),
                subtype_id=self.env.ref('mail.mt_note').id
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Exception Approved'),
                    'message': _("Inventory exception has been approved for %s.") % self.product_id.name,
                    'sticky': False,
                    'type': 'info',
                }
            }
        
        return True
    
    def action_reset_inventory_exception(self):
        """Reset inventory exception flag"""
        self.ensure_one()
        
        if self.inventory_exception:
            self.write({
                'inventory_exception': False,
                'exception_approved_by': False,
                'exception_approval_date': False
            })
            
            # Log message in chatter
            self.consolidation_id.message_post(
                body=_("Inventory exception reset for product '%s' by %s") % (
                    self.product_id.name, self.env.user.name
                ),
                subtype_id=self.env.ref('mail.mt_note').id
            )
    
    def action_view_forecast(self):
        """View forecasts for this product"""
        self.ensure_one()
        
        if not self.product_id:
            raise UserError(_("No product defined for this line."))
        
        domain = [
            ('product_id', '=', self.product_id.id)
        ]
        
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        
        return {
            'name': _('Product Forecasts'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.forecast',
            'view_mode': 'tree,form',
            'domain': domain,
        }

    # Add missing fields for procurement history
    last_purchase_date = fields.Date(
        string='Last Purchase Date',
        compute='_compute_procurement_history',
        store=True
    )
    last_purchase_price = fields.Float(
        string='Last Purchase Price',
        compute='_compute_procurement_history',
        store=True,
        digits='Product Price'
    )
    avg_monthly_usage = fields.Float(
        string='Avg Monthly Usage',
        compute='_compute_procurement_history',
        store=True,
        digits='Product Unit of Measure'
    )
    turnover_rate = fields.Float(
        string='Turnover Rate',
        compute='_compute_procurement_history',
        store=True,
        digits=(16, 2)
    )

    @api.depends('product_id', 'warehouse_id')
    def _compute_procurement_history(self):
        """Compute procurement history metrics"""
        for line in self:
            if not line.product_id or not line.warehouse_id:
                line.last_purchase_date = False
                line.last_purchase_price = 0.0
                line.avg_monthly_usage = 0.0
                line.turnover_rate = 0.0
                continue

            # Get last purchase with fixed ordering
            domain = [
                ('product_id', '=', line.product_id.id),
                ('state', '=', 'purchase'),
                ('order_id.picking_type_id.warehouse_id', '=', line.warehouse_id.id)
            ]
            last_po_line = self.env['purchase.order.line'].search(
                domain, 
                order='create_date desc',  # Changed from order_id.date_order
                limit=1
            )
            
            # Get date from order if exists
            if last_po_line and last_po_line.order_id:
                line.last_purchase_date = last_po_line.order_id.date_order.date() if last_po_line.order_id.date_order else False
                line.last_purchase_price = last_po_line.price_unit
            else:
                line.last_purchase_date = False
                line.last_purchase_price = 0.0

            # Calculate average monthly usage using relativedelta
            three_months_ago = fields.Date.today() - relativedelta(months=3)
            usage_moves = self.env['stock.move'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id.warehouse_id', '=', line.warehouse_id.id),
                ('location_dest_id.usage', 'in', ['customer', 'production']),
                ('state', '=', 'done'),
                ('date', '>=', three_months_ago)
            ])
            
            total_usage = sum(usage_moves.mapped('product_uom_qty'))
            line.avg_monthly_usage = total_usage / 3 if total_usage else 0.0

            # Calculate turnover rate
            if line.avg_monthly_usage and line.onhand_qty:
                line.turnover_rate = (line.avg_monthly_usage * 12) / line.onhand_qty
            else:
                line.turnover_rate = 0.0

    # Add missing consumption field
    avg_monthly_consumption = fields.Float(
        string='Average Monthly Consumption',
        compute='_compute_inventory_data',
        store=False,
        digits='Product Unit of Measure',
        help="Average monthly consumption based on last 3 months"
    )