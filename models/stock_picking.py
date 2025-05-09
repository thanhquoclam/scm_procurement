from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fulfillment_plan_id = fields.Many2one('scm.pr.fulfillment.plan', string='Fulfillment Plan')

    @api.model
    def _update_fulfillment_plans_on_receipt(self, pick):
        for move in pick.move_lines:
            po_line = move.purchase_line_id
            if not po_line:
                continue
            # Find PR line(s) linked to this PO line
            pr_lines = po_line.purchase_request_line_ids
            for pr_line in pr_lines:
                # Find fulfillment plans for this PR line and PO
                plans = self.env['scm.pr.fulfillment.plan'].search([
                    ('pr_line_id', '=', pr_line.id),
                    ('po_id', '=', po_line.order_id.id),
                ])
                for plan in plans:
                    plan.fulfilled_qty += move.quantity_done
                    if plan.fulfilled_qty >= plan.planned_qty:
                        plan.status = 'fulfilled'
                    else:
                        plan.status = 'in_progress'
                    plan._compute_remaining_qty()
                    pr_line._compute_fulfillment_status()  # If you add a computed status field

    def button_validate(self):
        res = super().button_validate()
        for pick in self:
            if pick.picking_type_code == 'incoming' and pick.state == 'done':
                self._update_fulfillment_plans_on_receipt(pick)
        return res 