# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ValidateInventoryWizard(models.TransientModel):
    _name = 'validate.inventory.wizard'
    _description = 'Inventory Validation Wizard'
    
    session_id = fields.Many2one('scm.pr.consolidation.session', string='Consolidation Session', required=True)
    line_ids = fields.One2many('validate.inventory.wizard.line', 'wizard_id', string='Lines')
    include_critical_only = fields.Boolean(string='Show Critical Items Only', default=True)
    update_safety_stock = fields.Boolean(string='Update Safety Stock Levels', default=False)
    notes = fields.Text(string='Notes')
    
    # Summary fields
    total_items = fields.Integer('Total Items', compute='_compute_summary')
    critical_items = fields.Integer('Critical Items', compute='_compute_summary')
    non_critical_items = fields.Integer('Non-Critical Items', compute='_compute_summary')
    expected_receipts = fields.Integer('Items with Expected Receipts', compute='_compute_summary')

    @api.depends('line_ids', 'include_critical_only')
    def _compute_summary(self):
        """Compute summary statistics for the wizard"""
        for wizard in self:
            wizard.total_items = len(wizard.line_ids)
            
            critical_lines = wizard.line_ids.filtered(
                lambda l: l.inventory_status in ['stockout', 'below_safety']
            )
            wizard.critical_items = len(critical_lines)
            
            non_critical_lines = wizard.line_ids.filtered(
                lambda l: l.inventory_status not in ['stockout', 'below_safety']
            )
            wizard.non_critical_items = len(non_critical_lines)
            
            # Count items with expected receipts (available quantity > 0)
            lines_with_receipts = wizard.line_ids.filtered(
                lambda l: l.available_qty > 0
            )
            wizard.expected_receipts = len(lines_with_receipts)
    
    @api.onchange('include_critical_only')
    def _onchange_include_critical_only(self):
        if self.include_critical_only:
            critical_lines = self.line_ids.filtered(lambda l: l.is_critical)
            self.line_ids = [(6, 0, critical_lines.ids)]
        else:
            session = self.session_id
            if session and session.consolidated_line_ids:
                wizard_line_vals = []
                for line in session.consolidated_line_ids:
                    # Get inventory levels
                    available_qty = line.product_id.with_context(
                        location=session.warehouse_id.lot_stock_id.id
                    ).qty_available
                    
                    # Get inventory rule
                    rule = self.env['scm.inventory.rule'].get_applicable_rule(
                        line.product_id, 
                        session.warehouse_id
                    )
                    
                    wizard_line_vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'consolidated_line_id': line.id,
                        'available_qty': available_qty,
                        'safety_stock_qty': rule.safety_stock_qty if rule else 0.0,
                        'reorder_point': rule.reorder_point if rule else 0.0,
                    }))
                
                self.line_ids = [(5, 0, 0)] + wizard_line_vals
    
    @api.onchange('session_id')
    def _onchange_session_id(self):
        """Update stock values when session changes according to FR-SCM-004"""
        if self.session_id and self.line_ids:
            for line in self.line_ids:
                if line.product_id:
                    # Get the stock location for the session
                    stock_location = self.session_id.warehouse_id.lot_stock_id
                    if stock_location:
                        # Get current stock (actual on-hand quantity) from the specific session
                        current_stock = line.product_id.with_context(
                            location=stock_location.id
                        ).qty_available
                        
                        # Get inventory rule parameters for the product in this session
                        rule = self.env['scm.inventory.rule'].get_applicable_rule(
                            line.product_id, 
                            self.session_id.warehouse_id
                        )
                        
                        # Calculate incoming quantity (moves to the stock location)
                        incoming_moves = self.env['stock.move'].search([
                            ('product_id', '=', line.product_id.id),
                            ('location_dest_id', '=', stock_location.id),
                            ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
                        ])
                        incoming_qty = sum(incoming_moves.mapped('product_uom_qty'))
                        
                        # Calculate outgoing quantity (moves from the stock location)
                        outgoing_moves = self.env['stock.move'].search([
                            ('product_id', '=', line.product_id.id),
                            ('location_id', '=', stock_location.id),
                            ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
                        ])
                        outgoing_qty = sum(outgoing_moves.mapped('product_uom_qty'))
                        
                        # Update fields according to FR-SCM-004
                        line.available_qty = current_stock + incoming_qty - outgoing_qty  # Forecast quantity
    
    def action_validate_inventory(self):
        self.ensure_one()
        _logger.info("Starting inventory validation")
        
        if not self.line_ids:
            raise UserError(_("No lines to validate."))
            
        # Validate each line
        validated_count = 0
        for line in self.line_ids:
            _logger.info(f"Validating line {line.id} - Product: {line.product_id.name}")
            
            # Find corresponding consolidated line
            consolidated_line = self.env['scm.consolidated.pr.line'].search([
                ('product_id', '=', line.product_id.id),
                ('consolidation_id', '=', self.session_id.id)
            ], limit=1)
            
            if consolidated_line:
                _logger.info(f"Found consolidated line {consolidated_line.id}")
                # Update consolidated line with wizard line data
                consolidated_line.write({
                    'onhand_qty': line.available_qty,
                    'inventory_status': line.inventory_status,
                })
                validated_count += 1
                _logger.info(f"Updated consolidated line with status: {line.inventory_status}")
            else:
                _logger.warning(f"No consolidated line found for product {line.product_id.name}")
        
        # Update the consolidation session
        self.session_id.write({
            'state': 'po_creation',
            'inventory_validation_notes': self.notes,
            'inventory_validated': True,
            'inventory_validation_date': fields.Datetime.now(),
            'inventory_validated_by': self.env.user.id,
            'inventory_status': 'approved'
        })
        
        # Show success message
        message = _("%d items have been validated successfully.") % validated_count
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Complete'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _update_safety_stock_levels(self):
        """Update safety stock levels based on inventory validation results."""
        for line in self.line_ids:
            if line.inventory_status in ['stockout', 'below_safety']:
                # Get current inventory rule
                rule = self.env['scm.inventory.rule'].get_applicable_rule(
                    line.product_id,
                    self.session_id.warehouse_id
                )
                
                if rule:
                    # Calculate new safety stock (20% increase for items with issues)
                    current_safety_stock = rule.safety_stock_qty
                    new_safety_stock = current_safety_stock * 1.2
                    
                    # Adjust based on lead time and average daily usage
                    lead_time_days = rule.lead_time_days or 1
                    avg_daily_usage = rule.average_daily_usage or 0
                    min_safety_stock = lead_time_days * avg_daily_usage
                    
                    new_safety_stock = max(new_safety_stock, min_safety_stock)
                    
                    # Update the rule
                    rule.write({
                        'safety_stock_qty': new_safety_stock,
                        'last_update_date': fields.Date.today(),
                    })
                    
                    # Log the change
                    self.env['scm.inventory.rule.history'].create({
                        'rule_id': rule.id,
                        'old_safety_stock': current_safety_stock,
                        'new_safety_stock': new_safety_stock,
                        'update_reason': 'Updated based on inventory validation results',
                        'updated_by': self.env.user.id,
                    })

    def _create_critical_items_activities(self, critical_lines):
        """Create activities for inventory managers to review critical items."""
        managers = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('stock.group_stock_manager').id)
        ])
        
        if not managers:
            return
        
        # Create activity for each manager
        for manager in managers:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'note': _('Please review and approve the following critical inventory items:\n\n%s') % 
                    '\n'.join(['- %s: %s' % (l.product_id.name, l.inventory_status) for l in critical_lines]),
                'user_id': manager.id,
                'res_id': self.session_id.id,
                'res_model_id': self.env['ir.model']._get('scm.pr.consolidation.session').id,
                'summary': _('Critical Inventory Items Review Required'),
            })
            
            # Send email notification
            template = self.env.ref('scm_procurement.mail_template_critical_inventory_review')
            if template:
                template.with_context(
                    critical_lines=critical_lines,
                    session=self.session_id
                ).send_mail(self.session_id.id, force_send=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ValidateInventoryWizard, self).default_get(fields_list)
        if 'line_ids' in fields_list and self.env.context.get('active_id'):
            consolidation = self.env['scm.pr.consolidation.session'].browse(self.env.context.get('active_id'))
            if consolidation:
                # Get all consolidated lines
                consolidated_lines = consolidation.consolidated_line_ids.filtered(
                    lambda l: l.product_id.type in ['product', 'consu']
                )
                
                # Create wizard line values
                wizard_line_vals = []
                for line in consolidated_lines:
                    # Get inventory rule for safety stock and reorder point
                    rule = self.env['scm.inventory.rule'].get_applicable_rule(
                        line.product_id, 
                        consolidation.warehouse_id
                    )
                    
                    # Get stock location
                    stock_location = consolidation.warehouse_id.lot_stock_id
                    
                    # Calculate incoming quantity (moves to the stock location)
                    incoming_moves = self.env['stock.move'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_dest_id', '=', stock_location.id),
                        ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
                    ])
                    incoming_qty = sum(incoming_moves.mapped('product_uom_qty'))
                    
                    # Calculate outgoing quantity (moves from the stock location)
                    outgoing_moves = self.env['stock.move'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_id', '=', stock_location.id),
                        ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
                    ])
                    outgoing_qty = sum(outgoing_moves.mapped('product_uom_qty'))
                    
                    wizard_line_vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'consolidated_line_id': line.id,
                        'available_qty': line.available_quantity,
                        'incoming_qty': incoming_qty,
                        'outgoing_qty': outgoing_qty,
                        'safety_stock_qty': rule.safety_stock_qty if rule else 0.0,
                        'reorder_point': rule.reorder_point if rule else 0.0,
                        'inventory_notes': line.notes or '',
                    }))
                
                # Set values directly in res
                res.update({
                    'session_id': consolidation.id,
                    'include_critical_only': any(wl[2].get('available_qty', 0) < wl[2].get('safety_stock_qty', 0) for wl in wizard_line_vals),
                    'line_ids': wizard_line_vals
                })
        return res

