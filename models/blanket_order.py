from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date


class BlanketOrder(models.Model):
    _name = 'scm.blanket.order'
    _description = 'Blanket Purchase Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('supplier_rank', '>', 0)],
        tracking=True
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        tracking=True
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, required=True)
    
    line_ids = fields.One2many(
        'scm.blanket.order.line',
        'blanket_order_id',
        string='Order Lines',
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id'
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id'
    )
    notes = fields.Text(string='Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('scm.blanket.order') or _('New')
        return super(BlanketOrder, self).create(vals_list)
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for order in self:
            if order.date_start > order.date_end:
                raise ValidationError(_("End date cannot be earlier than start date."))
    
    @api.depends('line_ids.price_subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(order.line_ids.mapped('price_subtotal'))
    
    def action_activate(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Cannot activate a blanket order without any lines."))
        return self.write({'state': 'active'})
    
    def action_cancel(self):
        self.ensure_one()
        return self.write({'state': 'cancelled'})
    
    def action_expire(self):
        self.ensure_one()
        return self.write({'state': 'expired'})
    
    def action_reset_to_draft(self):
        self.ensure_one()
        if self.state != 'cancelled':
            raise UserError(_("Only cancelled blanket orders can be reset to draft."))
        return self.write({'state': 'draft'})
    
    @api.model
    def _cron_check_expired(self):
        """Cron job to check and expire blanket orders past their end date."""
        today = fields.Date.today()
        expired_orders = self.search([
            ('state', '=', 'active'),
            ('date_end', '<', today)
        ])
        if expired_orders:
            expired_orders.write({'state': 'expired'})


class BlanketOrderLine(models.Model):
    _name = 'scm.blanket.order.line'
    _description = 'Blanket Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    blanket_order_id = fields.Many2one(
        'scm.blanket.order',
        string='Blanket Order',
        required=True,
        ondelete='cascade',
        index=True
    )
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
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
        required=True
    )
    min_qty = fields.Float(
        string='Minimum Quantity',
        digits='Product Unit of Measure',
        required=True
    )
    max_qty = fields.Float(
        string='Maximum Quantity',
        digits='Product Unit of Measure',
        required=True
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_price_subtotal',
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='blanket_order_id.currency_id',
        string='Currency',
        store=True
    )
    notes = fields.Text(string='Notes')
    
    @api.constrains('min_qty', 'max_qty')
    def _check_quantities(self):
        for line in self:
            if line.min_qty > line.max_qty:
                raise ValidationError(_("Minimum quantity cannot be greater than maximum quantity."))
    
    @api.depends('price_unit', 'max_qty')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.max_qty 