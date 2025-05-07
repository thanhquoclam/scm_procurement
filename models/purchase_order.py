from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    consolidation_id = fields.Many2one(
        'scm.pr.consolidation.session',  # Updated model reference
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
        string='From Consolidation',
        default=False
    )

    # Add fields for blanket order reference
    requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Blanket Order',
        tracking=True,
        help="Reference to the blanket order if this PO was created from a blanket order"
    )
    
    # Add field to indicate if this PO was created from a blanket order
    is_from_agreement = fields.Boolean(
        string='From Blanket Order',
        compute='_compute_is_from_agreement',
        store=True
    )

    requisition_line_id = fields.Many2one('purchase.requisition.line', string='Agreement Line')
    purchase_request_ids = fields.Many2many('purchase.request', string='Purchase Requests')
    purchase_request_line_ids = fields.Many2many('purchase.request.line', string='Purchase Request Lines')
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval State', default='draft')
    approver_id = fields.Many2one('res.users', string='Approved By')
    approval_date = fields.Datetime(string='Approval Date')
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.depends('requisition_id')
    def _compute_is_from_agreement(self):
        for order in self:
            order.is_from_agreement = bool(order.requisition_id)

    def action_view_consolidation(self):
        self.ensure_one()
        if self.consolidation_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'scm.pr.consolidation.session',
                'res_id': self.consolidation_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    # Status tracking fields
    approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status', default='pending', tracking=True)
    
    approver_id = fields.Many2one('res.users', string='Approver', tracking=True)
    approval_date = fields.Datetime('Approval Date', tracking=True)
    rejection_reason = fields.Text('Rejection Reason', tracking=True)
    
    # Link to original PRs
    purchase_request_ids = fields.Many2many(
        'purchase.request',
        string='Source Purchase Requests',
        compute='_compute_purchase_requests',
        store=True
    )
    
    @api.depends('order_line.purchase_request_line_ids.request_id')
    def _compute_purchase_requests(self):
        for po in self:
            requests = po.order_line.mapped('purchase_request_line_ids.request_id')
            po.purchase_request_ids = [(6, 0, requests.ids)]
    
    def action_approve(self):
        """Approve the purchase order."""
        self.ensure_one()
        if not self.env.user.has_group('purchase.group_purchase_manager'):
            raise UserError(_('Only purchase managers can approve purchase orders.'))
            
        self.write({
            'approval_state': 'approved',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        
        # Update related records
        if self.is_from_consolidation:
            self._update_consolidation_status()
    
    def action_reject(self):
        """Reject the purchase order."""
        self.ensure_one()
        if not self.env.user.has_group('purchase.group_purchase_manager'):
            raise UserError(_('Only purchase managers can reject purchase orders.'))
            
        return {
            'name': _('Reject Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }
    
    def _update_consolidation_status(self):
        """Update consolidation session status based on PO approvals."""
        if not self.consolidation_id:
            return
            
        # Check if all POs from this consolidation are approved
        all_pos = self.env['purchase.order'].search([
            ('consolidation_id', '=', self.consolidation_id.id)
        ])
        
        if all(po.approval_state == 'approved' for po in all_pos):
            self.consolidation_id.write({'state': 'done'})

    def _prepare_blanket_order_line(self, line):
        """Prepare values for creating a blanket order line"""
        return {
            'product_id': line.product_id.id,
            'product_qty': line.product_qty,
            'price_unit': line.price_unit,
            'requisition_id': line.requisition_id.id,
            'product_uom_id': line.product_id.uom_id.id,
            'date_planned': fields.Datetime.now(),
            'state': 'draft'
        }

    def _get_blanket_order_line(self, product, vendor):
        """Get matching blanket order line for product and vendor"""
        return self.env['purchase.requisition.line'].search([
            ('requisition_id.vendor_id', '=', vendor.id),
            ('product_id', '=', product.id),
            ('requisition_id.state', '=', 'done'),
            ('requisition_id.date_end', '>=', fields.Date.today())
        ], limit=1)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    requisition_line_id = fields.Many2one(
        'purchase.requisition.line',
        string='Blanket Order Line'
    )
    is_from_agreement = fields.Boolean(
        string='From Blanket Order',
        compute='_compute_is_from_agreement',
        store=True
    )
    purchase_request_line_ids = fields.Many2many(
        'purchase.request.line',
        string='Source PR Lines',
        copy=False
    )

    @api.depends('requisition_line_id')
    def _compute_is_from_agreement(self):
        for line in self:
            line.is_from_agreement = bool(line.requisition_line_id)


class PurchaseOrderRejectWizard(models.TransientModel):
    _name = 'purchase.order.reject.wizard'
    _description = 'Purchase Order Rejection Wizard'

    rejection_reason = fields.Text('Rejection Reason', required=True)

    def action_confirm(self):
        """Confirm the rejection with reason."""
        self.ensure_one()
        po = self.env['purchase.order'].browse(self.env.context.get('active_id'))
        po.write({
            'approval_state': 'rejected',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
            'rejection_reason': self.rejection_reason
        })
        return {'type': 'ir.actions.act_window_close'}

    # Override the standard price computation to consider blanket order prices
    @api.depends('order_line.price_unit', 'order_line.product_qty')
    def _compute_amount_total(self):
        for order in self:
            amount_untaxed = 0.0
            amount_tax = 0.0
            
            for line in order.order_line:
                # Check if there's a blanket order line with a specific price
                if order.requisition_id:
                    blanket_line = self.env['purchase.requisition.line'].search([
                        ('requisition_id', '=', order.requisition_id.id),
                        ('product_id', '=', line.product_id.id)
                    ], limit=1)
                    
                    if blanket_line:
                        # Use the blanket order price
                        line.price_unit = blanket_line.price_unit
                
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = amount_untaxed + amount_tax