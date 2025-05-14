from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FulfillmentSuggestionWizard(models.TransientModel):
    _name = 'scm.fulfillment.suggestion.wizard'
    _description = 'Fulfillment Suggestion Wizard'

    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',
        string='PR Consolidation Session',
        required=True,
        readonly=True
    )
    pr_id_readonly = fields.Boolean(compute='_compute_pr_id_readonly')
    pr_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True
    )
    pr_domain_ids = fields.Many2many(
        'purchase.request',
        compute='_compute_pr_domain_ids',
        string='PR Domain',
        store=False
    )
    line_ids = fields.One2many(
        'scm.fulfillment.suggestion.wizard.line',
        'wizard_id',
        string='Fulfillment Suggestions',
    )

    @api.onchange('pr_id')
    def _onchange_pr_id(self):
        if self.pr_id:
            commands = [(5, 0, 0)]  # Clear existing lines
            for pr_line in self.pr_id.line_ids:
                suggestion = self._suggest_fulfillment(pr_line)
                commands.append((0, 0, suggestion))
            self.line_ids = commands

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get('active_model') == 'scm.pr.consolidation.session' and ctx.get('active_id'):
            consolidation = self.env['scm.pr.consolidation.session'].browse(ctx['active_id'])
            res['consolidation_id'] = consolidation.id
            if consolidation.purchase_request_ids:
                res['pr_id'] = consolidation.purchase_request_ids[0].id
        elif ctx.get('active_model') == 'purchase.request' and ctx.get('active_id'):
            res['pr_id'] = ctx['active_id']
            # Try to find consolidation from context or PR line
            consolidation_id = ctx.get('default_consolidation_id') or ctx.get('consolidation_id')
            if not consolidation_id:
                pr = self.env['purchase.request'].browse(ctx['active_id'])
                if pr.line_ids and pr.line_ids[0].consolidated_line_ids:
                    consolidation_id = pr.line_ids[0].consolidated_line_ids[0].consolidation_id.id
            res['consolidation_id'] = consolidation_id
        return res

    @api.depends('pr_id')
    def _compute_pr_id_readonly(self):
        for wizard in self:
            ctx = self.env.context
            wizard.pr_id_readonly = ctx.get('active_model') == 'purchase.request'

    @api.depends('consolidation_id')
    def _compute_pr_domain_ids(self):
        for wizard in self:
            if wizard.consolidation_id and wizard.consolidation_id.purchase_request_ids:
                wizard.pr_domain_ids = wizard.consolidation_id.purchase_request_ids
            else:
                # Return an empty recordset to ensure domain is always valid
                wizard.pr_domain_ids = self.env['purchase.request']

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
            all_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
            candidate_locations = all_locations - dest_location
            
            for loc in candidate_locations:
                available_qty = self.env['stock.quant']._get_available_quantity(
                    pr_line.product_id,
                    loc
                )
                
                if available_qty >= pr_line.product_qty:
                    suggestion.update({
                        'source_type': 'transfer',
                        'source_location_id': loc.id,
                        'timeline': 'immediate',
                        'note': f'Product available in {loc.display_name}'
                    })
                    break
                    
            # If no internal transfer is possible, check if product is available in destination
            if suggestion['source_type'] == 'purchase':
                available_qty = self.env['stock.quant']._get_available_quantity(
                    pr_line.product_id,
                    dest_location
                )
                
                if available_qty >= pr_line.product_qty:
                    suggestion.update({
                        'source_type': 'stock',
                        'source_location_id': dest_location.id,
                        'timeline': 'immediate',
                        'note': 'Product available in destination location'
                    })
                    
        return suggestion

    def _suggest_fulfillment_consolidated(self, consolidated_line):
        # Suggest fulfillment for a consolidated line (product)
        suggestion = {
            'pr_line_id': consolidated_line.purchase_request_line_ids and consolidated_line.purchase_request_line_ids[0].id or False,
            'source_type': 'po',
            'source_location_id': False,
            'destination_location_id': False,
            'planned_qty': consolidated_line.total_quantity,
            'planned_start_date': fields.Date.today(),
            'planned_end_date': fields.Date.today(),
            'timeline': 'immediate',
            'note': False
        }
        # You can enhance this to use product, warehouse, etc. from consolidated_line
        return suggestion

    def action_confirm(self):
        if not self.pr_id or not self.consolidation_id:
            raise UserError(_("Both Purchase Request and Consolidation must be selected."))
        for line in self.line_ids:
            plan_vals = {
                'pr_line_id': line.pr_line_id.id,
                'pr_id': self.pr_id.id,
                'consolidation_id': self.consolidation_id.id,
                'planned_qty': line.planned_qty,
                'source_type': line.source_type,
                'source_location_id': line.source_location_id.id if line.source_location_id else False,
                'destination_location_id': line.destination_location_id.id if line.destination_location_id else False,
                'planned_start_date': line.planned_start_date,
                'planned_end_date': line.planned_end_date,
                'timeline': line.timeline,
                'note': line.note,
            }
            self.env['scm.pr.fulfillment.plan'].create(plan_vals)
        return {'type': 'ir.actions.act_window_close'}

    def _create_stock_move(self, plan, pr_line, qty):
        # Create a stock move for on-hand fulfillment
        product = pr_line.product_id
        company = pr_line.request_id.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        if not warehouse:
            raise UserError(_("No warehouse found for company %s") % company.display_name)
        dest_location = warehouse.lot_stock_id
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
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', pr_line.request_id.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_("No warehouse found for company %s") % pr_line.request_id.company_id.display_name)
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
            all_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
            candidate_locations = all_locations - dest_location
            
            for loc in candidate_locations:
                available_qty = self.env['stock.quant']._get_available_quantity(
                    pr_line.product_id,
                    loc
                )
                
                if available_qty >= pr_line.product_qty:
                    suggestion.update({
                        'source_type': 'transfer',
                        'source_location_id': loc.id,
                        'timeline': 'immediate',
                        'note': f'Product available in {loc.display_name}'
                    })
                    break
                    
            # If no internal transfer is possible, check if product is available in destination
            if suggestion['source_type'] == 'purchase':
                available_qty = self.env['stock.quant']._get_available_quantity(
                    pr_line.product_id,
                    dest_location
                )
                
                if available_qty >= pr_line.product_qty:
                    suggestion.update({
                        'source_type': 'stock',
                        'source_location_id': dest_location.id,
                        'timeline': 'immediate',
                        'note': 'Product available in destination location'
                    })
                    
        return suggestion

    def action_confirm(self):
        # Create fulfillment plans and actions based on user input
        for line in self.line_ids:
            pr_line = line.pr_line_id
            consolidation_id = (
                self.env.context.get('active_id') if self.env.context.get('active_model') == 'scm.pr.consolidation.session'
                else self.env.context.get('default_consolidation_id')
                or self.env.context.get('consolidation_id')
                or (pr_line.consolidated_line_ids and pr_line.consolidated_line_ids[0].consolidation_id.id)
                or False
            )
            if not consolidation_id:
                raise UserError(_("Cannot create a fulfillment plan: No consolidation session found for PR line '%s'. Please ensure the PR line is part of a consolidation.") % pr_line.display_name)
            plan_vals = {
                'pr_line_id': pr_line.id,
                'pr_id': pr_line.request_id.id,
                'consolidation_id': consolidation_id,
                'planned_qty': line.planned_qty,
                'source_type': line.source_type,
                'source_location_id': line.source_location_id.id if line.source_location_id else False,
                'destination_location_id': line.destination_location_id.id if line.destination_location_id else False,
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
            elif line.source_type == 'po':
                self._create_purchase_order(plan, pr_line, line.planned_qty)
        return {'type': 'ir.actions.act_window_close'}

    def _create_stock_move(self, plan, pr_line, qty):
        # Create a stock move for on-hand fulfillment
        product = pr_line.product_id
        company = pr_line.request_id.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        if not warehouse:
            raise UserError(_("No warehouse found for company %s") % company.display_name)
        dest_location = warehouse.lot_stock_id
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
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', pr_line.request_id.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_("No warehouse found for company %s") % pr_line.request_id.company_id.display_name)
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