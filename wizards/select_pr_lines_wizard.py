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
            if session.purchase_request_ids:
                pr_lines = self.env['purchase.request.line'].search([
                    ('request_id', 'in', session.purchase_request_ids.ids),
                    ('state', '=', 'approved')
                ])
                if pr_lines:
                    res['line_ids'] = [(6, 0, pr_lines.ids)]
        return res

    @api.onchange('session_id')
    def _onchange_session_id(self):
        if self.session_id and self.session_id.purchase_request_ids:
            available_lines = self.env['purchase.request.line'].search([
                ('request_id', 'in', self.session_id.purchase_request_ids.ids),
                ('state', '=', 'approved')
            ])
            if available_lines:
                self.line_ids = [(6, 0, available_lines.ids)]

    def action_consolidate_selected_lines(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Please select at least one line to consolidate.'))
        
        _logger.info("Selected lines: %s", self.line_ids)
        
        # Process the selected lines
        result = self.session_id._process_pr_lines_safely(self.line_ids)
        _logger.info("Process result: %s", result)
        
        # Check if consolidated lines were created
        consolidated_lines = self.session_id.consolidated_line_ids
        _logger.info("Consolidated lines after processing: %s", consolidated_lines)
        
        # Update session state
        self.session_id.write({'state': 'in_progress'})
        
        return {'type': 'ir.actions.act_window_close'} 