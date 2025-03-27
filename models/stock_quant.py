# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class StockQuantExtended(models.Model):
    _inherit = 'stock.quant'
    
    forecasted_qty = fields.Float('Forecasted Qty', compute='_compute_forecasted_qty', store=False)
    safety_stock_level = fields.Float('Safety Stock Level', compute='_compute_safety_stock')
    reorder_point = fields.Float('Reorder Point', compute='_compute_safety_stock')
    stock_status = fields.Selection([
        ('below_safety', 'Below Safety Stock'),
        ('below_reorder', 'Below Reorder Point'),
        ('normal', 'Normal'),
        ('excess', 'Excess')
    ], string='Stock Status', compute='_compute_stock_status', store=True)
    days_of_stock = fields.Float('Days of Stock', compute='_compute_days_of_stock')
    is_critical = fields.Boolean('Critical Shortage', compute='_compute_stock_status', store=True)
    
    def _compute_forecasted_qty(self):
        """Compute forecasted quantity based on current stock and planned movements"""
        for quant in self:
            # Current quantity already in quant
            current_qty = quant.quantity
            
            # Scheduled inbound deliveries (within next 30 days)
            date_limit = fields.Datetime.now() + timedelta(days=30)
            inbound_domain = [
                ('product_id', '=', quant.product_id.id),
                ('location_dest_id', '=', quant.location_id.id),
                ('state', 'in', ['assigned', 'partially_available']),
                ('date', '<=', date_limit)
            ]
            
            inbound_moves = self.env['stock.move'].search(inbound_domain)
            inbound_qty = sum(inbound_moves.mapped('product_qty')) if inbound_moves else 0
            
            # Scheduled outbound deliveries (within next 30 days)
            outbound_domain = [
                ('product_id', '=', quant.product_id.id),
                ('location_id', '=', quant.location_id.id),
                ('state', 'in', ['assigned', 'partially_available']),
                ('date', '<=', date_limit)
            ]
            
            outbound_moves = self.env['stock.move'].search(outbound_domain)
            outbound_qty = sum(outbound_moves.mapped('product_qty')) if outbound_moves else 0
            
            # Forecasted demand from sales forecast
            forecast_domain = [
                ('product_id', '=', quant.product_id.id),
                ('warehouse_id.lot_stock_id', '=', quant.location_id.id),
                ('date', '<=', fields.Date.today() + timedelta(days=30)),
                ('state', '=', 'confirmed')
            ]
            
            forecasts = self.env['scm.forecast.line'].search(forecast_domain)
            forecast_demand = sum(forecasts.mapped('forecast_qty')) if forecasts else 0
            
            # Final forecasted quantity
            quant.forecasted_qty = current_qty + inbound_qty - outbound_qty - forecast_demand
    
    def _compute_safety_stock(self):
        """Compute safety stock levels based on inventory rules"""
        inventory_rule_obj = self.env['scm.inventory.rule']
        
        for quant in self:
            warehouse = False
            if quant.location_id.usage == 'internal':
                warehouse = self.env['stock.warehouse'].search([
                    ('lot_stock_id', '=', quant.location_id.id)
                ], limit=1)
                
                if not warehouse:
                    warehouse = self.env['stock.warehouse'].search([
                        ('view_location_id', 'parent_of', quant.location_id.id)
                    ], limit=1)
            
            # Find applicable rule
            rule = inventory_rule_obj.get_applicable_rule(quant.product_id, warehouse)
            
            if rule:
                quant.safety_stock_level = rule.safety_stock_qty
                quant.reorder_point = rule.reorder_point
            else:
                quant.safety_stock_level = 0.0
                quant.reorder_point = 0.0
    
    @api.depends('quantity', 'safety_stock_level', 'reorder_point')
    def _compute_stock_status(self):
        """Determine stock status based on quantity and inventory rules"""
        for quant in self:
            if quant.quantity <= 0:
                quant.stock_status = 'below_safety'
                quant.is_critical = True
            elif quant.quantity < quant.safety_stock_level:
                quant.stock_status = 'below_safety'
                quant.is_critical = True
            elif quant.quantity < quant.reorder_point:
                quant.stock_status = 'below_reorder'
                quant.is_critical = False
            elif quant.quantity > quant.reorder_point * 2:  # Simple definition of excess
                quant.stock_status = 'excess'
                quant.is_critical = False
            else:
                quant.stock_status = 'normal'
                quant.is_critical = False
    
    def _compute_days_of_stock(self):
        """Calculate days of inventory based on average daily usage"""
        for quant in self:
            # Find applicable rule to get average daily usage
            warehouse = False
            if quant.location_id.usage == 'internal':
                warehouse = self.env['stock.warehouse'].search([
                    ('lot_stock_id', '=', quant.location_id.id)
                ], limit=1)
                
                if not warehouse:
                    warehouse = self.env['stock.warehouse'].search([
                        ('view_location_id', 'parent_of', quant.location_id.id)
                    ], limit=1)
            
            # Get rule with avg_daily_usage
            rule = self.env['scm.inventory.rule'].get_applicable_rule(quant.product_id, warehouse)
            
            if rule and rule.avg_daily_usage > 0:
                quant.days_of_stock = quant.quantity / rule.avg_daily_usage
            else:
                # Default if no usage data
                quant.days_of_stock = 0.0
    
    def action_view_inventory_rule(self):
        """Open the inventory rule for this product"""
        self.ensure_one()
        
        warehouse = False
        if self.location_id.usage == 'internal':
            warehouse = self.env['stock.warehouse'].search([
                ('lot_stock_id', '=', self.location_id.id)
            ], limit=1)
            
            if not warehouse:
                warehouse = self.env['stock.warehouse'].search([
                    ('view_location_id', 'parent_of', self.location_id.id)
                ], limit=1)
        
        rule = self.env['scm.inventory.rule'].get_applicable_rule(self.product_id, warehouse)
        
        if not rule:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Create Inventory Rule'),
                'res_model': 'scm.inventory.rule',
                'view_mode': 'form',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_warehouse_id': warehouse.id if warehouse else False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inventory Rule'),
            'res_model': 'scm.inventory.rule',
            'res_id': rule.id,
            'view_mode': 'form',
        }
    
    def action_check_stock_sufficiency(self):
        """Check if stock is sufficient for upcoming demand"""
        self.ensure_one()
        
        # Compute forecasted quantity for next 30 days
        self._compute_forecasted_qty()
        
        # Get inventory rule data
        self._compute_safety_stock()
        
        message = ''
        if self.forecasted_qty < self.safety_stock_level:
            message = _("WARNING: Forecasted quantity (%s) is below safety stock level (%s).") % (
                self.forecasted_qty, self.safety_stock_level)
        elif self.forecasted_qty < self.reorder_point:
            message = _("NOTICE: Forecasted quantity (%s) is below reorder point (%s).") % (
                self.forecasted_qty, self.reorder_point)
        else:
            message = _("Stock level is sufficient. Forecasted quantity (%s) is above reorder point (%s).") % (
                self.forecasted_qty, self.reorder_point)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stock Sufficiency Check'),
                'message': message,
                'sticky': False,
                'type': 'info' if self.forecasted_qty >= self.safety_stock_level else 'warning',
            }
        }