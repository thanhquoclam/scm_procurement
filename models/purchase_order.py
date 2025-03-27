from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    consolidation_id = fields.Many2one(
        'scm.consolidation',
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

    @api.depends('consolidation_id')
    def _compute_is_from_consolidation(self):
        for order in self:
            order.is_from_consolidation = bool(order.consolidation_id)