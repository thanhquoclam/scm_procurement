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