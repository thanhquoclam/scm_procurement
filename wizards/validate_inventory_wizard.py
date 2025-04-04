# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ValidateInventoryWizard(models.TransientModel):
    _name = 'validate.inventory.wizard'
    _description = 'Validate Inventory Wizard'
    
    consolidation_id = fields.Many2one('scm.consolidation', 'Consolidation', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    line_ids = fields.One2many(
        'validate.inventory.wizard.line',
        'wizard_id',
        string='Items to Validate'
    )
    validation_notes = fields.Text('Validation Notes')
    
    include_critical_only = fields.Boolean('Critical Issues Only', default=True)
    auto_approve_non_critical = fields.Boolean('Auto-Approve Non-Critical Issues', default=True)
    request_manager_approval = fields.Boolean('Request Manager Approval for Critical Issues', default=True)
    update_safety_stock = fields.Boolean('Update Safety Stock Levels', default=False)
    
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
        """Filter lines based on criticality"""
        if self.include_critical_only:
            consolidation = self.consolidation_id
            if consolidation:
                critical_lines = consolidation.consolidated_line_ids.filtered(
                    lambda l: l.inventory_status in ['stockout', 'below_safety'] 
                    and l.product_id.type in ['product', 'consu']
                )
                self.line_ids = critical_lines
        else:
            consolidation = self.consolidation_id
            if consolidation:
                issue_lines = consolidation.consolidated_line_ids.filtered(
                    lambda l: l.inventory_status in ['stockout', 'below_safety', 'below_reorder'] 
                    and l.product_id.type in ['product', 'consu']
                )
                self.line_ids = issue_lines
    
    def action_validate_inventory(self):
        """Validate inventory and handle exceptions"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_("No lines to validate."))
        
        # Handle critical items
        critical_lines = self.line_ids.filtered(
            lambda l: l.inventory_status in ['stockout', 'below_safety']
        )
        
        # Handle non-critical items
        non_critical_lines = self.line_ids.filtered(
            lambda l: l.inventory_status not in ['stockout', 'below_safety']
        )
        
        # Auto-approve non-critical items if enabled
        if self.auto_approve_non_critical and non_critical_lines:
            for line in non_critical_lines:
                line.write({
                    'inventory_exception': True,
                    'exception_approved_by': self.env.user.id,
                    'exception_approval_date': fields.Datetime.now(),
                    'inventory_notes': _("Auto-approved: Below reorder point but not critical.")
                })
        
        # Update consolidation
        self.consolidation_id.write({
            'inventory_validation_notes': self.validation_notes,
            'pending_approval': self.request_manager_approval and bool(critical_lines),
            'inventory_status': 'in_progress',
        })
        
        # Request manager approval if needed
        if self.request_manager_approval and critical_lines:
            # Find users with inventory approval rights
            inventory_manager_group = self.env.ref('stock.group_stock_manager')
            inventory_managers = inventory_manager_group.users
            
            if inventory_managers:
                # Prepare email template
                template = self.env.ref('scm_procurement.mail_template_inventory_approval')
                
                # Send notification
                for manager in inventory_managers:
                    template.send_mail(
                        self.consolidation_id.id, 
                        force_send=True,
                        email_values={'email_to': manager.email}
                    )
        else:
            # Auto-approve if no manager approval needed
            self.consolidation_id.write({
                'inventory_validated': True,
                'inventory_validation_date': fields.Datetime.now(),
                'inventory_validated_by': self.env.user.id,
                'inventory_status': 'approved',
                'pending_approval': False,
            })
        
        # Update safety stock if requested
        if self.update_safety_stock:
            self._update_safety_stock_levels()
        
        # Log message in chatter
        self.consolidation_id.message_post(
            body=_("Inventory validation by %s:\n%s") % (
                self.env.user.name, self.validation_notes or 'No notes provided'
            ),
            subtype_id=self.env.ref('mail.mt_note').id
        )
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _update_safety_stock_levels(self):
        """Update safety stock levels based on validation"""
        inventory_rule_obj = self.env['scm.inventory.rule']
        
        for line in self.line_ids:
            # Find applicable rule
            rule = inventory_rule_obj.get_applicable_rule(line.product_id, self.warehouse_id)
            
            if rule:
                # Recalculate safety stock and reorder points
                rule.calculate_safety_stock()
                rule.calculate_reorder_point()
            else:
                # Create new rule with default values
                rule_vals = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'warehouse_id': self.warehouse_id.id,
                    'company_id': line.company_id.id,
                }
                
                new_rule = inventory_rule_obj.create(rule_vals)
                new_rule.calculate_safety_stock()
                new_rule.calculate_reorder_point()

class ValidateInventoryWizardLine(models.TransientModel):
    _name = 'validate.inventory.wizard.line'
    _description = 'Inventory Validation Line'

    wizard_id = fields.Many2one(
        'validate.inventory.wizard',
        string='Wizard'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    current_stock = fields.Float(
        string='Current Stock',
        readonly=True
    )
    required_qty = fields.Float(
        string='Required Quantity'
    )
    available_qty = fields.Float(
        string='Available Quantity'
    )
    notes = fields.Text(
        string='Notes'
    )

class RejectInventoryWizard(models.TransientModel):
    _name = 'reject.inventory.wizard'
    _description = 'Reject Inventory Validation Wizard'
    
    consolidation_id = fields.Many2one('scm.consolidation', 'Consolidation', required=True)
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