# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ForecastWizard(models.TransientModel):
    _name = 'forecast.wizard'
    _description = 'Inventory Forecast Wizard'
    
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    forecast_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], string='Forecast Period', default='monthly', required=True)
    
    forecasting_method = fields.Selection([
        ('historical', 'Historical Usage'),
        ('manual', 'Manual Input'),
        ('template', 'From Template')
    ], string='Forecasting Method', default='historical', required=True)
    
    start_date = fields.Date('Start Date', default=fields.Date.today, required=True)
    product_ids = fields.Many2many('product.product', string='Products',
                                   domain=[('type', 'in', ['product', 'consu'])])
    category_id = fields.Many2one('product.category', 'Product Category')
    
    template_id = fields.Many2one('scm.forecast', 'Forecast Template', 
                                  domain=[('is_template', '=', True)])
    
    line_ids = fields.One2many('forecast.wizard.line', 'wizard_id', 'Forecast Lines')
    
    consider_open_orders = fields.Boolean('Consider Open Orders', default=True)
    consider_historical_usage = fields.Boolean('Consider Historical Usage', default=True)
    historical_period = fields.Selection([
        ('30', 'Last 30 Days'),
        ('90', 'Last 90 Days'),
        ('180', 'Last 180 Days'),
        ('365', 'Last Year')
    ], string='Historical Period', default='90')
    
    @api.onchange('product_ids', 'warehouse_id', 'forecasting_method')
    def _onchange_products(self):
        """Generate forecast lines based on selected products"""
        self.ensure_one()
        
        # Clear existing lines
        self.line_ids = [(5, 0, 0)]
        
        if not self.product_ids or not self.warehouse_id:
            return
        
        forecast_lines = []
        
        for product in self.product_ids:
            # Calculate forecast quantity based on method
            if self.forecasting_method == 'historical':
                forecast_qty = self._calculate_from_historical(product)
            else:
                forecast_qty = 0.0
            
            # Create forecast line
            line_vals = {
                'wizard_id': self.id,
                'product_id': product.id,
                'warehouse_id': self.warehouse_id.id,
                'forecast_qty': forecast_qty,
                'uom_id': product.uom_id.id,
            }
            forecast_lines.append((0, 0, line_vals))
        
        self.line_ids = forecast_lines
    
    @api.onchange('category_id')
    def _onchange_category(self):
        """Filter products by category"""
        if self.category_id:
            domain = [('categ_id', 'child_of', self.category_id.id), ('type', 'in', ['product', 'consu'])]
            return {'domain': {'product_ids': domain}}
    
    def _calculate_from_historical(self, product):
        """Calculate forecast based on historical usage"""
        self.ensure_one()
        
        if not product or not self.warehouse_id:
            return 0.0
        
        # Default to 90 days if not specified
        days = int(self.historical_period) if self.historical_period else 90
        date_from = fields.Date.today() - fields.Relativedelta(days=days)
        
        # Get stock moves (outgoing) for this product
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '>=', date_from),
            ('location_id.warehouse_id', '=', self.warehouse_id.id),
            ('location_dest_id.usage', 'in', ['customer', 'production'])
        ]
        
        moves = self.env['stock.move'].search(domain)
        
        if not moves:
            return 0.0
        
        # Calculate total quantity
        total_qty = sum(moves.mapped('product_qty'))
        
        # Convert to forecast period
        avg_daily = total_qty / days
        
        if self.forecast_period == 'daily':
            return avg_daily
        elif self.forecast_period == 'weekly':
            return avg_daily * 7
        elif self.forecast_period == 'monthly':
            return avg_daily * 30
        elif self.forecast_period == 'quarterly':
            return avg_daily * 90
        else:
            return avg_daily
    
    def action_create_forecasts(self):
        """Create forecasts from wizard data"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_("No forecast lines to process."))
        
        forecast_obj = self.env['scm.forecast']
        forecasts_created = []
        
        for line in self.line_ids:
            if line.forecast_qty <= 0:
                continue
                
            # Create forecast
            forecast_vals = {
                'product_id': line.product_id.id,
                'warehouse_id': line.warehouse_id.id,
                'date': self.start_date,
                'forecast_period': self.forecast_period,
                'forecast_qty': line.forecast_qty,
                'notes': line.notes,
                'state': 'draft',
            }
            
            forecast = forecast_obj.create(forecast_vals)
            forecasts_created.append(forecast.id)
            
            # Generate forecast lines
            forecast.generate_forecast_lines()
            
            # Copy from template if selected
            if self.forecasting_method == 'template' and self.template_id:
                forecast.copy_from_template(self.template_id.id)
        
        if forecasts_created:
            # Show created forecasts
            return {
                'name': _('Created Forecasts'),
                'type': 'ir.actions.act_window',
                'res_model': 'scm.forecast',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', forecasts_created)],
            }
        else:
            return {'type': 'ir.actions.act_window_close'}


class ForecastWizardLine(models.TransientModel):
    _name = 'forecast.wizard.line'
    _description = 'Forecast Wizard Line'
    
    wizard_id = fields.Many2one('forecast.wizard', 'Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    current_stock = fields.Float('Current Stock', compute='_compute_stock_info')
    forecast_qty = fields.Float('Forecast Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', readonly=True)
    notes = fields.Text('Notes')
    
    @api.depends('product_id', 'warehouse_id')
    def _compute_stock_info(self):
        """Compute current stock information"""
        for line in self:
            if line.product_id and line.warehouse_id:
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.warehouse_id.lot_stock_id.id)
                ])
                
                line.current_stock = sum(stock_quant.mapped('quantity')) if stock_quant else 0.0
            else:
                line.current_stock = 0.0