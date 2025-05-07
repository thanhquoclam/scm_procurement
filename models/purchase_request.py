# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    name = fields.Char('Request Reference', required=True, copy=False, readonly=True, default='New')
    requester_id = fields.Many2one(
        'res.users', 
        string='Requester',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    department = fields.Char(
        string='Department',
        required=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('consolidated', 'Consolidated'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.model
    def _get_fulfillment_status_selection(self):
        return [
            ('not_included', 'Not Included'),
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('partially_fulfilled', 'Partially Fulfilled'),
            ('fulfilled', 'Fulfilled'),
            ('cancelled', 'Cancelled')
        ]
    
    fulfillment_status = fields.Selection(
        selection='_get_fulfillment_status_selection',
        string='Fulfillment Status', 
        compute='_compute_fulfillment_status', 
        store=True
    )
    
    expected_fulfillment_date = fields.Date(
        string='Expected Fulfillment Date', 
        compute='_compute_expected_fulfillment_date'
    )
    
    consolidation_count = fields.Integer(
        string='Consolidations',
        compute='_compute_consolidation_count'
    )

    consolidation_ids = fields.Many2many(
        comodel_name='scm.pr.consolidation.session',
        relation='scm_pr_consolidation_request_rel',
        column1='request_id',
        column2='consolidation_id',
        string='Consolidation Sessions',
        tracking=True
    )
    
    notes = fields.Text(
        string='Notes',
        tracking=True,
        help="Additional notes and remarks for this request"
    )
    
    @api.depends('consolidation_ids')
    def _compute_consolidation_count(self):
        for record in self:
            record.consolidation_count = len(record.consolidation_ids)
    
    @api.depends('line_ids.fulfillment_status')
    def _compute_fulfillment_status(self):
        for request in self:
            if not request.consolidation_ids:
                request.fulfillment_status = 'not_included'
                continue
                
            line_states = request.line_ids.mapped('fulfillment_status')
            if not line_states or all(state == 'not_included' for state in line_states):
                request.fulfillment_status = 'not_included'
            elif all(state == 'fulfilled' for state in line_states):
                request.fulfillment_status = 'fulfilled'
            elif any(state == 'in_progress' for state in line_states):
                request.fulfillment_status = 'in_progress'
            elif any(state == 'partially_fulfilled' for state in line_states):
                request.fulfillment_status = 'partially_fulfilled'
            elif any(state == 'pending' for state in line_states):
                request.fulfillment_status = 'pending'
            else:
                request.fulfillment_status = 'not_included'
    
    @api.depends('line_ids.expected_fulfillment_date')
    def _compute_expected_fulfillment_date(self):
        for request in self:
            dates = request.line_ids.mapped('expected_fulfillment_date')
            # Filter out False/None values
            dates = [d for d in dates if d]
            request.expected_fulfillment_date = max(dates) if dates else False
    
    def action_view_consolidations(self):
        self.ensure_one()
        return {
            'name': _('Consolidation Sessions'),
            'view_mode': 'tree,form',
            'res_model': 'scm.pr.consolidation.session',
            'domain': [('id', 'in', self.consolidation_ids.ids)],
            'type': 'ir.actions.act_window',
        }

    def action_submit(self):
        """Submit the purchase request for approval."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Cannot submit an empty purchase request."))
        return self.write({'state': 'to_approve'})

    def button_to_approve(self):
        """Submit the purchase request for approval."""
        return self.action_submit()

    def action_approve(self):
        """Approve the purchase request."""
        self.ensure_one()
        return self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now()
        })

    def action_reject(self):
        """Reject the purchase request."""
        self.ensure_one()
        return self.write({'state': 'rejected'})

    def action_reset(self):
        """Reset to draft state."""
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError(_("Only rejected requests can be reset to draft."))
        return self.write({'state': 'draft'})

    def action_cancel(self):
        """Cancel the purchase request."""
        self.ensure_one()
        if self.state in ['cancelled', 'consolidated']:
            raise UserError(_("Cannot cancel request in current state."))
        return self.write({'state': 'cancelled'})

    @api.constrains('state', 'line_ids')
    def _check_lines(self):
        """Ensure purchase request has lines before submission."""
        for request in self:
            if request.state != 'draft' and not request.line_ids:
                raise UserError(_("Cannot submit or approve an empty purchase request."))

    def unlink(self):
        """Control deletion of purchase requests based on user rights and state."""
        is_admin = self.env.user._is_admin() or \
                  self.env.user.has_group('base.group_system')
        for request in self:
            if not is_admin and request.state != 'draft':
                raise UserError(_("Only draft purchase requests can be deleted. Please contact your administrator for special cases."))
        return super(PurchaseRequest, self).unlink()

    def button_done(self):
        """Mark the purchase request as done."""
        self.ensure_one()
        return self.write({"state": "consolidated"})


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'
    
    @api.model
    def _get_fulfillment_status_selection(self):
        return [
            ('not_included', 'Not Included'),
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('partially_fulfilled', 'Partially Fulfilled'),
            ('fulfilled', 'Fulfilled'),
            ('cancelled', 'Cancelled')
        ]
    
    consolidated_line_ids = fields.Many2many(
        'scm.consolidated.pr.line',
        string='Consolidated Lines'
    )
    
    fulfillment_status = fields.Selection(
        selection='_get_fulfillment_status_selection',
        string='Fulfillment Status', 
        compute='_compute_fulfillment_status', 
        store=True
    )
    
    expected_fulfillment_date = fields.Date(
        string='Expected Fulfillment Date', 
        compute='_compute_expected_fulfillment_date'
    )
    
    @api.depends('consolidated_line_ids')
    def _compute_fulfillment_status(self):
        # This is a placeholder - in Phase 4, this will be based on fulfillment plans
        for line in self:
            if not line.consolidated_line_ids:
                line.fulfillment_status = 'not_included'
            else:
                # For now, just link it to the consolidated line state
                consolidated_states = line.consolidated_line_ids.mapped('state')
                if 'fulfilled' in consolidated_states:
                    line.fulfillment_status = 'fulfilled'
                elif 'po_created' in consolidated_states:
                    line.fulfillment_status = 'in_progress'
                elif 'po_suggested' in consolidated_states:
                    line.fulfillment_status = 'pending'
                elif 'validated' in consolidated_states:
                    line.fulfillment_status = 'pending'
                else:
                    line.fulfillment_status = 'not_included'
    
    @api.depends('consolidated_line_ids')
    def _compute_expected_fulfillment_date(self):
        # This is a placeholder - in Phase 4, this will be based on PO dates
        for line in self:
            line.expected_fulfillment_date = False
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('consolidated', 'Consolidated'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, required=True)

    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id',
        string='Product UOM Category'
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]",
        required=True
    )

    def unlink(self):
        """Control deletion of purchase request lines based on user rights and state."""
        is_admin = self.env.user._is_admin() or \
                  self.env.user.has_group('base.group_system')
        if is_admin:
            return models.Model.unlink(self)
            
        for line in self:
            if line.request_id and line.request_id.state != 'draft':
                raise UserError(_("You can only delete a purchase request line if the purchase request is in draft state."))
        return super(PurchaseRequestLine, self).unlink()