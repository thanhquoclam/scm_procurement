# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CreateConsolidationWizard(models.TransientModel):
    _name = 'scm.create.consolidation.wizard'
    _description = 'Create Consolidation Session Wizard'

    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('New Consolidation Session')
    )
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    pr_count = fields.Integer(
        string='Purchase Request Count',
        compute='_compute_pr_count'
    )
    auto_start = fields.Boolean(
        string='Auto Start',
        default=False,
        help='Automatically start the consolidation process after creation'
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Filter purchase requests by departments'
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Filter purchase requests by product categories'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes for the consolidation session'
    )

    @api.depends('date_from', 'date_to', 'warehouse_id', 'department_ids', 'category_ids')
    def _compute_pr_count(self):
        for wizard in self:
            domain = [
                ('state', '=', 'approved'),
                ('date_required', '>=', wizard.date_from),
                ('date_required', '<=', wizard.date_to),
            ]
            
            # Add warehouse filter if specified
            if wizard.warehouse_id:
                domain.append(('warehouse_id', '=', wizard.warehouse_id.id))
                
            # Add department filter if specified
            if wizard.department_ids:
                domain.append(('department_id', 'in', wizard.department_ids.ids))
            
            # Add category filter if specified
            if wizard.category_ids:
                domain.append(('product_id.categ_id', 'in', wizard.category_ids.ids))
                
            # Count eligible purchase requests
            wizard.pr_count = self.env['purchase.request'].search_count(domain)

    def action_preview_prs(self):
        self.ensure_one()
        
        # Build domain for eligible purchase requests
        domain = [
            ('state', '=', 'approved'),
            ('date_required', '>=', self.date_from),
            ('date_required', '<=', self.date_to),
        ]
        
        # Add warehouse filter if specified
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
            
        # Add department filter if specified
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
            
        # Add category filter if specified
        if self.category_ids:
            domain.append(('product_id.categ_id', 'in', self.category_ids.ids))
            
        # Get eligible purchase requests
        purchase_requests = self.env['purchase.request'].search(domain)
        
        # Return action to view the purchase requests
        return {
            'name': _('Eligible Purchase Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_requests.ids)],
            'context': {'create': False}
        }

    @api.model
    def default_get(self, fields_list):
        res = super(CreateConsolidationWizard, self).default_get(fields_list)
        if 'warehouse_id' in fields_list and not res.get('warehouse_id'):
            # Get default warehouse from user's settings
            default_warehouse = self.env['stock.warehouse'].search([], limit=1)
            if default_warehouse:
                res['warehouse_id'] = default_warehouse.id
        return res

    def action_create_consolidation(self):
        self.ensure_one()
        
        # Create consolidation session
        consolidation = self.env['scm.pr.consolidation.session'].create({
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'warehouse_id': self.warehouse_id.id,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'state': 'draft',
            'notes': self.notes
        })
        
        # If auto_start is enabled, automatically start the consolidation process
        if self.auto_start and self.pr_count > 0:
            # Get eligible purchase requests
            domain = [
                ('state', '=', 'approved'),
                ('date_required', '>=', self.date_from),
                ('date_required', '<=', self.date_to),
            ]
            
            # Add warehouse filter if specified
            if self.warehouse_id:
                domain.append(('warehouse_id', '=', self.warehouse_id.id))
                
            # Add department filter if specified
            if self.department_ids:
                domain.append(('department_id', 'in', self.department_ids.ids))
                
            # Add category filter if specified
            if self.category_ids:
                domain.append(('product_id.categ_id', 'in', self.category_ids.ids))
                
            # Get eligible purchase requests
            purchase_requests = self.env['purchase.request'].search(domain)
            
            # Add purchase requests to the consolidation session
            consolidation.write({
                'purchase_request_ids': [(6, 0, purchase_requests.ids)]
            })
            
            # Start the consolidation process
            consolidation.action_start()
        
        # Return action to open the created consolidation
        return {
            'name': _('Consolidation Session'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.pr.consolidation.session',
            'view_mode': 'form',
            'res_id': consolidation.id,
        }

# The SelectPRLinesWizard class has been moved to select_pr_lines_wizard.py