# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreatePOWizard(models.TransientModel):
    _name = 'create.po.wizard'
    _description = 'Create Purchase Orders Wizard'

    consolidation_id = fields.Many2one('scm.pr.consolidation.session', string='Consolidation', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    line_ids = fields.One2many('create.po.wizard.line', 'wizard_id', string='Lines to Create PO')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    date_order = fields.Date(string='Order Date', required=True, default=fields.Date.context_today)
    notes = fields.Text(string='Notes')

    @api.model
    def default_get(self, fields_list):
        res = super(CreatePOWizard, self).default_get(fields_list)
        if self.env.context.get('active_id'):
            consolidation = self.env['scm.pr.consolidation.session'].browse(self.env.context.get('active_id'))
            if consolidation:
                # Create wizard line values only for lines with positive quantity to purchase
                wizard_line_vals = []
                for line in consolidation.consolidated_line_ids:
                    if line.quantity_to_purchase > 0:  # Only include lines that need to be purchased
                        wizard_line_vals.append({
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom_id.id,
                            'product_qty': line.quantity_to_purchase,
                            'price_unit': line.purchase_price,
                            'price_subtotal': line.subtotal,
                        })
                
                # Always set the basic fields regardless of whether there are lines or not
                res.update({
                    'consolidation_id': consolidation.id,
                    'warehouse_id': consolidation.warehouse_id.id,
                    'date_order': fields.Date.context_today(self),
                    'line_ids': [(0, 0, vals) for vals in wizard_line_vals] if wizard_line_vals else []
                })
                
        return res

    @api.model
    def create(self, vals):
        # Check if we need to show the "No Purchase Needed" wizard
        if vals.get('no_lines_to_purchase'):
            # Remove the flag from vals
            vals.pop('no_lines_to_purchase')
            # Create the wizard record
            wizard = super(CreatePOWizard, self).create(vals)
            # Return action to open the "No Purchase Needed" wizard
            return {
                'type': 'ir.actions.act_window',
                'name': _('No Purchase Needed'),
                'res_model': 'no.po.needed.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_consolidation_id': wizard.consolidation_id.id,
                    'default_message': _("No lines need to be purchased. All products have sufficient inventory available. Do you want to proceed without creating a purchase order?")
                }
            }
        return super(CreatePOWizard, self).create(vals)

    def action_create_po(self):
        self.ensure_one()
        
        # Check if there are no lines to purchase
        if not self.line_ids:
            # Open the "No Purchase Needed" wizard
            return {
                'type': 'ir.actions.act_window',
                'name': _('No Purchase Needed'),
                'res_model': 'no.po.needed.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_consolidation_id': self.consolidation_id.id,
                    'default_message': _("No lines need to be purchased. All products have sufficient inventory available. Do you want to proceed without creating a purchase order?")
                }
            }

        # Create purchase order
        po_vals = {
            'partner_id': self.vendor_id.id,
            'date_order': self.date_order,
            'consolidation_id': self.consolidation_id.id,
            'notes': self.notes,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'product_qty': line.product_qty,
                'price_unit': line.price_unit,
            }) for line in self.line_ids]
        }
        
        po = self.env['purchase.order'].create(po_vals)
        
        # Update consolidation state
        self.consolidation_id.write({
            'state': 'po_created',
            'po_creation_date': fields.Datetime.now()
        })
        
        # Return action to view the created PO
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
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
            'po_creation_date': fields.Datetime.now()
        })
        return {'type': 'ir.actions.act_window_close'} 