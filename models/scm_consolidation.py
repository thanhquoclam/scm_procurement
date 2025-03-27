# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class PRConsolidationSession(models.Model):
    _name = 'scm.pr.consolidation.session'
    _description = 'Purchase Request Consolidation Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'creation_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        tracking=True
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        tracking=True
    )
    # Define selection field using a method
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('validated', 'Validated'),
        ('po_created', 'POs Created'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('inventory_validation', 'Inventory Validation'),
        ('approved', 'Approved')
    ], string='Status', default='draft')
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True
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
    consolidated_line_ids = fields.One2many(
        'scm.consolidated.pr.line',
        'consolidation_id',
        string='Consolidated Lines',
        tracking=True,
        copy=True
    )
    purchase_request_ids = fields.Many2many(
        comodel_name='purchase.request',
        relation='scm_pr_consolidation_request_rel',
        column1='consolidation_id',
        column2='request_id',
        string='Purchase Requests',
        tracking=True
    )
    #purchase_suggestion_ids = fields.One2many(
    #    'scm.purchase.suggestion',
    #    'consolidation_id',
    #    string='Purchase Suggestions'
    #)
    po_count = fields.Integer(
        string='Purchase Orders',
        compute='_compute_po_count'
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True
    )
    creation_date = fields.Datetime(
        string='Creation Date',
        default=fields.Datetime.now,
        readonly=True
    )
    validation_date = fields.Datetime(
        string='Validation Date',
        readonly=True
    )
    po_creation_date = fields.Datetime(
        string='PO Creation Date',
        readonly=True
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    pr_count = fields.Integer(
        string='Purchase Requests',
        compute='_compute_pr_count'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([], limit=1),
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('scm.pr.consolidation') or _('New')
        return super(PRConsolidationSession, self).create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for session in self:
            if session.date_from > session.date_to:
                raise ValidationError(_("End date cannot be earlier than start date."))

    @api.depends('consolidated_line_ids.subtotal')
    def _compute_total_amount(self):
        for session in self:
            session.total_amount = sum(session.consolidated_line_ids.mapped('subtotal'))

    def _compute_po_count(self):
        for session in self:
            # session.po_count = self.env['purchase.order'].search_count([
            #     ('consolidation_id', '=', session.id)
            # ])
            session.po_count = 0

    def _compute_pr_count(self):
        for session in self:
            purchase_requests = self.env['purchase.request'].search([
                ('consolidation_ids', 'in', session.id)
            ])
            session.pr_count = len(purchase_requests)

    def action_start_consolidation(self):
        """Start the consolidation process."""
        self.ensure_one()
        return self.write({
            'state': 'in_progress'
        })

    def action_validate_consolidation(self):
        """Validate the consolidated lines."""
        self.ensure_one()
        if not self.consolidated_line_ids:
            raise UserError(_('No consolidated lines to validate.'))
        return self.write({
            'state': 'validated',
            'validation_date': fields.Datetime.now()
        })

    def action_start_inventory_validation(self):
        """Start the inventory validation phase."""
        self.ensure_one()
        return self.write({
            'state': 'inventory_validation'
        })

    def action_approve_inventory(self):
        """Approve the inventory validation."""
        self.ensure_one()
        return self.write({
            'state': 'approved'
        })

    def action_create_purchase_orders(self):
        """Create purchase orders from consolidated lines."""
        self.ensure_one()
        # TODO: Implement PO creation logic
        return self.write({
            'state': 'po_created',
            'po_creation_date': fields.Datetime.now()
        })

    def action_mark_done(self):
        """Mark the consolidation session as done."""
        self.ensure_one()
        return self.write({
            'state': 'done'
        })

    def action_cancel(self):
        """Cancel the consolidation session."""
        self.ensure_one()
        return self.write({
            'state': 'cancelled'
        })

    def action_reset_to_draft(self):
        """Reset the cancelled session to draft state."""
        self.ensure_one()
        if self.state != 'cancelled':
            raise UserError(_('Only cancelled sessions can be reset to draft.'))
        return self.write({
            'state': 'draft'
        })

    def action_view_purchase_orders(self):
        """Open related purchase orders."""
        self.ensure_one()
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['domain'] = [('consolidation_id', '=', self.id)]
        return action

    def action_view_purchase_requests(self):
        """Open related purchase requests."""
        self.ensure_one()
        action = self.env.ref('purchase_request.purchase_request_action').read()[0]
        action['domain'] = [('id', 'in', self.purchase_request_ids.ids)]
        return action

    def _collect_purchase_requests(self):
        self.ensure_one()
        
        # Define domain to search for approved purchase requests
        domain = [
            ('state', '=', 'approved'),
            ('date_start', '>=', self.date_from),
            ('date_start', '<=', self.date_to)
        ]
        
        # Add department filter if specified
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        
        # Search for purchase requests matching the criteria
        purchase_requests = self.env['purchase.request'].search(domain)
        
        # Skip if no PRs found
        if not purchase_requests:
            raise UserError(_("No approved Purchase Requests found for the selected period."))
        
        # Link PRs to this consolidation
        purchase_requests.write({
            'consolidation_ids': [(4, self.id)]
        })
        
        # Now process the PR lines to create consolidated lines
        self._consolidate_pr_lines(purchase_requests)
        
        return True
    
    def _consolidate_pr_lines(self, purchase_requests):
        self.ensure_one()
        
        # Dictionary to group PR lines by product
        product_lines = {}
        
        # Process each purchase request
        for pr in purchase_requests:
            for line in pr.line_ids.filtered(lambda l: l.product_id):
                # Skip if product category filter is applied and not matching
                if self.category_ids and line.product_id.categ_id.id not in self.category_ids.ids:
                    continue
                
                # Group by product
                if line.product_id.id not in product_lines:
                    product_lines[line.product_id.id] = {
                        'product': line.product_id,
                        'uom': line.product_uom_id,
                        'total_qty': 0,
                        'pr_lines': [],
                        'earliest_date': line.date_required or pr.date_start,
                        'highest_priority': line.priority or 'normal'
                    }
                
                # Update group data
                product_data = product_lines[line.product_id.id]
                product_data['total_qty'] += line.product_qty
                product_data['pr_lines'].append(line)
                
                # Update earliest date needed
                line_date = line.date_required or pr.date_start
                if line_date and line_date < product_data['earliest_date']:
                    product_data['earliest_date'] = line_date
                
                # Update highest priority
                priority_order = {'low': 0, 'normal': 1, 'high': 2, 'critical': 3}
                line_priority = line.priority or 'normal'
                if priority_order.get(line_priority, 1) > priority_order.get(product_data['highest_priority'], 1):
                    product_data['highest_priority'] = line_priority
        
        # Create consolidated lines
        for product_id, data in product_lines.items():
            # Check if a line already exists for this product
            existing_line = self.consolidated_line_ids.filtered(
                lambda l: l.product_id.id == product_id
            )
            
            if existing_line:
                # Update existing line
                existing_line.write({
                    'total_quantity': data['total_qty'],
                    'purchase_request_line_ids': [(6, 0, [line.id for line in data['pr_lines']])],
                    'earliest_date_required': data['earliest_date'],
                    'priority': data['highest_priority']
                })
            else:
                # Create new consolidated line
                self.env['scm.consolidated.pr.line'].create({
                    'consolidation_id': self.id,
                    'product_id': product_id,
                    'product_uom_id': data['uom'].id,
                    'total_quantity': data['total_qty'],
                    'purchase_request_line_ids': [(6, 0, [line.id for line in data['pr_lines']])],
                    'earliest_date_required': data['earliest_date'],
                    'priority': data['highest_priority'],
                    'state': 'draft'
                })
        
        return True
    
    # Phase 2 additions
    # Add inventory validation fields
    inventory_validated = fields.Boolean('Inventory Validated', default=False, copy=False)
    inventory_validation_date = fields.Datetime('Inventory Validation Date', readonly=True, copy=False)
    inventory_validated_by = fields.Many2one('res.users', 'Validated By', readonly=True, copy=False)
    inventory_validation_notes = fields.Text('Validation Notes', copy=False)
    
    has_inventory_issues = fields.Boolean('Has Inventory Issues', compute='_compute_inventory_status', store=True)
    has_critical_shortages = fields.Boolean('Has Critical Shortages', compute='_compute_inventory_status', store=True)
    pending_approval = fields.Boolean('Pending Inventory Approval', default=False, copy=False)
    inventory_status = fields.Selection([
        ('not_validated', 'Not Validated'),
        ('in_progress', 'Validation In Progress'),
        ('approved', 'Inventory Approved'),
        ('rejected', 'Inventory Rejected')
    ], string='Inventory Status', default='not_validated', copy=False)
    
    total_stockout_items = fields.Integer('Total Stockout Items', compute='_compute_inventory_status', store=True)
    total_below_safety = fields.Integer('Items Below Safety Stock', compute='_compute_inventory_status', store=True)
    total_below_reorder = fields.Integer('Items Below Reorder Point', compute='_compute_inventory_status', store=True)
    
    # Extend state selection to include inventory validation steps
    # state = fields.Selection(selection_add=[
    #     ('inventory_validation', 'Inventory Validation'),
    #     ('approved', 'Approved')
    # ])

    def button_validate_inventory(self):
        """Open inventory validation wizard"""
        self.ensure_one()
        
        if self.state not in ['draft', 'reviewed', 'inventory_validation']:
            raise UserError(_("Inventory validation can only be performed in Draft, Reviewed or Inventory Validation states."))
        
        # Get consolidated lines with inventory issues
        lines_with_issues = self.consolidated_line_ids.filtered(
            lambda l: l.inventory_status in ['below_safety', 'below_reorder'] and l.product_id.type in ['product', 'consu']
        )
        
        # Update state to inventory validation if needed
        if self.state != 'inventory_validation':
            self.write({'state': 'inventory_validation'})
        
        return {
            'name': _('Validate Inventory'),
            'type': 'ir.actions.act_window',
            'res_model': 'validate.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consolidation_id': self.id,
                'default_line_ids': [(6, 0, lines_with_issues.ids)],
                'default_warehouse_id': self.warehouse_id.id,
            }
        }
    
    def button_inventory_approved(self):
        """Mark inventory as approved"""
        self.ensure_one()
        
        if self.state != 'inventory_validation':
            raise UserError(_("Cannot approve inventory for consolidation not in Inventory Validation state."))
        
        self.write({
            'inventory_validated': True,
            'inventory_validation_date': fields.Datetime.now(),
            'inventory_validated_by': self.env.user.id,
            'inventory_status': 'approved',
            'state': 'approved',
            'pending_approval': False,
        })
        
        # Log message in chatter
        self.message_post(
            body=_("Inventory validation approved by %s on %s") % (
                self.env.user.name, fields.Datetime.now()
            ),
            subtype_id=self.env.ref('mail.mt_note').id
        )
        
        return True
    
    def button_reject_inventory(self):
        """Reject inventory validation"""
        self.ensure_one()
        
        if self.state != 'inventory_validation':
            raise UserError(_("Cannot reject inventory for consolidation not in Inventory Validation state."))
        
        # Open wizard to collect rejection reason
        return {
            'name': _('Reject Inventory Validation'),
            'type': 'ir.actions.act_window',
            'res_model': 'reject.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consolidation_id': self.id,
            }
        }
    
    @api.depends('consolidated_line_ids.inventory_status')
    def _compute_inventory_status(self):
        """Compute inventory status flags"""
        for consolidation in self:
            stockout_items = consolidation.consolidated_line_ids.filtered(
                lambda l: l.inventory_status == 'stockout' and l.product_id.type in ['product', 'consu']
            )
            
            below_safety_items = consolidation.consolidated_line_ids.filtered(
                lambda l: l.inventory_status == 'below_safety' and l.product_id.type in ['product', 'consu'] 
            )
            
            below_reorder_items = consolidation.consolidated_line_ids.filtered(
                lambda l: l.inventory_status == 'below_reorder' and l.product_id.type in ['product', 'consu']
            )
            
            consolidation.total_stockout_items = len(stockout_items)
            consolidation.total_below_safety = len(below_safety_items)
            consolidation.total_below_reorder = len(below_reorder_items)
            
            consolidation.has_critical_shortages = bool(stockout_items or below_safety_items)
            consolidation.has_inventory_issues = bool(stockout_items or below_safety_items or below_reorder_items)
    
    def action_forecast_inventory(self):
        """Open wizard to forecast inventory for selected products"""
        self.ensure_one()
        
        # Filter stockable products
        stockable_products = self.consolidated_line_ids.filtered(
            lambda l: l.product_id.type in ['product', 'consu']
        ).mapped('product_id')
        
        if not stockable_products:
            raise UserError(_("No stockable products found in this consolidation."))
        
        return {
            'name': _('Forecast Inventory'),
            'type': 'ir.actions.act_window',
            'res_model': 'forecast.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_warehouse_id': self.warehouse_id.id,
                'default_product_ids': [(6, 0, stockable_products.ids)],
            }
        }
    
    def action_check_inventory_all(self):
        """Check inventory status for all consolidated lines"""
        self.ensure_one()
        
        if not self.consolidated_line_ids:
            raise UserError(_("No consolidated lines to check."))
        
        # Update inventory status for all lines
        for line in self.consolidated_line_ids:
            if line.product_id.type in ['product', 'consu']:
                line._compute_inventory_status()
        
        # Update overall status
        self._compute_inventory_status()
        
        # Show notification with results
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Inventory Check Complete'),
                'message': _(
                    "Inventory check completed:\n"
                    "- Stockout items: %s\n"
                    "- Below safety stock: %s\n"
                    "- Below reorder point: %s"
                ) % (
                    self.total_stockout_items,
                    self.total_below_safety,
                    self.total_below_reorder
                ),
                'sticky': False,
                'type': 'info' if not self.has_critical_shortages else 'warning',
            }
        }
    
    def action_view_inventory_issues(self):
        """View consolidated lines with inventory issues"""
        self.ensure_one()
        
        lines_with_issues = self.consolidated_line_ids.filtered(
            lambda l: l.inventory_status in ['stockout', 'below_safety', 'below_reorder'] 
            and l.product_id.type in ['product', 'consu']
        )
        
        if not lines_with_issues:
            raise UserError(_("No inventory issues found."))
        
        return {
            'name': _('Inventory Issues'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.consolidated.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', lines_with_issues.ids)],
            'context': {'default_consolidation_id': self.id},
        }
    
    def action_send_inventory_approval_request(self):
        """Send email to inventory manager for approval"""
        self.ensure_one()
        
        if not self.has_inventory_issues:
            raise UserError(_("No inventory issues to approve."))
        
        # Find users with inventory approval rights
        inventory_manager_group = self.env.ref('stock.group_stock_manager')
        inventory_managers = inventory_manager_group.users
        
        if not inventory_managers:
            raise UserError(_("No inventory managers found to request approval."))
        
        # Set pending approval flag
        self.write({'pending_approval': True})
        
        # Prepare email template
        template = self.env.ref('scm_procurement.mail_template_inventory_approval')
        
        # Send notification
        for manager in inventory_managers:
            template.send_mail(
                self.id, 
                force_send=True,
                email_values={'email_to': manager.email}
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Approval Request Sent'),
                'message': _("Inventory approval request has been sent to inventory managers."),
                'sticky': False,
                'type': 'info',
            }
        }

