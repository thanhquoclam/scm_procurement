from odoo import models, fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    fulfillment_plan_id = fields.Many2one('scm.pr.fulfillment.plan', string='Fulfillment Plan') 