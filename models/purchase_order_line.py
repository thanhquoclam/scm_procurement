from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # Add field for blanket order line reference
    blanket_order_line_id = fields.Many2one(
        'scm.blanket.order.line',
        string='Blanket Order Line',
        tracking=True,
        help="Reference to the blanket order line if this PO line was created from a blanket order"
    )
    
    # Add field to indicate if this PO line was created from a blanket order
    is_from_blanket_order = fields.Boolean(
        string='From Blanket Order',
        compute='_compute_is_from_blanket_order',
        store=True
    )
    
    @api.depends('blanket_order_line_id')
    def _compute_is_from_blanket_order(self):
        for line in self:
            line.is_from_blanket_order = bool(line.blanket_order_line_id)
    
    # Override the standard price computation to consider blanket order prices
    @api.onchange('product_id', 'product_qty')
    def _onchange_product_id(self):
        result = super(PurchaseOrderLine, self)._onchange_product_id()
        
        # Check if there's a blanket order line with a specific price
        if self.order_id.blanket_order_id and self.product_id:
            blanket_line = self.env['scm.blanket.order.line'].search([
                ('blanket_order_id', '=', self.order_id.blanket_order_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            
            if blanket_line:
                # Use the blanket order price
                self.price_unit = blanket_line.price_unit
                self.blanket_order_line_id = blanket_line.id
                
                # Check if quantity is within min/max limits
                if self.product_qty < blanket_line.min_qty:
                    return {
                        'warning': {
                            'title': _('Quantity Below Minimum'),
                            'message': _('The quantity is below the minimum quantity (%s) specified in the blanket order.') % blanket_line.min_qty
                        }
                    }
                elif self.product_qty > blanket_line.max_qty:
                    return {
                        'warning': {
                            'title': _('Quantity Above Maximum'),
                            'message': _('The quantity is above the maximum quantity (%s) specified in the blanket order.') % blanket_line.max_qty
                        }
                    }
        
        return result 