class ValidateInventoryWizardLine(models.TransientModel):
    _name = 'validate.inventory.wizard.line'
    _description = 'Inventory Validation Wizard Line'

    wizard_id = fields.Many2one('validate.inventory.wizard', string='Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    consolidated_line_id = fields.Many2one('scm.consolidated.pr.line', string='Consolidated Line')
    
    # Inventory fields
    required_quantity = fields.Float(
        string='Required Quantity',
        compute='_compute_required_quantity',
        store=True,
        digits='Product Unit of Measure',
        help='Total quantity required from consolidated purchase requests'
    )
    available_qty = fields.Float(string='Available Quantity', digits='Product Unit of Measure')
    incoming_qty = fields.Float(string='Incoming Quantity', digits='Product Unit of Measure')
    outgoing_qty = fields.Float(string='Outgoing Quantity', digits='Product Unit of Measure')
    forecasted_qty = fields.Float(
        string='Forecasted Quantity',
        compute='_compute_forecasted_qty',
        digits='Product Unit of Measure',
        help='Available quantity + incoming quantity - outgoing quantity'
    )
    safety_stock_qty = fields.Float(string='Safety Stock', digits='Product Unit of Measure')
    reorder_point = fields.Float(string='Reorder Point', digits='Product Unit of Measure')
    inventory_status = fields.Selection([
        ('ok', 'OK'),
        ('below_safety', 'Below Safety Stock'),
        ('stockout', 'Stockout'),
        ('below_reorder', 'Below Reorder Point'),
        ('excess', 'Excess'),
        ('sufficient', 'Sufficient'),
        ('partial', 'Partial'),
        ('insufficient', 'Insufficient')
    ], string='Inventory Status', compute='_compute_inventory_status', store=True)
    
    # Exception handling fields
    inventory_exception = fields.Boolean(string='Has Exception', default=False)
    exception_approved_by = fields.Many2one('res.users', string='Approved By')
    exception_approval_date = fields.Datetime(string='Approval Date')
    inventory_notes = fields.Text(string='Notes')
    is_critical = fields.Boolean(string='Critical Item', compute='_compute_is_critical', store=True)
    
    # Quantity to purchase field
    quantity_to_purchase = fields.Float(
        string='Quantity to Purchase',
        compute='_compute_quantity_to_purchase',
        store=True,
        digits='Product Unit of Measure',
        help='Quantity that needs to be purchased based on required quantity and available quantity'
    )
    
    @api.depends('consolidated_line_id.total_quantity')
    def _compute_required_quantity(self):
        for line in self:
            if line.consolidated_line_id and line.consolidated_line_id.total_quantity:
                line.required_quantity = line.consolidated_line_id.total_quantity
            else:
                line.required_quantity = 0.0
    
    @api.depends('product_id', 'wizard_id.session_id.warehouse_id')
    def _compute_incoming_outgoing_qty(self):
        for line in self:
            if not line.product_id or not line.wizard_id.session_id.warehouse_id:
                line.incoming_qty = 0.0
                line.outgoing_qty = 0.0
                continue
                
            warehouse = line.wizard_id.session_id.warehouse_id
            stock_location = warehouse.lot_stock_id
            
            if not stock_location:
                line.incoming_qty = 0.0
                line.outgoing_qty = 0.0
                continue
                
            # Calculate incoming quantity (moves to the stock location)
            incoming_moves = self.env['stock.move'].search([
                ('product_id', '=', line.product_id.id),
                ('location_dest_id', '=', stock_location.id),
                ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
            ])
            line.incoming_qty = sum(incoming_moves.mapped('product_uom_qty'))
            
            # Calculate outgoing quantity (moves from the stock location)
            outgoing_moves = self.env['stock.move'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', stock_location.id),
                ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
            ])
            line.outgoing_qty = sum(outgoing_moves.mapped('product_uom_qty'))
            
            _logger.info(f"Product {line.product_id.name}: Incoming={line.incoming_qty}, Outgoing={line.outgoing_qty}")
    
    @api.depends('available_qty', 'incoming_qty', 'outgoing_qty')
    def _compute_forecasted_qty(self):
        for line in self:
            line.forecasted_qty = line.available_qty + line.incoming_qty - line.outgoing_qty
            _logger.info(f"Product {line.product_id.name}: Available={line.available_qty}, Forecasted={line.forecasted_qty}")
    
    @api.depends('available_qty', 'safety_stock_qty', 'reorder_point', 'required_quantity')
    def _compute_inventory_status(self):
        for line in self:
            _logger.info(f"Computing inventory status for line {line.id}")
            _logger.info(f"Available qty: {line.available_qty}, Safety stock: {line.safety_stock_qty}, Reorder point: {line.reorder_point}")
            
            if not line.product_id:
                line.inventory_status = False
                continue
                
            if line.product_id.type == 'service':
                line.inventory_status = 'ok'
                continue
                
            if line.available_qty <= 0:
                line.inventory_status = 'stockout'
            elif line.available_qty < line.safety_stock_qty:
                line.inventory_status = 'below_safety'
            elif line.available_qty < line.reorder_point:
                line.inventory_status = 'below_reorder'
            elif line.available_qty > (line.safety_stock_qty * 2):
                line.inventory_status = 'excess'
            else:
                line.inventory_status = 'ok'
                
            _logger.info(f"Computed inventory status: {line.inventory_status}")
    
    @api.depends('inventory_status')
    def _compute_is_critical(self):
        for line in self:
            # Critical items are those with stockout or below safety stock
            line.is_critical = line.inventory_status in ['stockout', 'below_safety']
    
    @api.depends('consolidated_line_id.total_quantity', 'available_qty')
    def _compute_quantity_to_purchase(self):
        for line in self:
            if line.consolidated_line_id and line.consolidated_line_id.total_quantity:
                line.quantity_to_purchase = max(0, line.consolidated_line_id.total_quantity - line.available_qty)
            else:
                line.quantity_to_purchase = 0.0
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in fields_list and self.env.context.get('active_id'):
            session = self.env['scm.pr.consolidation.session'].browse(self.env.context.get('active_id'))
            if session.consolidated_line_ids:
                line_vals = []
                for line in session.consolidated_line_ids:
                    # Get inventory levels
                    available_qty = line.product_id.with_context(
                        location=session.warehouse_id.lot_stock_id.id
                    ).qty_available
                    
                    # Get inventory rule
                    rule = self.env['scm.inventory.rule'].get_applicable_rule(
                        line.product_id, 
                        session.warehouse_id
                    )
                    
                    # Calculate expected receipt (incoming moves)
                    stock_location = session.warehouse_id.lot_stock_id
                    incoming_moves = self.env['stock.move'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_dest_id', '=', stock_location.id),
                        ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
                    ])
                    incoming_qty = sum(incoming_moves.mapped('product_uom_qty'))
                    
                    # Calculate outgoing quantity (moves from the stock location)
                    outgoing_moves = self.env['stock.move'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_id', '=', stock_location.id),
                        ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])
                    ])
                    outgoing_qty = sum(outgoing_moves.mapped('product_uom_qty'))
                    
                    # Calculate available quantity including incoming and outgoing
                    available_qty = available_qty + incoming_qty - outgoing_qty
                    
                    line_vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'consolidated_line_id': line.id,
                        'available_qty': available_qty,
                        'safety_stock_qty': rule.safety_stock_qty if rule else 0.0,
                        'reorder_point': rule.reorder_point if rule else 0.0,
                    }))
                
                if line_vals:
                    res['line_ids'] = line_vals
        return res

class RejectInventoryWizard(models.TransientModel):
    _name = 'reject.inventory.wizard'
    _description = 'Reject Inventory Validation Wizard'
    
    consolidation_id = fields.Many2one('scm.pr.consolidation.session', 'Consolidation', required=True)
    rejection_reason = fields.Text('Rejection Reason', required=True)
    
    def action_reject(self):
        """Reject inventory validation with reason"""
        self.ensure_one()
        
        if not self.consolidation_id:
            raise UserError(_("No consolidation selected."))
        
        # Update consolidation
        self.consolidation_id.write({
            'inventory_status': 'rejected',
            'inventory_validation_notes': self.rejection_reason,
            'pending_approval': False,
            # Keep state as 'inventory_validation' to allow resubmission
        })
        
        # Log message in chatter
        self.consolidation_id.message_post(
            body=_("Inventory validation rejected by %s. Reason: %s") % (
                self.env.user.name, self.rejection_reason
            ),
            subtype_id=self.env.ref('mail.mt_note').id
        )
        
        return {'type': 'ir.actions.act_window_close'}