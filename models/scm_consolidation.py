# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


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
        ('selecting_lines', 'Selecting Lines'),
        ('in_progress', 'In Progress'),
        ('validated', 'Validated'),
        ('inventory_validation', 'Inventory Validation'),
        ('po_creation', 'PO Creation'),
        ('po_created', 'PO Created'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, required=True)
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        relation='scm_consolidation_category_rel',
        column1='consolidation_id',
        column2='category_id',
        help='Filter PRs by these product categories. Leave empty to include all categories.',
        tracking=True
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
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'consolidation_id',
        string='Purchase Orders',
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
            session.po_count = self.env['purchase.order'].search_count([
                ('consolidation_id', '=', session.id)
            ])

    def _compute_pr_count(self):
        for session in self:
            purchase_requests = self.env['purchase.request'].search([
                ('consolidation_ids', 'in', session.id)
            ])
            session.pr_count = len(purchase_requests)

    def action_start_consolidation(self):
        """Start the consolidation process."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Consolidation can only be started from draft state.'))

        if not self.date_from or not self.date_to:
            raise UserError(_('Please set start and end dates.'))

        if self.date_from > self.date_to:
            raise UserError(_('End date cannot be earlier than start date.'))

        # Search for approved purchase requests in the date range
        domain = [
            ('state', '=', 'approved'),
            ('line_ids.date_required', '>=', self.date_from),
            ('line_ids.date_required', '<=', self.date_to)
        ]
        
        if self.category_ids:
            domain.append(('line_ids.product_id.categ_id', 'in', self.category_ids.ids))
        
        _logger.info("Searching for PRs with domain: %s", domain)
        purchase_requests = self.env['purchase.request'].search(domain)
        _logger.info("Found %d purchase requests", len(purchase_requests))
        
        if not purchase_requests:
            raise UserError(_('No approved purchase requests found for the selected period.'))
        
        # Link the purchase requests to this session
        self.write({
            'state': 'selecting_lines',
            'purchase_request_ids': [(6, 0, purchase_requests.ids)]
        })
        
        return {
            'name': _('Select Lines for Consolidation'),
            'type': 'ir.actions.act_window',
            'res_model': 'select.pr.lines.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    def _process_pr_lines_safely(self, pr_lines, safe_self=None):
        """Process purchase request lines using ORM but with safe approach."""
        _logger.info("Processing purchase request lines: %s", pr_lines)
        
        if not pr_lines:
            _logger.warning("No purchase request lines provided")
            return False
        
        if safe_self is None:
            safe_self = self.with_context(tracking_disable=True, mail_notrack=True)
        
        # Dictionary to group PR lines by product
        product_lines = {}
        
        # Process each line
        for line in pr_lines:
            _logger.info("Processing line: %s", line)
            if not line.product_id:
                continue
                
            product_id = line.product_id.id
            
            # Group by product
            if product_id not in product_lines:
                product_lines[product_id] = {
                    'product': line.product_id,
                    'uom': line.product_uom_id,
                    'total_qty': 0,
                    'pr_lines': [],
                    'earliest_date': line.date_required or line.request_id.date_start,
                }
            
            # Update group data
            data = product_lines[product_id]
            data['total_qty'] += line.product_qty
            data['pr_lines'].append(line)
            
            # Update earliest date needed
            line_date = line.date_required or line.request_id.date_start
            if line_date and (not data['earliest_date'] or line_date < data['earliest_date']):
                data['earliest_date'] = line_date
        
        _logger.info("Product lines grouped: %s", product_lines)
        
        # Process each product group to create/update consolidated lines
        created_lines = []
        for product_id, data in product_lines.items():
            try:
                _logger.info("Creating/updating consolidated line for product: %s", product_id)
                ConsolidatedLine = self.env['scm.consolidated.pr.line'].with_context(
                    tracking_disable=True, 
                    mail_notrack=True
                )
                
                # Check if a consolidated line already exists for this product
                existing_line = safe_self.consolidated_line_ids.filtered(
                    lambda l: l.product_id.id == product_id
                )
                
                # Convert pr_lines list to recordset
                pr_line_ids = [(6, 0, [line.id for line in data['pr_lines']])]
                
                if existing_line:
                    _logger.info("Updating existing line: %s", existing_line)
                    # Update existing line
                    existing_line.write({
                        'total_quantity': data['total_qty'],
                        'purchase_request_line_ids': pr_line_ids,
                        'earliest_date_required': data['earliest_date'],
                    })
                    created_lines.append(existing_line)
                else:
                    _logger.info("Creating new consolidated line for product: %s", product_id)
                    # Create new consolidated line
                    new_line = ConsolidatedLine.create({
                        'consolidation_id': safe_self.id,
                        'product_id': product_id,
                        'product_uom_id': data['uom'].id,
                        'total_quantity': data['total_qty'],
                        'purchase_request_line_ids': pr_line_ids,
                        'earliest_date_required': data['earliest_date'],
                        'state': 'draft'
                    })
                    _logger.info("Created new consolidated line: %s", new_line)
                    created_lines.append(new_line)
            except Exception as line_err:
                _logger.error("Error processing product %s: %s", product_id, str(line_err))
                # Continue to next product
        
        # Refresh the record to get the updated consolidated lines
        safe_self.invalidate_recordset()
        
        # Log the current state of consolidated lines
        _logger.info("Current consolidated lines before recompute: %s", safe_self.consolidated_line_ids)
        _logger.info("Created/Updated lines: %s", created_lines)
        
        # Force a recompute of the consolidated lines
        for line in safe_self.consolidated_line_ids:
            line._compute_available_quantity()
            line._compute_quantity_to_purchase()
            line._compute_inventory_status()
        
        # Log final state
        _logger.info("Final consolidated lines after recompute: %s", safe_self.consolidated_line_ids)
        
        # Update the session state to in_progress
        safe_self.write({'state': 'in_progress'})
        
        return True

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
        if self.state != 'validated':
            raise UserError(_("Inventory validation can only be started from Validated state."))
        
        # Update state to inventory validation
        self.write({'state': 'inventory_validation'})
        
        # Get consolidated lines with inventory issues
        lines_with_issues = self.consolidated_line_ids.filtered(
            lambda l: l.inventory_status in ['below_safety', 'below_reorder'] and l.product_id.type in ['product', 'consu']
        )
        
        # Create wizard lines
        wizard_line_vals = []
        for line in lines_with_issues:
            wizard_line_vals.append({
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'consolidated_line_id': line.id,
                'available_qty': line.available_quantity,
                'required_quantity': line.total_quantity,
                'inventory_notes': line.notes or '',
            })
        
        return {
            'name': _('Validate Inventory'),
            'type': 'ir.actions.act_window',
            'res_model': 'validate.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consolidation_id': self.id,
                'default_warehouse_id': self.warehouse_id.id,
                'default_line_ids': wizard_line_vals,
            }
        }

    def button_validate_inventory(self):
        """Open inventory validation wizard"""
        self.ensure_one()
        
        if self.state != 'inventory_validation':
            raise UserError(_("Inventory validation can only be performed in Inventory Validation state."))
        
        # Get consolidated lines with inventory issues
        lines_with_issues = self.consolidated_line_ids.filtered(
            lambda l: l.inventory_status in ['below_safety', 'below_reorder'] and l.product_id.type in ['product', 'consu']
        )
        
        # Create wizard lines
        wizard_line_vals = []
        for line in lines_with_issues:
            wizard_line_vals.append({
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'consolidated_line_id': line.id,
                'available_qty': line.available_quantity,
                'required_quantity': line.total_quantity,
                'inventory_notes': line.notes or '',
            })
        
        return {
            'name': _('Validate Inventory'),
            'type': 'ir.actions.act_window',
            'res_model': 'validate.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consolidation_id': self.id,
                'default_warehouse_id': self.warehouse_id.id,
                'default_line_ids': wizard_line_vals,
            }
        }

    def action_approve_inventory(self):
        """Approve the inventory validation."""
        self.ensure_one()
        return self.write({
            'state': 'approved'
        })

    def action_move_to_po_creation(self):
        """Move the consolidation session to PO creation state."""
        self.ensure_one()
        
        if self.state != 'po_creation':
            raise UserError(_("Cannot move to PO creation from current state."))
            
        # Update state to PO created
        self.write({
            'state': 'po_created',
            'po_creation_date': fields.Datetime.now()
        })
        
        # Return action to mark as done
        return {
            'name': _('Mark as Done'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.pr.consolidation.session',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_id': self.id,
                'default_state': 'done'
            }
        }

    def action_create_po(self):
        self.ensure_one()
        
        if self.state != 'approved':
            raise UserError(_("Purchase orders can only be created from approved state."))
            
        # Update state to po_creation
        self.write({'state': 'po_creation'})
        
        # Create wizard with context
        return {
            'name': _('Create Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.create.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consolidation_id': self.id,
                'default_date_order': fields.Datetime.now(),
                'default_currency_id': self.env.company.currency_id.id,
                'default_line_ids': [(0, 0, {
                    'consolidated_line_id': line.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity_to_purchase': line.quantity_to_purchase,
                    'price_unit': line.purchase_price,
                    'vendor_id': line.suggested_vendor_id.id if line.suggested_vendor_id else False,
                }) for line in self.consolidated_line_ids.filtered(lambda l: l.quantity_to_purchase > 0)]
            }
        }

    def action_mark_done(self):
        """Mark the consolidation session as done."""
        self.ensure_one()
        return self.write({
            'state': 'done'
        })

    def action_open_po_creation_wizard(self):
        """Open the PO creation wizard."""
        self.ensure_one()
        if self.state != 'po_creation':
            raise UserError(_("Cannot open PO creation wizard from current state."))
            
        # Get consolidated lines with quantity to purchase > 0
        consolidated_lines = self.consolidated_line_ids.filtered(
            lambda l: l.quantity_to_purchase > 0
        )
        
        # Create wizard line values
        wizard_line_vals = []
        for line in consolidated_lines:
            wizard_line_vals.append((0, 0, {
                'consolidated_line_id': line.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'quantity_to_purchase': line.quantity_to_purchase,
                'price_unit': line.purchase_price,
                'vendor_id': line.suggested_vendor_id.id if line.suggested_vendor_id else False,
            }))
            
        return {
            'name': _('Create Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'scm.create.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consolidation_id': self.id,
                'default_currency_id': self.currency_id.id if self.currency_id else self.env.company.currency_id.id,
                'default_line_ids': wizard_line_vals,
                'default_product_id': consolidated_lines[0].product_id.id if consolidated_lines else False,
            }
        }

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
        self.ensure_one()
        action = {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
            'context': {'default_consolidation_id': self.id},
        }
        return action

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            'name': _('Purchase Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.purchase_request_ids.ids)],
            'context': {'default_consolidation_id': self.id},
        }
        return action
    
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

    def button_inventory_approved(self):
        """Approve the inventory validation and move to approved state."""
        self.ensure_one()
        
        if self.state != 'inventory_validation':
            raise UserError(_("Inventory can only be approved when in Inventory Validation state."))
        
        # Check if there are any critical shortages that need manager approval
        if self.has_critical_shortages and not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_("Only Inventory Managers can approve sessions with critical shortages."))
        
        # Update the session
        self.write({
            'state': 'approved',
            'inventory_validated': True,
            'inventory_validation_date': fields.Datetime.now(),
            'inventory_validated_by': self.env.user.id,
            'pending_approval': False
        })
        
        # Log the approval in the chatter
        self.message_post(
            body=_("Inventory validation approved by %s") % self.env.user.name,
            subtype_id=self.env.ref('mail.mt_note').id
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Inventory Approved'),
                'message': _("The inventory validation has been approved. You can now proceed with creating purchase orders."),
                'sticky': False,
                'type': 'success',
            }
        }

    @api.onchange('consolidated_line_ids')
    def _onchange_consolidated_line_ids(self):
        """Update purchase requests when consolidated lines change."""
        if self.consolidated_line_ids:
            # Get all purchase request IDs from the current lines
            pr_ids = self.consolidated_line_ids.mapped('purchase_request_line_ids.request_id').ids
            
            # Update the purchase_request_ids field
            self.purchase_request_ids = [(6, 0, pr_ids)]
            
            # If no lines remain, reset the state to draft
            if not self.consolidated_line_ids:
                self.state = 'draft'

    def write(self, vals):
        """Override write to handle consolidated line removal."""
        result = super(PRConsolidationSession, self).write(vals)
        
        # Check if consolidated_line_ids was modified
        if 'consolidated_line_ids' in vals:
            # Get all purchase request IDs from the current lines
            pr_ids = self.consolidated_line_ids.mapped('purchase_request_line_ids.request_id').ids
            
            # Update the purchase_request_ids field
            self.write({'purchase_request_ids': [(6, 0, pr_ids)]})
            
            # If no lines remain, reset the state to draft
            if not self.consolidated_line_ids:
                self.write({'state': 'draft'})
        
        return result

