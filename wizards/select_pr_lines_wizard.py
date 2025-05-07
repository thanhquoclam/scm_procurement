# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SelectPRLinesWizard(models.TransientModel):
    _name = 'select.pr.lines.wizard'
    _description = 'Select Purchase Request Lines Wizard'

    session_id = fields.Many2one(
        'scm.pr.consolidation.session',
        string='Consolidation Session',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    line_ids = fields.Many2many(
        'purchase.request.line',
        string='Purchase Request Lines'
    )
    available_line_ids = fields.Many2many(
        'purchase.request.line',
        string='Available Lines',
        compute='_compute_available_line_ids'
    )
    purchase_request_ids = fields.Many2many(
        'purchase.request', 
        string='Purchase Requests', 
        compute='_compute_purchase_request_ids', 
        store=True
    )

    @api.depends('session_id')
    def _compute_purchase_request_ids(self):
        for wizard in self:
            if wizard.session_id:
                wizard.purchase_request_ids = wizard.session_id.purchase_request_ids
            else:
                wizard.purchase_request_ids = False

    @api.depends('session_id')
    def _compute_available_line_ids(self):
        for wizard in self:
            if wizard.session_id and wizard.session_id.purchase_request_ids:
                wizard.available_line_ids = self.env['purchase.request.line'].search([
                    ('request_id', 'in', wizard.session_id.purchase_request_ids.ids),
                    ('state', '=', 'approved')
                ])
            else:
                wizard.available_line_ids = False

    @api.model
    def default_get(self, fields_list):
        res = super(SelectPRLinesWizard, self).default_get(fields_list)
        if 'line_ids' in fields_list and self.env.context.get('active_id'):
            session = self.env['scm.pr.consolidation.session'].browse(self.env.context.get('active_id'))
            _logger.info("Getting default lines for session %s with %d PRs", session.id, len(session.purchase_request_ids))
            
            if session.purchase_request_ids:
                # Get all lines from approved PRs
                pr_lines = self.env['purchase.request.line'].search([
                    ('request_id', 'in', session.purchase_request_ids.ids),
                    ('request_id.state', '=', 'approved')
                ])
                _logger.info("Found %d PR lines", len(pr_lines))
                res['line_ids'] = [(6, 0, pr_lines.ids)]
        return res

    @api.onchange('session_id')
    def _onchange_session_id(self):
        if self.session_id and self.session_id.purchase_request_ids:
            _logger.info("Session changed to %s with %d PRs", self.session_id.id, len(self.session_id.purchase_request_ids))
            
            # Get all lines from approved PRs
            available_lines = self.env['purchase.request.line'].search([
                ('request_id', 'in', self.session_id.purchase_request_ids.ids),
                ('request_id.state', '=', 'approved')
            ])
            _logger.info("Found %d available lines", len(available_lines))
            
            if available_lines:
                self.line_ids = [(6, 0, available_lines.ids)]

    def action_consolidate_selected_lines(self):
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_("Please select at least one line to consolidate."))
        
        # Group lines by product
        product_lines = {}
        for line in self.line_ids:
            if line.product_id.id not in product_lines:
                product_lines[line.product_id.id] = {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'lines': [],
                    'total_quantity': 0.0
                }
            product_lines[line.product_id.id]['lines'].append(line)
            product_lines[line.product_id.id]['total_quantity'] += line.product_qty
        
        # Create or update consolidated lines
        for product_id, data in product_lines.items():
            # Check if consolidated line already exists
            existing_line = self.env['scm.consolidated.pr.line'].search([
                ('consolidation_id', '=', self.session_id.id),
                ('product_id', '=', product_id)
            ], limit=1)
            
            if existing_line:
                # Update existing line
                existing_line.write({
                    'purchase_request_line_ids': [(6, 0, [line.id for line in data['lines']])],
                    'total_quantity': data['total_quantity']
                })
            else:
                # Create new line
                self.env['scm.consolidated.pr.line'].create({
                    'consolidation_id': self.session_id.id,
                    'product_id': product_id,
                    'product_uom_id': data['product_uom_id'],
                    'total_quantity': data['total_quantity'],
                    'purchase_request_line_ids': [(6, 0, [line.id for line in data['lines']])]
                })
        
        # Update session state to in_progress after consolidating lines
        self.session_id.write({
            'state': 'in_progress',
            'purchase_request_ids': [(6, 0, self.line_ids.mapped('request_id').ids)]
        })
        
        return {'type': 'ir.actions.act_window_close'} 