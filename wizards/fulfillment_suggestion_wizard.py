from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FulfillmentSuggestionWizard(models.TransientModel):
    _name = 'scm.fulfillment.suggestion.wizard'
    _description = 'Fulfillment Suggestion Wizard'

    pr_line_ids = fields.Many2many(
        'purchase.request.line',
        string='PR Lines to Fulfill',
    )
    line_ids = fields.One2many(
        'scm.fulfillment.suggestion.wizard.line',
        'wizard_id',
        string='Fulfillment Suggestions',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            pr_lines = self.env['purchase.request.line'].browse(active_ids)
            res['pr_line_ids'] = [(6, 0, pr_lines.ids)]
            suggestion_lines = []
            for pr_line in pr_lines:
                suggestion = self._suggest_fulfillment(pr_line)
                suggestion_lines.append((0, 0, suggestion))
            res['line_ids'] = suggestion_lines
        return res

    def _suggest_fulfillment(self, pr_line):
        """Suggest fulfillment based on product availability and rules"""
        suggestion = {
            'source_type': 'purchase',
            'source_location_id': False,
            'destination_location_id': False,
            'planned_qty': pr_line.product_qty,
            'planned_start_date': fields.Date.today(),
            'planned_end_date': fields.Date.today(),
            'timeline': 'immediate',
            'note': False
        }
        
        # Get destination location from PR's company warehouse
        company = pr_line.request_id.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        if warehouse:
            dest_location = warehouse.lot_stock_id
            suggestion['destination_location_id'] = dest_location.id
            
            # Check if product is available in any internal location
            available_qty = self.env['stock.quant']._get_available_quantity(
                pr_line.product_id,
                dest_location
            )
            
            if available_qty >= pr_line.product_qty:
                suggestion.update({
                    'source_type': 'transfer',
                    'source_location_id': dest_location.id,
                    'timeline': 'immediate',
                    'note': 'Product available in stock'
                })
                return suggestion
        return suggestion

    def action_confirm(self):
        # Create fulfillment plans and actions based on user input
        for line in self.line_ids:
            pr_line = line.pr_line_id
            plan_vals = {
                'pr_line_id': pr_line.id,
                'planned_qty': line.planned_qty,
                'source_type': line.source_type,
                'source_location_id': line.source_location_id.id,
                'destination_location_id': line.destination_location_id.id,
                'planned_start_date': line.planned_start_date,
                'planned_end_date': line.planned_end_date,
                'timeline': line.timeline,
                'note': line.note,
            }
            plan = self.env['scm.pr.fulfillment.plan'].create(plan_vals)
            
            # Create fulfillment actions based on source type
            if line.source_type == 'stock':
                self._create_stock_move(plan, pr_line, line.planned_qty)
            elif line.source_type == 'transfer':
                self._create_internal_transfer(plan, pr_line, line.planned_qty)
            elif line.source_type == 'purchase':
                self._create_purchase_order(plan, pr_line, line.planned_qty)
        return {'type': 'ir.actions.act_window_close'}

    def _create_stock_move(self, plan, pr_line, qty):
        # Create a stock move for on-hand fulfillment
        product = pr_line.product_id
        dest_location = pr_line.request_id.company_id.warehouse_id.lot_stock_id
        move = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'name': product.display_name,
            'location_id': dest_location.id,  # On-hand at destination
            'location_dest_id': dest_location.id,
            'fulfillment_plan_id': plan.id,
            'origin': _('PR Fulfillment Plan %s') % plan.id,
        })
        plan.stock_move_ids = [(4, move.id)]
        plan.status = 'in_progress'
        plan.timeline = _('Stock move created for on-hand fulfillment.')

    def _create_internal_transfer(self, plan, pr_line, qty):
        # Create an internal transfer (stock picking)
        product = pr_line.product_id
        warehouse = pr_line.request_id.company_id.warehouse_id or self.env['stock.warehouse'].search([], limit=1)
        dest_location = warehouse.lot_stock_id
        all_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        candidate_locations = all_locations - dest_location
        source_location = False
        for loc in candidate_locations:
            available_qty = self.env['stock.quant']._get_available_quantity(product, loc)
            if available_qty >= qty:
                source_location = loc
                break
        if not source_location:
            raise UserError(_('No other location has enough stock for an internal transfer.'))
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'move_ids_without_package': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'name': product.display_name,
                'fulfillment_plan_id': plan.id,
            })],
            'origin': _('PR Fulfillment Plan %s') % plan.id,
            'fulfillment_plan_id': plan.id,
        })
        plan.transfer_ids = [(4, picking.id)]
        plan.status = 'in_progress'
        plan.timeline = _('Internal transfer created from %s to %s') % (source_location.display_name, dest_location.display_name)

    def _create_purchase_order(self, plan, pr_line, qty):
        # Create a purchase order for the required quantity
        product = pr_line.product_id
        partner = product.seller_ids and product.seller_ids[0].name or False
        if not partner:
            raise UserError(_('No vendor found for product %s') % product.display_name)
        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.display_name,
                'product_qty': qty,
                'product_uom': product.uom_id.id,
                'price_unit': product.standard_price,
                'date_planned': fields.Datetime.now(),
                'fulfillment_plan_id': plan.id,
            })],
            'fulfillment_plan_id': plan.id,
            'origin': _('PR Fulfillment Plan %s') % plan.id,
        })
        plan.po_ids = [(4, po.id)]
        plan.status = 'in_progress'
        plan.timeline = _('Purchase order created for fulfillment.')

