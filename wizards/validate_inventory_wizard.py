# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
            
            lines_with_receipts = wizard.line_ids.filtered(
                lambda l: l.expected_receipt_date
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
                        line.current_stock = current_stock  # Actual on-hand quantity
                        line.available_qty = current_stock + incoming_qty - outgoing_qty  # Forecast quantity
    
    def action_validate_inventory(self):
        self.ensure_one()
        
        # Validate all lines
        for line in self.line_ids:
            if line.inventory_exception and not line.exception_approved_by:
                raise UserError(_('All inventory exceptions must be approved before proceeding.'))
        
        # Update safety stock levels if requested
        if self.update_safety_stock:
            self._update_safety_stock_levels()
        
        # Process critical and non-critical items
        critical_lines = self.line_ids.filtered(lambda l: l.is_critical)
        non_critical_lines = self.line_ids.filtered(lambda l: not l.is_critical)
        
        # Auto-approve non-critical items
        for line in non_critical_lines:
            line.write({
                'inventory_exception': False,
                'exception_approved_by': self.env.user.id,
                'exception_approval_date': fields.Datetime.now(),
            })
        
        # Create activities for critical items
        if critical_lines:
            self._create_critical_items_activities(critical_lines)
        
        # Update session state
        self.session_id.write({
            'state': 'validated',
            'inventory_validation_date': fields.Datetime.now(),
            'inventory_validated_by': self.env.user.id,
            'inventory_notes': self.notes,
        })
        
        return {'type': 'ir.actions.act_window_close'}
    
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
                    wizard_line_vals.append({
                        'product_id': line.product_id.id,
                        'uom_id': line.product_uom_id.id,
                        'current_stock': line.available_quantity,
                        'required_qty': line.total_quantity,
                        'available_qty': line.available_quantity,
                        'notes': line.notes or '',
                    })
                
                res['line_ids'] = [(0, 0, vals) for vals in wizard_line_vals]
                res['session_id'] = consolidation.id
                res['include_critical_only'] = True
        return res

class ValidateInventoryWizardLine(models.TransientModel):
    _name = 'validate.inventory.wizard.line'
    _description = 'Inventory Validation Wizard Line'

    wizard_id = fields.Many2one('validate.inventory.wizard', string='Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    consolidated_line_id = fields.Many2one('scm.consolidated.pr.line', string='Consolidated Line')
    
    # Inventory fields
    available_qty = fields.Float(string='Available Quantity', digits='Product Unit of Measure')
    safety_stock_qty = fields.Float(string='Safety Stock', digits='Product Unit of Measure')
    reorder_point = fields.Float(string='Reorder Point', digits='Product Unit of Measure')
    inventory_status = fields.Selection([
        ('ok', 'OK'),
        ('below_safety', 'Below Safety Stock'),
        ('stockout', 'Stockout')
    ], string='Inventory Status', compute='_compute_inventory_status', store=True)
    
    # Exception handling fields
    inventory_exception = fields.Boolean(string='Has Exception', default=False)
    exception_approved_by = fields.Many2one('res.users', string='Approved By')
    exception_approval_date = fields.Datetime(string='Approval Date')
    inventory_notes = fields.Text(string='Notes')
    is_critical = fields.Boolean(string='Critical Item', compute='_compute_is_critical', store=True)
    
    @api.depends('available_qty', 'safety_stock_qty')
    def _compute_inventory_status(self):
        for line in self:
            if line.available_qty <= 0:
                line.inventory_status = 'stockout'
            elif line.available_qty < line.safety_stock_qty:
                line.inventory_status = 'below_safety'
            else:
                line.inventory_status = 'ok'
    
    @api.depends('inventory_status')
    def _compute_is_critical(self):
        for line in self:
            line.is_critical = line.inventory_status in ['stockout', 'below_safety']
    
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