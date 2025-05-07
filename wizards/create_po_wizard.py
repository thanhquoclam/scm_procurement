# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class CreatePOWizard(models.TransientModel):
    _name = 'scm.create.po.wizard'
    _description = 'Create Purchase Orders Wizard'

    consolidation_id = fields.Many2one('scm.pr.consolidation.session', required=True, readonly=True)
    date_order = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('scm.create.po.wizard.line', 'wizard_id', string='Lines')
    notes = fields.Text(string='Notes')
    
    # Summary fields
    total_lines = fields.Integer(compute='_compute_summary', store=True)
    total_vendors = fields.Integer(compute='_compute_summary', store=True)
    total_products = fields.Integer(compute='_compute_summary', store=True)
    total_amount = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')

    @api.depends('line_ids', 'line_ids.vendor_id', 'line_ids.product_id', 'line_ids.quantity_to_purchase', 'line_ids.price_unit')
    def _compute_summary(self):
        for wizard in self:
            wizard.total_lines = len(wizard.line_ids)
            wizard.total_vendors = len(wizard.line_ids.mapped('vendor_id'))
            wizard.total_products = len(wizard.line_ids.mapped('product_id'))
            wizard.total_amount = sum(line.quantity_to_purchase * line.price_unit for line in wizard.line_ids if line.price_unit)

    @api.model
    def create(self, vals):
        """Override create to ensure lines are created with all required fields."""
        if vals.get('line_ids'):
            for line_command in vals['line_ids']:
                if line_command[0] == 0:  # Create command
                    # Ensure product_id is set
                    if not line_command[2].get('product_id'):
                        consolidated_line = self.env['scm.consolidated.pr.line'].browse(
                            line_command[2].get('consolidated_line_id')
                        )
                        if consolidated_line and consolidated_line.product_id:
                            line_command[2]['product_id'] = consolidated_line.product_id.id
                    
                    # Ensure product_uom_id is set
                    if not line_command[2].get('product_uom_id'):
                        if line_command[2].get('consolidated_line_id'):
                            consolidated_line = self.env['scm.consolidated.pr.line'].browse(
                                line_command[2].get('consolidated_line_id')
                            )
                            if consolidated_line and consolidated_line.product_uom_id:
                                line_command[2]['product_uom_id'] = consolidated_line.product_uom_id.id
                        elif line_command[2].get('product_id'):
                            product = self.env['product.product'].browse(line_command[2].get('product_id'))
                            if product and product.uom_id:
                                line_command[2]['product_uom_id'] = product.uom_id.id
        return super().create(vals)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'scm.pr.consolidation.session':
            consolidation = self.env['scm.pr.consolidation.session'].browse(self.env.context.get('active_id'))
            if consolidation:
                # Get lines with quantity to purchase > 0
                lines_to_purchase = consolidation.consolidated_line_ids.filtered(lambda l: l.quantity_to_purchase > 0)
                
                wizard_lines = []
                for line in lines_to_purchase:
                    if not line.product_id:
                        continue
                    
                    # Ensure product_uom_id is set
                    product_uom_id = line.product_uom_id.id if line.product_uom_id else line.product_id.uom_id.id
                    
                    wizard_lines.append((0, 0, {
                        'consolidated_line_id': line.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': product_uom_id,
                        'quantity_to_purchase': line.quantity_to_purchase,
                        'price_unit': line.purchase_price,
                        'vendor_id': line.suggested_vendor_id.id if line.suggested_vendor_id else False,
                    }))
                
                res.update({
                    'consolidation_id': consolidation.id,
                    'line_ids': wizard_lines,
                })
        return res

    def action_auto_assign_vendors(self):
        """Auto-assign vendors and agreements to lines based on purchase history and active agreements."""
        self.ensure_one()
        
        for line in self.line_ids:
            if line.vendor_id:
                continue  # Skip if vendor already assigned
                
            # First try to find a vendor from active agreements
            agreements = self.env['purchase.requisition'].search([
                ('state', 'in', ['ongoing', 'open']),
                ('line_ids.product_id', '=', line.product_id.id)
            ])
            
            if agreements:
                # Take the most recent agreement's vendor
                latest_agreement = agreements.sorted(lambda a: a.create_date, reverse=True)[0]
                line.vendor_id = latest_agreement.vendor_id.id
                continue
            
            # If no agreement found, try to find from purchase history
            purchase_lines = self.env['purchase.order.line'].search([
                ('product_id', '=', line.product_id.id),
                ('order_id.state', 'in', ['purchase', 'done'])
            ], order='create_date desc', limit=1)
            
            if purchase_lines:
                line.vendor_id = purchase_lines.order_id.partner_id.id

        return {'type': 'ir.actions.act_window_close'}

    def action_create_pos(self):
        self.ensure_one()
        
        # Check if all lines have vendors assigned
        if not all(line.vendor_id for line in self.line_ids):
            raise UserError(_("Please assign vendors to all lines before creating purchase orders."))
        
        # Group lines by vendor
        lines_by_vendor = {}
        for line in self.line_ids:
            if line.vendor_id not in lines_by_vendor:
                lines_by_vendor[line.vendor_id] = []
            lines_by_vendor[line.vendor_id].append(line)
        
        # Create PO for each vendor
        created_pos = self.env['purchase.order']
        for vendor, lines in lines_by_vendor.items():
            po_vals = {
                'partner_id': vendor.id,
                'date_order': self.date_order,
                'currency_id': self.currency_id.id,
                'origin': self.consolidation_id.name,
                'consolidation_id': self.consolidation_id.id,  # Link to consolidation
                'order_line': [],
            }
            
            for line in lines:
                po_line_vals = {
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name,
                    'product_uom_qty': line.quantity_to_purchase,
                    'product_uom': line.product_uom_id.id,
                    'price_unit': line.price_unit,
                    'date_planned': self.date_order,
                }
                
                if line.agreement_id:
                    po_vals['requisition_id'] = line.agreement_id.id
                    agreement_line = line.agreement_id.line_ids.filtered(
                        lambda l: l.product_id == line.product_id
                    )
                    if agreement_line:
                        po_line_vals['price_unit'] = agreement_line[0].price_unit
                
                po_vals['order_line'].append((0, 0, po_line_vals))
            
            po = self.env['purchase.order'].create(po_vals)
            created_pos |= po
            
            # Update consolidation lines with the created PO
            for line in lines:
                po_line = po.order_line.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if po_line:
                    line.consolidated_line_id.write({
                        'purchase_order_id': po.id,
                        'purchase_line_id': po_line.id,
                        'state': 'po_created'
                    })
        
        # Update consolidation state to po_created
        self.consolidation_id.write({
            'state': 'po_created',
            'po_creation_date': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_pos.ids)],
        }

    @api.constrains('line_ids')
    def _check_line_ids(self):
        for wizard in self:
            if not wizard.line_ids:
                raise ValidationError(_("You must have at least one line to create purchase orders."))
            
            for line in wizard.line_ids:
                if not line.consolidated_line_id:
                    raise ValidationError(_("All lines must have a valid consolidated line. Please close this wizard and try again."))
                if not line.product_id:
                    raise ValidationError(_("All lines must have a product assigned."))
                if not line.vendor_id:
                    raise ValidationError(_("All lines must have a vendor assigned."))


