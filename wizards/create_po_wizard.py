# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreatePOWizard(models.TransientModel):
    _name = 'scm.create.po.wizard'
    _description = 'Create Purchase Orders from Validated Lines'

    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',
        string='Consolidation Session',
        required=True
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('supplier_rank', '>', 0)]
    )
    date_order = fields.Date(
        string='Order Date',
        default=fields.Date.context_today,
        required=True
    )
    notes = fields.Text(string='Notes')
    
    # Add field for blanket order selection
    blanket_order_id = fields.Many2one(
        'scm.blanket.order',
        string='Blanket Order',
        domain="[('partner_id', '=', vendor_id), ('state', '=', 'active')]",
        help="Select a blanket order to use its pricing and terms"
    )
    
    # Add field to show available blanket orders
    available_blanket_orders = fields.Many2many(
        'scm.blanket.order',
        string='Available Blanket Orders',
        compute='_compute_available_blanket_orders'
    )
    
    expected_receipts = fields.Integer('Items with Expected Receipts', compute='_compute_expected_receipts')
    
    @api.depends('vendor_id')
    def _compute_available_blanket_orders(self):
        for wizard in self:
            if wizard.vendor_id:
                wizard.available_blanket_orders = self.env['scm.blanket.order'].search([
                    ('partner_id', '=', wizard.vendor_id.id),
                    ('state', '=', 'active'),
                    ('date_start', '<=', fields.Date.today()),
                    ('date_end', '>=', fields.Date.today())
                ])
            else:
                wizard.available_blanket_orders = False
    
    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        if self.vendor_id:
            # Reset blanket order when vendor changes
            self.blanket_order_id = False
            
            # Check if there are active blanket orders for this vendor
            blanket_orders = self.env['scm.blanket.order'].search([
                ('partner_id', '=', self.vendor_id.id),
                ('state', '=', 'active'),
                ('date_start', '<=', fields.Date.today()),
                ('date_end', '>=', fields.Date.today())
            ])
            
            if blanket_orders:
                # If there's only one, select it automatically
                if len(blanket_orders) == 1:
                    self.blanket_order_id = blanket_orders[0].id
                return {
                    'warning': {
                        'title': _('Blanket Orders Available'),
                        'message': _('There are %d active blanket orders available for this vendor.') % len(blanket_orders)
                    }
                }
    
    def action_create_po(self):
        self.ensure_one()
        
        # Get validated lines for the selected vendor
        validated_lines = self.env['scm.consolidated.pr.line'].search([
            ('consolidation_id', '=', self.consolidation_id.id),
            ('state', '=', 'validated'),
            ('quantity_to_purchase', '>', 0),
            ('product_id.seller_ids.partner_id', '=', self.vendor_id.id)
        ])
        
        if not validated_lines:
            # Open NoPONeededWizard instead of raising an error
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'no.po.needed.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_consolidation_id': self.consolidation_id.id,
                    'default_message': _("No validated lines found for the selected vendor %s. No purchase order will be created.") % self.vendor_id.name
                }
            }
        
        # Create purchase order
        po_vals = {
            'partner_id': self.vendor_id.id,
            'date_order': self.date_order,
            'notes': self.notes,
            'consolidation_id': self.consolidation_id.id,
            'is_from_consolidation': True,
        }
        
        # Add blanket order reference if selected
        if self.blanket_order_id:
            po_vals['blanket_order_id'] = self.blanket_order_id.id
        
        purchase_order = self.env['purchase.order'].create(po_vals)
        
        # Create purchase order lines
        for line in validated_lines:
            # Check if product is in blanket order
            blanket_line = False
            if self.blanket_order_id:
                blanket_line = self.env['scm.blanket.order.line'].search([
                    ('blanket_order_id', '=', self.blanket_order_id.id),
                    ('product_id', '=', line.product_id.id)
                ], limit=1)
            
            # Prepare line values
            line_vals = {
                'order_id': purchase_order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_qty': line.quantity_to_purchase,
                'product_uom': line.product_id.uom_po_id.id,
                'price_unit': line.product_id.standard_price,
                'date_planned': fields.Datetime.now(),
            }
            
            # If blanket order line exists, use its price and reference
            if blanket_line:
                line_vals.update({
                    'price_unit': blanket_line.price_unit,
                    'blanket_order_line_id': blanket_line.id,
                })
                
                # Check quantity constraints
                if line.quantity_to_purchase < blanket_line.min_qty:
                    raise UserError(_(
                        "Product %s: Quantity %s is below the minimum quantity %s specified in the blanket order."
                    ) % (line.product_id.name, line.quantity_to_purchase, blanket_line.min_qty))
                
                if line.quantity_to_purchase > blanket_line.max_qty:
                    raise UserError(_(
                        "Product %s: Quantity %s is above the maximum quantity %s specified in the blanket order."
                    ) % (line.product_id.name, line.quantity_to_purchase, blanket_line.max_qty))
            
            # Create the line
            self.env['purchase.order.line'].create(line_vals)
        
        # Update consolidation session state
        self.consolidation_id.write({
            'state': 'po_created',
            'po_creation_date': fields.Date.today(),
            'po_created_by': self.env.user.id
        })
        
        # Return action to open the created PO
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
            'name': _('Purchase Order')
        }


class CreatePOWizardLine(models.TransientModel):
    _name = 'create.po.wizard.line'
    _description = 'Create Purchase Order Wizard Line'

    wizard_id = fields.Many2one('create.po.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    product_qty = fields.Float(string='Quantity', required=True)
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit


class NoPONeededWizard(models.TransientModel):
    _name = 'no.po.needed.wizard'
    _description = 'No Purchase Order Needed Wizard'

    consolidation_id = fields.Many2one('scm.pr.consolidation.session', string='Consolidation', required=True)
    message = fields.Text(string='Message', required=True)

    def action_confirm(self):
        self.ensure_one()
        # Update consolidation state to po_created without creating a PO
        self.consolidation_id.write({
            'state': 'po_created',
            'po_creation_date': fields.Datetime.now(),
            'notes': self.message
        })
        return {'type': 'ir.actions.act_window_close'} 