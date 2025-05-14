from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PRFulfillmentPlan(models.Model):
    _name = 'scm.pr.fulfillment.plan'
    _description = 'PR Fulfillment Plan'
    _order = 'id desc'

    pr_line_id = fields.Many2one(
        'purchase.request.line',
        string='Purchase Request Line',
        required=True,
        ondelete='cascade',
    )
    pr_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        compute='_compute_pr_id',
        store=True,
        readonly=False,
    )
    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',
        string='PR Consolidation Session',
        required=True,
        ondelete='restrict',
    )
    source_type = fields.Selection([
        ('stock', 'On-hand Stock'),
        ('transfer', 'Internal Transfer'),
        ('po', 'Purchase Order'),
    ], string='Source Type')
    source_location_id = fields.Many2one('stock.location', string='Source Location')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    planned_start_date = fields.Datetime(string='Planned Start Date')
    planned_end_date = fields.Datetime(string='Planned End Date')
    actual_start_date = fields.Datetime(string='Actual Start Date')
    actual_end_date = fields.Datetime(string='Actual End Date')
    responsible_id = fields.Many2one('res.users', string='Responsible')
    po_ids = fields.One2many('purchase.order', 'fulfillment_plan_id', string='Purchase Orders')
    transfer_ids = fields.One2many('stock.picking', 'fulfillment_plan_id', string='Internal Transfers')
    stock_move_ids = fields.One2many('stock.move', 'fulfillment_plan_id', string='Stock Moves')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('fulfilled', 'Fulfilled'),
        ('partial', 'Partial'),
        ('exception', 'Exception'),
    ], string='Status', default='pending', required=True)
    planned_qty = fields.Float(string='Planned Quantity', required=True)
    fulfilled_qty = fields.Float(string='Fulfilled Quantity', default=0.0)
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_remaining_qty', store=True)
    timeline = fields.Char(string='Timeline/Notes')
    note = fields.Text(string='Notes')
    create_date = fields.Datetime(string='Created On', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)
    fulfillment_method = fields.Selection([
        ('internal_transfer', 'Internal Transfer'),
        ('purchase', 'Purchase Order'),
        ('stock', 'On-hand Stock'),
    ], string='Fulfillment Method')

    # Deprecated fields (for backward compatibility, to be removed after migration)
    po_id = fields.Many2one('purchase.order', string='Purchase Order (deprecated)')
    transfer_id = fields.Many2one('stock.picking', string='Internal Transfer (deprecated)')

    code = fields.Char(string='Code', required=True, readonly=True, copy=False, index=True, default='/')

    @api.depends('pr_line_id')
    def _compute_pr_id(self):
        for rec in self:
            rec.pr_id = rec.pr_line_id.request_id if rec.pr_line_id else False

    @api.depends('planned_qty', 'fulfilled_qty')
    def _compute_remaining_qty(self):
        for rec in self:
            rec.remaining_qty = max(rec.planned_qty - rec.fulfilled_qty, 0.0)

    def action_suggest_internal_transfer(self):
        """Suggest an internal transfer if stock is available in other locations."""
        self.ensure_one()
        product = self.pr_line_id.product_id
        required_qty = self.remaining_qty
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.pr_line_id.request_id.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_("No warehouse found for company %s") % self.pr_line_id.request_id.company_id.display_name)
        # Find all locations except the destination warehouse's main stock
        all_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        dest_location = warehouse.lot_stock_id
        candidate_locations = all_locations - dest_location
        # Check stock in other locations
        available = 0.0
        source_location = False
        for loc in candidate_locations:
            qty = self.env['stock.quant']._get_available_quantity(product, loc)
            if qty >= required_qty:
                available = qty
                source_location = loc
                break
        if not source_location:
            raise UserError(_('No other location has enough stock for an internal transfer.'))
        # Store suggestion info in the plan (or show a wizard in the UI)
        self.timeline = _('Suggested transfer from %s (%.2f available) to %s') % (source_location.display_name, available, dest_location.display_name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Internal Transfer Suggested'),
                'message': self.timeline,
                'sticky': False,
                'type': 'success',
            }
        }

    def action_create_internal_transfer(self):
        """Create an internal transfer picking for this fulfillment plan."""
        self.ensure_one()
        product = self.pr_line_id.product_id
        required_qty = self.remaining_qty
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.pr_line_id.request_id.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_("No warehouse found for company %s") % self.pr_line_id.request_id.company_id.display_name)
        dest_location = warehouse.lot_stock_id
        # Find a source location with enough stock
        all_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        candidate_locations = all_locations - dest_location
        source_location = False
        for loc in candidate_locations:
            qty = self.env['stock.quant']._get_available_quantity(product, loc)
            if qty >= required_qty:
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
                'product_uom_qty': required_qty,
                'product_uom': product.uom_id.id,
                'name': product.display_name,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
            })],
            'origin': _('PR Fulfillment Plan %s') % self.id,
        })
        self.transfer_id = picking.id
        self.fulfillment_method = 'internal_transfer'
        self.status = 'in_progress'
        self.timeline = _('Internal transfer created from %s to %s') % (source_location.display_name, dest_location.display_name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
        }

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('scm.pr.fulfillment.plan') or '/'
        return super().create(vals) 