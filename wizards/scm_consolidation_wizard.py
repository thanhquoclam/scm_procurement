# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class CreateConsolidationWizard(models.TransientModel):
    _name = 'scm.create.consolidation.wizard'
    _description = 'Create Consolidation Session Wizard'

    name = fields.Char(
        string='Session Name',
        required=True,
        default=lambda self: _('Consolidation %s') % fields.Date.today()
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today()
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Filter PRs by these departments. Leave empty to include all departments.'
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Filter PRs by these product categories. Leave empty to include all categories.'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    auto_start = fields.Boolean(
        string='Auto Start Consolidation',
        default=True,
        help='Automatically start the consolidation process after creation'
    )
    pr_count = fields.Integer(
        string='Eligible Purchase Requests',
        compute='_compute_pr_count'
    )

    @api.depends('date_from', 'date_to', 'department_ids', 'category_ids')
    def _compute_pr_count(self):
        for wizard in self:
            domain = [
                ('state', '=', 'approved'),
                ('date_start', '>=', wizard.date_from),
                ('date_start', '<=', wizard.date_to)
            ]
            
            if wizard.department_ids:
                domain.append(('department_id', 'in', wizard.department_ids.ids))
            
            purchase_requests = self.env['purchase.request'].search(domain)
            
            # If category filter is applied, we need to check PR lines
            if wizard.category_ids:
                category_prs = self.env['purchase.request']
                for pr in purchase_requests:
                    for line in pr.line_ids:
                        if line.product_id and line.product_id.categ_id.id in wizard.category_ids.ids:
                            category_prs |= pr
                            break
                purchase_requests = category_prs
            
            wizard.pr_count = len(purchase_requests)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("End date cannot be earlier than start date."))

    def action_preview_prs(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'approved'),
            ('date_start', '>=', self.date_from),
            ('date_start', '<=', self.date_to)
        ]
        
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        
        # Fix for the PR preview with category filter
        action = {
            'name': _('Eligible Purchase Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'view_mode': 'tree,form',
            'domain': domain,
        }
        
        # If category filter is applied, we need to handle it differently
        if self.category_ids:
            # We'll need to retrieve the PRs manually and pass their IDs
            purchase_requests = self.env['purchase.request'].search(domain)
            category_pr_ids = []
            
            for pr in purchase_requests:
                for line in pr.line_ids:
                    if line.product_id and line.product_id.categ_id.id in self.category_ids.ids:
                        category_pr_ids.append(pr.id)
                        break
            
            action['domain'] = [('id', 'in', category_pr_ids)]
        
        return action

    def action_create_consolidation(self):
        self.ensure_one()
        
        if self.pr_count == 0:
            raise UserError(_("No eligible Purchase Requests found for the selected criteria."))
            
        values = {
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'department_ids': [(6, 0, self.department_ids.ids)],
            'category_ids': [(6, 0, self.category_ids.ids)],
            'user_id': self.user_id.id,
            'notes': self.notes,
            'company_id': self.company_id.id,
            'state': 'draft'
        }
        
        consolidation = self.env['scm.pr.consolidation.session'].create(values)
        
        # If auto_start is checked, automatically start the consolidation
        if self.auto_start:
            consolidation.action_start_consolidation()
        
        # Open the created consolidation
        return {
            'name': _('Consolidation Session'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.pr.consolidation.session',
            'view_mode': 'form',
            'res_id': consolidation.id,
        }

class SelectPRLinesWizard(models.TransientModel):
    _name = 'select.pr.lines.wizard'
    _description = 'Select Purchase Request Lines for Consolidation'

    session_id = fields.Many2one('scm.pr.consolidation.session', string='Consolidation Session', required=True)
    line_ids = fields.Many2many('purchase.request.line', string='Purchase Request Lines')

    @api.model
    def default_get(self, fields):
        res = super(SelectPRLinesWizard, self).default_get(fields)
        session = self.env['scm.pr.consolidation.session'].browse(self._context.get('active_id'))
        if session:
            res['session_id'] = session.id
            # Get all lines from linked purchase requests
            pr_lines = session.purchase_request_ids.mapped('line_ids')
            res['line_ids'] = pr_lines.ids
        return res

    def _process_selected_lines(self):
        """Process selected lines and create consolidated lines."""
        self.ensure_one()
        
        # Group lines by product
        product_lines = {}
        for line in self.line_ids:
            product_id = line.product_id.id
            if not product_id:
                continue
                
            if product_id not in product_lines:
                product_lines[product_id] = {
                    'product': line.product_id,
                    'uom': line.product_uom_id,
                    'total_qty': 0,
                    'pr_lines': self.env['purchase.request.line'],
                    'earliest_date': line.date_required or line.request_id.date_start,
                }
            
            data = product_lines[product_id]
            data['total_qty'] += line.product_qty
            data['pr_lines'] |= line
            
            line_date = line.date_required or line.request_id.date_start
            if line_date and (not data['earliest_date'] or line_date < data['earliest_date']):
                data['earliest_date'] = line_date

        # Create consolidated lines
        ConsolidatedLine = self.env['scm.consolidated.pr.line'].with_context(
            tracking_disable=True,
            mail_notrack=True
        )
        
        for product_id, data in product_lines.items():
            # Check if consolidated line already exists
            existing_line = self.session_id.consolidated_line_ids.filtered(
                lambda l: l.product_id.id == product_id
            )
            
            if existing_line:
                existing_line.write({
                    'total_quantity': data['total_qty'],
                    'purchase_request_line_ids': [(6, 0, data['pr_lines'].ids)],
                    'earliest_date_required': data['earliest_date'],
                })
            else:
                ConsolidatedLine.create({
                    'consolidation_id': self.session_id.id,
                    'product_id': product_id,
                    'product_uom_id': data['uom'].id,
                    'total_quantity': data['total_qty'],
                    'purchase_request_line_ids': [(6, 0, data['pr_lines'].ids)],
                    'earliest_date_required': data['earliest_date'],
                    'state': 'draft'
                })

    def action_consolidate_selected_lines(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('No lines selected for consolidation.'))
        
        # Process the selected lines
        self._process_selected_lines()
        
        # Update session state to in_progress
        self.session_id.write({'state': 'in_progress'})
        
        return {'type': 'ir.actions.act_window_close'}