from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'
    _description = 'Purchase Agreement (Blanket Order)'

    consolidated_line_ids = fields.One2many(
        'scm.consolidated.pr.line',
        'requisition_id',
        string='Consolidated Lines'
    )
    
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Notes')
    
    def action_activate(self):
        for order in self:
            if order.state == 'draft':
                order.state = 'active'
    
    def action_cancel(self):
        for order in self:
            if order.state in ['draft', 'active']:
                order.state = 'cancelled'
    
    def action_expire(self):
        for order in self:
            if order.state == 'active':
                order.state = 'expired'
    
    def action_reset_to_draft(self):
        for order in self:
            if order.state == 'cancelled':
                order.state = 'draft'
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for order in self:
            if order.date_start and order.date_end and order.date_start > order.date_end:
                raise ValidationError(_('End date must be greater than start date.'))
    
    @api.depends('line_ids.price_subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(order.line_ids.mapped('price_subtotal'))


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'
    _description = 'Purchase Agreement Line'

    consolidated_line_id = fields.Many2one(
        'scm.consolidated.pr.line',
        string='Consolidated Line',
        tracking=True
    )
    
    price_unit = fields.Float(string='Unit Price', required=True)
    min_qty = fields.Float(string='Minimum Quantity', required=True)
    max_qty = fields.Float(string='Maximum Quantity', required=True)
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_subtotal', store=True)
    currency_id = fields.Many2one(related='requisition_id.currency_id', string='Currency', store=True)
    
    @api.depends('price_unit', 'product_qty')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.product_qty
    
    @api.constrains('min_qty', 'max_qty')
    def _check_quantities(self):
        for line in self:
            if line.min_qty and line.max_qty and line.min_qty > line.max_qty:
                raise ValidationError(_('Maximum quantity must be greater than minimum quantity.')) 