class FulfillmentSuggestionWizardLine(models.TransientModel):
    _name = 'scm.fulfillment.suggestion.wizard.line'
    _description = 'Fulfillment Suggestion Wizard Line'

    wizard_id = fields.Many2one('scm.fulfillment.suggestion.wizard', string='Wizard')
    pr_line_id = fields.Many2one('purchase.request.line', string='PR Line', required=True)
    source_type = fields.Selection([
        ('purchase', 'Purchase Order'),
        ('transfer', 'Internal Transfer'),
        ('stock', 'On-hand Stock')
    ], string='Source Type', required=True, default='purchase')
    source_location_id = fields.Many2one('stock.location', string='Source Location')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    planned_qty = fields.Float(string='Planned Quantity', required=True)
    planned_start_date = fields.Date(string='Planned Start Date')
    planned_end_date = fields.Date(string='Planned End Date')
    timeline = fields.Selection([
        ('immediate', 'Immediate'),
        ('scheduled', 'Scheduled'),
        ('future', 'Future')
    ], string='Timeline', default='immediate')
    note = fields.Text(string='Note')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'pr_line_id' in fields_list and self.env.context.get('active_id'):
            pr_line = self.env['purchase.request.line'].browse(self.env.context['active_id'])
            res.update({
                'pr_line_id': pr_line.id,
                'planned_qty': pr_line.product_qty,
                'planned_start_date': fields.Date.today(),
                'planned_end_date': fields.Date.today(),
            })
        return res

    def _suggest_fulfillment(self, pr_line):
        """Suggest fulfillment based on product availability and rules"""
        suggestion = {
            'pr_line_id': pr_line.id,
            'source_type': 'purchase',
            'source_location_id': False,
            'destination_location_id': False,
            'planned_qty': pr_line.product_qty,
            'planned_start_date': fields.Date.today(),
            'planned_end_date': fields.Date.today(),
            'timeline': 'immediate',
            'note': False
        }
        
        # Get destination location from PR's company warehouse
        company = pr_line.request_id.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        if warehouse:
            dest_location = warehouse.lot_stock_id
            suggestion['destination_location_id'] = dest_location.id
            
            # Check if product is available in any internal location
            available_qty = self.env['stock.quant']._get_available_quantity(
                pr_line.product_id,
                dest_location
            )
            
            if available_qty >= pr_line.product_qty:
                suggestion.update({
                    'source_type': 'transfer',
                    'source_location_id': dest_location.id,
                    'timeline': 'immediate',
                    'note': 'Product available in stock'
                })
                return suggestion
        return suggestion

    def action_confirm(self):
        # Create fulfillment plans and actions based on user input
        for line in self.line_ids:
            pr_line = line.pr_line_id
            plan_vals = {
                'pr_line_id': pr_line.id,
                'planned_qty': line.planned_qty,
                'source_type': line.source_type,
                'source_location_id': line.source_location_id.id,
                'destination_location_id': line.destination_location_id.id,
                'planned_start_date': line.planned_start_date,
                'planned_end_date': line.planned_end_date,
                'timeline': line.timeline,
                'note': line.note,
            }
            plan = self.env['scm.pr.fulfillment.plan'].create(plan_vals)
            
            # Create fulfillment actions based on source type
            if line.source_type == 'stock':
                self._create_stock_move(plan, pr_line, line.planned_qty)
            elif line.source_type == 'transfer':
                self._create_internal_transfer(plan, pr_line, line.planned_qty)
            elif line.source_type == 'purchase':
                self._create_purchase_order(plan, pr_line, line.planned_qty)
        return {'type': 'ir.actions.act_window_close'}

    def _create_stock_move(self, plan, pr_line, qty):
        # Create a stock move for on-hand fulfillment
        product = pr_line.product_id
        dest_location = pr_line.request_id.company_id.warehouse_id.lot_stock_id
        move = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'name': product.display_name,
            'location_id': dest_location.id,  # On-hand at destination
            'location_dest_id': dest_location.id,
            'fulfillment_plan_id': plan.id,
            'origin': _('PR Fulfillment Plan %s') % plan.id,
        })
        plan.stock_move_ids = [(4, move.id)]
        plan.status = 'in_progress'
        plan.timeline = _('Stock move created for on-hand fulfillment.')

    def _create_internal_transfer(self, plan, pr_line, qty):
        # Create an internal transfer (stock picking)
        product = pr_line.product_id
        warehouse = pr_line.request_id.company_id.warehouse_id or self.env['stock.warehouse'].search([], limit=1)
        dest_location = warehouse.lot_stock_id
        all_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        candidate_locations = all_locations - dest_location
        source_location = False
        for loc in candidate_locations:
            available_qty = self.env['stock.quant']._get_available_quantity(product, loc)
            if available_qty >= qty:
                source_location = loc
                break
        if not source_location:
            raise UserError(_('No other location has enough stock for an internal transfer.'))
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'move_ids_without_package': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'name': product.display_name,
                'fulfillment_plan_id': plan.id,
            })],
            'origin': _('PR Fulfillment Plan %s') % plan.id,
            'fulfillment_plan_id': plan.id,
        })
        plan.transfer_ids = [(4, picking.id)]
        plan.status = 'in_progress'
        plan.timeline = _('Internal transfer created from %s to %s') % (source_location.display_name, dest_location.display_name)

    def _create_purchase_order(self, plan, pr_line, qty):
        # Create a purchase order for the required quantity
        product = pr_line.product_id
        partner = product.seller_ids and product.seller_ids[0].name or False
        if not partner:
            raise UserError(_('No vendor found for product %s') % product.display_name)
        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.display_name,
                'product_qty': qty,
                'product_uom': product.uom_id.id,
                'price_unit': product.standard_price,
                'date_planned': fields.Datetime.now(),
                'fulfillment_plan_id': plan.id,
            })],
            'fulfillment_plan_id': plan.id,
            'origin': _('PR Fulfillment Plan %s') % plan.id,
        })
        plan.po_ids = [(4, po.id)]
        plan.status = 'in_progress'
        plan.timeline = _('Purchase order created for fulfillment.') 