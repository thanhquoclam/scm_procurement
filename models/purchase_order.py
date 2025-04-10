from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',  # Updated model reference
        string='Consolidation Session',
        readonly=True,
        copy=False,
        help="Consolidation session that generated this purchase order"
    )
    consolidation_state = fields.Selection(
        # related='consolidation_id.state',
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('validated', 'Validated'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled')
        ],
        string='Consolidation Status',
        store=True,
        readonly=True
    )
    is_from_consolidation = fields.Boolean(
        compute='_compute_is_from_consolidation',
        store=True
    )

    # Add fields for blanket order reference
    blanket_order_id = fields.Many2one(
        'scm.blanket.order',
        string='Blanket Order',
        tracking=True,
        help="Reference to the blanket order if this PO was created from a blanket order"
    )
    
    # Add field to indicate if this PO was created from a blanket order
    is_from_blanket_order = fields.Boolean(
        string='From Blanket Order',
        compute='_compute_is_from_blanket_order',
        store=True
    )

    @api.depends('consolidation_id')
    def _compute_is_from_consolidation(self):
        for order in self:
            order.is_from_consolidation = bool(order.consolidation_id)

    @api.depends('blanket_order_id')
    def _compute_is_from_blanket_order(self):
        for order in self:
            order.is_from_blanket_order = bool(order.blanket_order_id)

    # Override the standard price computation to consider blanket order prices
    @api.depends('order_line.price_unit', 'order_line.product_qty')
    def _compute_amount_total(self):
        for order in self:
            amount_untaxed = 0.0
            amount_tax = 0.0
            
            for line in order.order_line:
                # Check if there's a blanket order line with a specific price
                if order.blanket_order_id:
                    blanket_line = self.env['scm.blanket.order.line'].search([
                        ('blanket_order_id', '=', order.blanket_order_id.id),
                        ('product_id', '=', line.product_id.id)
                    ], limit=1)
                    
                    if blanket_line:
                        # Use the blanket order price
                        line.price_unit = blanket_line.price_unit
                
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = amount_untaxed + amount_tax