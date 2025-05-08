from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ConsolidationChangeLog(models.Model):
    _name = 'scm.consolidation.change.log'
    _description = 'Consolidation Change Log'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True
    )
    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',
        string='Consolidation Session',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    change_type = fields.Selection([
        ('pr', 'Purchase Request'),
        ('inventory', 'Inventory'),
        ('po', 'Purchase Order')
    ], string='Change Type', required=True, tracking=True)
    
    change_subtype = fields.Selection([
        ('pr_added', 'PR Added'),
        ('pr_modified', 'PR Modified'),
        ('pr_deleted', 'PR Deleted'),
        ('stock_change', 'Stock Level Change'),
        ('reserved_change', 'Reserved Quantity Change'),
        ('incoming_change', 'Incoming Quantity Change'),
        ('po_status', 'PO Status Change'),
        ('po_quantity', 'PO Quantity Change'),
        ('po_delivery', 'PO Delivery Date Change'),
        ('po_cancelled', 'PO Cancelled')
    ], string='Change Subtype', required=True, tracking=True)
    
    record_id = fields.Integer(string='Record ID', required=True)
    record_model = fields.Char(string='Record Model', required=True)
    record_name = fields.Char(string='Record Name', required=True)
    
    old_value = fields.Char(string='Old Value', tracking=True)
    new_value = fields.Char(string='New Value', tracking=True)
    
    impact_severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Impact Severity', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assessed', 'Impact Assessed'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    notes = fields.Text(string='Notes', tracking=True)
    resolution_notes = fields.Text(string='Resolution Notes', tracking=True)
    resolved_by = fields.Many2one('res.users', string='Resolved By', tracking=True)
    resolved_date = fields.Datetime(string='Resolved Date', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('scm.consolidation.change.log') or _('New')
        return super().create(vals_list)
    
    def action_assess_impact(self):
        """Assess the impact of the change and update severity"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft changes can be assessed.'))
            
        # Calculate impact based on change type and values
        impact = self._calculate_impact()
        self.write({
            'impact_severity': impact,
            'state': 'assessed'
        })
        
        # Notify relevant users
        self._notify_impact_assessment()
    
    def action_resolve(self):
        """Mark the change as resolved"""
        self.ensure_one()
        if self.state != 'assessed':
            raise UserError(_('Only assessed changes can be resolved.'))
            
        self.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Datetime.now()
        })
        
        # Update related records based on resolution
        self._apply_resolution()
        
        # Notify about resolution
        self._notify_resolution()
    
    def _calculate_impact(self):
        """Calculate the impact severity of the change"""
        # Default to medium impact
        impact = 'medium'
        
        try:
            if self.change_type == 'pr':
                # For PR changes, check quantity changes
                old_qty = float(self.old_value or 0)
                new_qty = float(self.new_value or 0)
                qty_diff = abs(new_qty - old_qty)
                
                if qty_diff > 1000:
                    impact = 'critical'
                elif qty_diff > 500:
                    impact = 'high'
                elif qty_diff > 100:
                    impact = 'medium'
                else:
                    impact = 'low'
                    
            elif self.change_type == 'inventory':
                # For inventory changes, check stock level impact
                old_stock = float(self.old_value or 0)
                new_stock = float(self.new_value or 0)
                stock_diff = abs(new_stock - old_stock)
                
                if new_stock <= 0:
                    impact = 'critical'
                elif stock_diff > 500:
                    impact = 'high'
                elif stock_diff > 100:
                    impact = 'medium'
                else:
                    impact = 'low'
                    
            elif self.change_type == 'po':
                # For PO changes, check status and quantity changes
                if self.change_subtype == 'po_cancelled':
                    impact = 'critical'
                elif self.change_subtype == 'po_quantity':
                    old_qty = float(self.old_value or 0)
                    new_qty = float(self.new_value or 0)
                    qty_diff = abs(new_qty - old_qty)
                    
                    if qty_diff > 1000:
                        impact = 'critical'
                    elif qty_diff > 500:
                        impact = 'high'
                    elif qty_diff > 100:
                        impact = 'medium'
                    else:
                        impact = 'low'
                        
        except (ValueError, TypeError):
            _logger.warning("Error calculating impact for change log %s", self.name)
            
        return impact
    
    def _notify_impact_assessment(self):
        """Notify relevant users about impact assessment"""
        template = self.env.ref('scm_procurement.mail_template_consolidation_change_impact')
        if template:
            template.send_mail(self.id, force_send=True)
    
    def _notify_resolution(self):
        """Notify about change resolution"""
        template = self.env.ref('scm_procurement.mail_template_consolidation_change_resolved')
        if template:
            template.send_mail(self.id, force_send=True)
    
    def _apply_resolution(self):
        """Apply the resolution to related records"""
        if self.change_type == 'pr':
            self._update_pr_data()
        elif self.change_type == 'inventory':
            self._update_inventory_data()
        elif self.change_type == 'po':
            self._update_po_data()
    
    def _update_pr_data(self):
        """Update PR related data after resolution"""
        # Implementation will depend on specific PR update requirements
        pass
    
    def _update_inventory_data(self):
        """Update inventory related data after resolution"""
        # Implementation will depend on specific inventory update requirements
        pass
    
    def _update_po_data(self):
        """Update PO related data after resolution"""
        # Implementation will depend on specific PO update requirements
        pass 