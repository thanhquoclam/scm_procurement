from odoo import models, fields, api, _

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # Add field for purchase agreement line reference
    requisition_line_id = fields.Many2one(
        'purchase.requisition.line',
        string='Purchase Agreement Line',
        tracking=True,
        help="Reference to the purchase agreement line if this PO line was created from a purchase agreement"
    )
    
    # Add field to indicate if this PO line was created from a purchase agreement
    is_from_agreement = fields.Boolean(
        string='From Purchase Agreement',
        compute='_compute_is_from_agreement',
        store=True
    )
    
    @api.depends('requisition_line_id')
    def _compute_is_from_agreement(self):
        for line in self:
            line.is_from_agreement = bool(line.requisition_line_id)
    
    # Override the standard price computation to consider purchase agreement prices
    @api.onchange('product_id', 'product_qty')
    def _onchange_product_id(self):
        result = super(PurchaseOrderLine, self)._onchange_product_id()
        
        # Check if there's a purchase agreement line with a specific price
        if self.order_id.requisition_id and self.product_id:
            agreement_line = self.env['purchase.requisition.line'].search([
                ('requisition_id', '=', self.order_id.requisition_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            
            if agreement_line:
                # Use the purchase agreement price
                self.price_unit = agreement_line.price_unit
                self.requisition_line_id = agreement_line.id
                
                # Check if quantity is within min/max limits
                if self.product_qty < agreement_line.min_qty:
                    return {
                        'warning': {
                            'title': _('Quantity Below Minimum'),
                            'message': _('The quantity is below the minimum quantity (%s) specified in the purchase agreement.') % agreement_line.min_qty
                        }
                    }
                elif self.product_qty > agreement_line.max_qty:
                    return {
                        'warning': {
                            'title': _('Quantity Above Maximum'),
                            'message': _('The quantity is above the maximum quantity (%s) specified in the purchase agreement.') % agreement_line.max_qty
                        }
                    }
        
        return result 