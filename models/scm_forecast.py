# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ScmForecast(models.Model):
    _name = 'scm.forecast'
    _description = 'Inventory Forecast'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, product_id'
    
    name = fields.Char('Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', 'Company', required=True, 
                               default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', 'Product', required=True,
                               domain=[('type', 'in', ['product', 'consu'])])
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    date = fields.Date('Forecast Date', required=True, default=fields.Date.today)
    forecast_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], string='Forecast Period', default='monthly')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', readonly=True)
    forecast_qty = fields.Float('Forecasted Quantity', required=True)
    actual_qty = fields.Float('Actual Quantity', readonly=True)
    variance = fields.Float('Variance', compute='_compute_variance', store=True)
    variance_percent = fields.Float('Variance %', compute='_compute_variance', store=True)
    # Properly define the selection options for the state field
    state = fields.Selection(
        selection=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')
    ], string='Status', default='draft')
    notes = fields.Text('Notes')
    forecast_line_ids = fields.One2many('scm.forecast.line', 'forecast_id', 'Forecast Lines')
    is_template = fields.Boolean('Is Template', default=False)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('scm.forecast') or _('New')
        return super(ScmForecast, self).create(vals)
    
    @api.depends('forecast_qty', 'actual_qty')
    def _compute_variance(self):
        for forecast in self:
            if forecast.forecast_qty and forecast.actual_qty:
                forecast.variance = forecast.actual_qty - forecast.forecast_qty
                forecast.variance_percent = (forecast.variance / forecast.forecast_qty) * 100 if forecast.forecast_qty else 0
            else:
                forecast.variance = 0
                forecast.variance_percent = 0
    
    def action_confirm(self):
        for forecast in self:
            forecast.write({'state': 'confirmed'})
        return True
    
    def action_done(self):
        for forecast in self:
            # Update with actual quantities
            stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', forecast.product_id.id),
                ('location_id.warehouse_id', '=', forecast.warehouse_id.id),
                ('location_id.usage', '=', 'internal')
            ], limit=1)
            
            actual_qty = sum(stock_quant.mapped('quantity')) if stock_quant else 0
            forecast.write({
                'actual_qty': actual_qty,
                'state': 'done'
            })
        return True
    
    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True
    
    def generate_forecast_lines(self):
        """Generate time-phased forecast lines based on the forecast period"""
        self.ensure_one()
        if self.forecast_line_ids:
            self.forecast_line_ids.unlink()
            
        forecast_lines = []
        start_date = self.date
        
        # Define the number of periods and duration based on forecast_period
        periods = {
            'daily': {'count': 30, 'delta': timedelta(days=1)},
            'weekly': {'count': 12, 'delta': timedelta(weeks=1)},
            'monthly': {'count': 6, 'delta': relativedelta(months=1)},
            'quarterly': {'count': 4, 'delta': relativedelta(months=3)}
        }
        
        count = periods[self.forecast_period]['count']
        delta = periods[self.forecast_period]['delta']
        
        for i in range(count):
            # Create forecast line for each period
            line_date = start_date + (delta * i)
            
            # Distribute forecast quantity based on historical patterns
            # For now using a simple distribution
            period_qty = self.forecast_qty / count
            
            # Create forecast line
            line_vals = {
                'forecast_id': self.id,
                'date': line_date,
                'forecast_qty': period_qty,
                'product_id': self.product_id.id,
                'warehouse_id': self.warehouse_id.id
            }
            forecast_lines.append((0, 0, line_vals))
            
        if forecast_lines:
            self.write({'forecast_line_ids': forecast_lines})
        
        return True
    
    def copy_from_template(self, template_id):
        """Copy forecast pattern from a template"""
        template = self.browse(template_id)
        if not template or not template.is_template:
            raise ValidationError(_("Selected forecast is not a template."))
            
        self.ensure_one()
        if self.forecast_line_ids:
            self.forecast_line_ids.unlink()
            
        # Copy template lines with adjusted dates
        forecast_lines = []
        date_diff = self.date - template.date if template.date else timedelta(days=0)
        
        for line in template.forecast_line_ids:
            new_date = line.date + date_diff if line.date else self.date
            line_vals = {
                'forecast_id': self.id,
                'date': new_date,
                'forecast_qty': line.forecast_qty,
                'product_id': self.product_id.id,
                'warehouse_id': self.warehouse_id.id
            }
            forecast_lines.append((0, 0, line_vals))
            
        if forecast_lines:
            self.write({'forecast_line_ids': forecast_lines})
            
        return True


class ScmForecastLine(models.Model):
    _name = 'scm.forecast.line'
    _description = 'Inventory Forecast Line'
    _order = 'date, product_id'
    
    forecast_id = fields.Many2one('scm.forecast', 'Forecast', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='forecast_id.company_id')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    date = fields.Date('Forecast Date', required=True)
    forecast_qty = fields.Float('Forecasted Quantity', required=True)
    actual_qty = fields.Float('Actual Quantity', readonly=True)
    expected_inventory = fields.Float('Expected Inventory', compute='_compute_expected_inventory', store=True)
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', readonly=True)
    state = fields.Selection(related='forecast_id.state', string='Status', store=True)
    notes = fields.Text('Notes')
    
    @api.depends('product_id', 'warehouse_id', 'date', 'forecast_qty')
    def _compute_expected_inventory(self):
        for line in self:
            # Get current stock
            stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id.warehouse_id', '=', line.warehouse_id.id),
                ('location_id.usage', '=', 'internal')
            ])
            
            current_qty = sum(stock_quant.mapped('quantity')) if stock_quant else 0
            
            # Get incoming stock before the forecast date
            incoming_domain = [
                ('product_id', '=', line.product_id.id),
                ('location_dest_id.warehouse_id', '=', line.warehouse_id.id),
                ('location_dest_id.usage', '=', 'internal'),
                ('state', 'in', ['assigned', 'partially_available']),
                ('date', '<=', line.date)
            ]
            
            incoming_moves = self.env['stock.move'].search(incoming_domain)
            incoming_qty = sum(incoming_moves.mapped('product_qty')) if incoming_moves else 0
            
            # Get outgoing stock before the forecast date
            outgoing_domain = [
                ('product_id', '=', line.product_id.id),
                ('location_id.warehouse_id', '=', line.warehouse_id.id),
                ('location_id.usage', '=', 'internal'),
                ('state', 'in', ['assigned', 'partially_available']),
                ('date', '<=', line.date)
            ]
            
            outgoing_moves = self.env['stock.move'].search(outgoing_domain)
            outgoing_qty = sum(outgoing_moves.mapped('product_qty')) if outgoing_moves else 0
            
            # Calculate expected inventory
            line.expected_inventory = current_qty + incoming_qty - outgoing_qty - line.forecast_qty