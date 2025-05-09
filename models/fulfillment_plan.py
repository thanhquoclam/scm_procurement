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
    fulfillment_method = fields.Selection([
        ('po', 'Purchase Order'),
        ('internal_transfer', 'Internal Transfer'),
        ('other', 'Other'),
    ], string='Fulfillment Method', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('fulfilled', 'Fulfilled'),
        ('exception', 'Exception'),
    ], string='Status', default='pending', required=True)
    po_id = fields.Many2one('purchase.order', string='Purchase Order')
    transfer_id = fields.Many2one('stock.picking', string='Internal Transfer')
    planned_qty = fields.Float(string='Planned Quantity', required=True)
    fulfilled_qty = fields.Float(string='Fulfilled Quantity', default=0.0)
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_remaining_qty', store=True)
    timeline = fields.Char(string='Timeline/Notes')
    note = fields.Text(string='Notes')
    create_date = fields.Datetime(string='Created On', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)

    @api.depends('planned_qty', 'fulfilled_qty')
    def _compute_remaining_qty(self):
        for rec in self:
            rec.remaining_qty = max(rec.planned_qty - rec.fulfilled_qty, 0.0)

    def action_suggest_internal_transfer(self):
        """Suggest an internal transfer if stock is available in other locations."""
        self.ensure_one()
        product = self.pr_line_id.product_id
        required_qty = self.remaining_qty
        warehouse = self.pr_line_id.request_id.company_id.warehouse_id or self.env['stock.warehouse'].search([], limit=1)
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
            'type': 'ir.actions.act_window_message',
            'title': _('Internal Transfer Suggested'),
            'message': self.timeline,
        }

    def action_create_internal_transfer(self):
        """Create an internal transfer picking for this fulfillment plan."""
        self.ensure_one()
        product = self.pr_line_id.product_id
        required_qty = self.remaining_qty
        warehouse = self.pr_line_id.request_id.company_id.warehouse_id or self.env['stock.warehouse'].search([], limit=1)
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

    # Add inverse relation to PR line (to be added in purchase.request.line) 