class CreatePOWizardLine(models.TransientModel):
    _name = 'scm.create.po.wizard.line'
    _description = 'Create Purchase Order Wizard Line'

    wizard_id = fields.Many2one('scm.create.po.wizard', string='Wizard', required=True, ondelete='cascade')
    consolidated_line_id = fields.Many2one('scm.consolidated.pr.line', string='Consolidated Line', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, default=lambda self: self.env.context.get('default_product_id'))
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, default=lambda self: self._get_default_uom())
    quantity_to_purchase = fields.Float(string='Quantity to Purchase', digits='Product Unit of Measure')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, domain="[('supplier_rank', '>', 0)]")
    agreement_id = fields.Many2one('purchase.requisition', string='Agreement', domain="[('id', 'in', suggested_agreement_ids)]")
    requisition_line_id = fields.Many2one('purchase.requisition.line', string='Agreement Line')
    suggested_agreement_ids = fields.Many2many(
        'purchase.requisition', 
        string='Suggested Agreements',
        compute='_compute_suggested_agreements',
        store=True
    )
    agreement_count = fields.Integer(
        string='Available Agreements',
        compute='_compute_suggested_agreements',
        store=True
    )
    has_agreements = fields.Boolean(
        string='Has Agreements',
        compute='_compute_suggested_agreements',
        store=True
    )
    
    @api.depends('product_id', 'vendor_id')
    def _compute_suggested_agreements(self):
        for line in self:
            if not line.product_id:
                line.suggested_agreement_ids = False
                line.agreement_count = 0
                line.has_agreements = False
                continue

            _logger.info(f'Finding agreements for product: {line.product_id.display_name}')

            # First find all agreements that have this product in their lines
            domain = [
                ('product_id', '=', line.product_id.id),
            ]
            
            # Add condition for end date: either no end date or end date >= today
            today = fields.Date.today()
            domain.append('|')
            domain.append(('requisition_id.date_end', '=', False))
            domain.append(('requisition_id.date_end', '>=', today))
            
            requisition_lines = self.env['purchase.requisition.line'].search(domain)
            agreements = requisition_lines.mapped('requisition_id')
            
            # If vendor is selected, filter agreements by vendor
            if line.vendor_id:
                agreements = agreements.filtered(lambda a: a.vendor_id == line.vendor_id)
            
            _logger.info(f'Found {len(agreements)} valid agreements for product {line.product_id.display_name}')
            if agreements:
                _logger.info(f'Agreement vendors: {agreements.mapped("vendor_id.name")}')
            
            line.suggested_agreement_ids = agreements
            line.agreement_count = len(agreements)
            line.has_agreements = bool(agreements)
            
            # If there's only one agreement and no agreement selected yet, select it
            if len(agreements) == 1 and not line.agreement_id:
                line.agreement_id = agreements.id
                line._onchange_agreement_id()
    
    @api.onchange('agreement_id')
    def _onchange_agreement_id(self):
        if self.agreement_id:
            # Set the vendor from the agreement if not set
            if not self.vendor_id:
                self.vendor_id = self.agreement_id.vendor_id.id
            
            if self.product_id:
                # Find matching line in the agreement
                requisition_line = self.env['purchase.requisition.line'].search([
                    ('requisition_id', '=', self.agreement_id.id),
                    ('product_id', '=', self.product_id.id)
                ], limit=1)
                
                if requisition_line:
                    self.requisition_line_id = requisition_line.id
                    self.price_unit = requisition_line.price_unit
                else:
                    self.requisition_line_id = False
        else:
            self.requisition_line_id = False
    
    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        if self.vendor_id:
            # Recompute suggested agreements when vendor changes
            self._compute_suggested_agreements()
            
            # Clear agreement if vendor doesn't match
            if self.agreement_id and self.agreement_id.vendor_id != self.vendor_id:
                self.agreement_id = False
                self.requisition_line_id = False
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_consolidated_line_id'):
            consolidated_line = self.env['scm.consolidated.pr.line'].browse(self.env.context.get('default_consolidated_line_id'))
            if consolidated_line:
                _logger.info(f'Initializing wizard line for product {consolidated_line.product_id.display_name}')
                
                # Get suggested vendor from consolidated line
                vendor_id = consolidated_line.suggested_vendor_id.id if consolidated_line.suggested_vendor_id else False
                
                # If no suggested vendor, try to find one from agreements
                if not vendor_id:
                    # Search for agreements with this product
                    agreements = self.env['purchase.requisition'].search([
                        ('state', 'in', ['active', 'done']),
                        ('date_end', '>=', fields.Date.today())
                    ])
                    
                    for agreement in agreements:
                        requisition_line = self.env['purchase.requisition.line'].search([
                            ('requisition_id', '=', agreement.id),
                            ('product_id', '=', consolidated_line.product_id.id)
                        ], limit=1)
                        
                        if requisition_line:
                            vendor_id = agreement.vendor_id.id
                            _logger.info(f'Found vendor {agreement.vendor_id.name} from agreement {agreement.name}')
                            break
                
                res.update({
                    'consolidated_line_id': consolidated_line.id,
                    'product_id': consolidated_line.product_id.id,
                    'product_uom_id': consolidated_line.product_uom_id.id,
                    'quantity_to_purchase': consolidated_line.quantity_to_purchase,
                    'price_unit': consolidated_line.purchase_price,
                    'vendor_id': vendor_id,
                })
                
                _logger.info(f'Initialized wizard line with vendor_id: {vendor_id}')
        elif self.env.context.get('default_product_id'):
            # Fallback to default_product_id from context if no consolidated line
            res['product_id'] = self.env.context.get('default_product_id')
        return res

    @api.model
    def _get_default_uom(self):
        """Get default UoM from consolidated line or product."""
        if self.env.context.get('default_consolidated_line_id'):
            consolidated_line = self.env['scm.consolidated.pr.line'].browse(
                self.env.context.get('default_consolidated_line_id')
            )
            if consolidated_line and consolidated_line.product_uom_id:
                return consolidated_line.product_uom_id.id
        
        # If no consolidated line or no UoM in consolidated line, try to get from product
        if self.env.context.get('default_product_id'):
            product = self.env['product.product'].browse(self.env.context.get('default_product_id'))
            if product and product.uom_id:
                return product.uom_id.id
        
        # Fallback to default purchase UoM
        return self.env['product.product']._get_default_uom_id()


class NoPONeededWizard(models.TransientModel):
    _name = 'no.po.needed.wizard'
    _description = 'No Purchase Order Needed Wizard'

    consolidation_id = fields.Many2one('scm.pr.consolidation.session', string='Consolidation', required=True)
    message = fields.Text(string='Message', required=True)

    def action_confirm(self):
        self.consolidation_id.write({'state': 'no_po_needed'})
        return {'type': 'ir.actions.act_window_close'} 