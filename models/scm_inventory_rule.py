# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ScmInventoryRule(models.Model):
    _name = 'scm.inventory.rule'
    _description = 'Safety Stock Rules'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'product_id, product_category_id, company_id'

    name = fields.Char('Rule Name', required=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', 'Product', 
                                domain=[('type', 'in', ['product', 'consu'])])
    product_category_id = fields.Many2one('product.category', 'Product Category')
    safety_stock_qty = fields.Float('Safety Stock Quantity', default=0.0)
    min_stock_qty = fields.Float('Minimum Stock Quantity', default=0.0)
    reorder_point = fields.Float('Reorder Point', default=0.0)
    max_stock_qty = fields.Float('Maximum Stock Quantity', default=0.0)
    priority = fields.Selection([
        ('1', 'Low'),
        ('2', 'Medium'),
        ('3', 'High'),
        ('4', 'Critical')
    ], string='Priority', default='2')
    lead_time = fields.Integer('Lead Time (Days)', default=0)
    avg_daily_usage = fields.Float('Average Daily Usage', compute='_compute_avg_daily_usage', store=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    
    @api.constrains('product_id', 'product_category_id')
    def _check_product_or_category(self):
        for rule in self:
            if not rule.product_id and not rule.product_category_id:
                raise ValidationError(_("You must specify either a product or a product category."))
    
    @api.constrains('min_stock_qty', 'reorder_point', 'max_stock_qty', 'safety_stock_qty')
    def _check_quantity_consistency(self):
        for rule in self:
            if rule.min_stock_qty > rule.reorder_point:
                raise ValidationError(_("Minimum stock quantity cannot be greater than reorder point."))
            if rule.reorder_point > rule.max_stock_qty:
                raise ValidationError(_("Reorder point cannot be greater than maximum stock quantity."))
            if rule.safety_stock_qty > rule.min_stock_qty:
                raise ValidationError(_("Safety stock should not be greater than minimum stock."))
    
    @api.depends('product_id')
    def _compute_avg_daily_usage(self):
        for rule in self:
            if rule.product_id:
                # Calculate the average daily usage based on the last 90 days of stock moves
                date_from = fields.Date.today() - fields.Relativedelta(days=90)
                domain = [
                    ('product_id', '=', rule.product_id.id),
                    ('state', '=', 'done'),
                    ('date', '>=', date_from)
                ]
                
                # Get outgoing moves (typically to customers or for production)
                moves = self.env['stock.move'].search(domain + [('location_dest_id.usage', 'in', ['customer', 'production'])])
                
                if moves:
                    total_qty = sum(move.product_qty for move in moves)
                    rule.avg_daily_usage = total_qty / 90.0
                else:
                    rule.avg_daily_usage = 0.0
            else:
                rule.avg_daily_usage = 0.0
    
    def calculate_safety_stock(self):
        """Calculate safety stock based on average daily usage and lead time"""
        self.ensure_one()
        if self.lead_time and self.avg_daily_usage:
            safety_factor = 1.5  # Adjustable factor based on service level desired
            calculated_safety = self.avg_daily_usage * self.lead_time * safety_factor
            self.write({'safety_stock_qty': calculated_safety})
        return True
    
    def calculate_reorder_point(self):
        """Calculate reorder point based on lead time demand and safety stock"""
        self.ensure_one()
        if self.lead_time and self.avg_daily_usage:
            lead_time_demand = self.avg_daily_usage * self.lead_time
            reorder = lead_time_demand + self.safety_stock_qty
            self.write({'reorder_point': reorder})
        return True
    
    @api.model
    def get_applicable_rule(self, product, warehouse=None):
        """Find the most specific applicable rule for a product"""
        domain = [('active', '=', True)]
        
        if warehouse:
            domain += ['|', ('warehouse_id', '=', warehouse.id), ('warehouse_id', '=', False)]
            
        # Try to find a rule specific to this product
        if product:
            product_rules = self.search(domain + [('product_id', '=', product.id)], limit=1)
            if product_rules:
                return product_rules[0]
                
            # If no product-specific rule, check for category rule
            category_rules = self.search(domain + [
                ('product_category_id', '=', product.categ_id.id),
                ('product_id', '=', False)
            ], limit=1)
            if category_rules:
                return category_rules[0]
                
            # Look for parent category rules if no direct category rule
            parent_category = product.categ_id.parent_id
            while parent_category and not category_rules:
                category_rules = self.search(domain + [
                    ('product_category_id', '=', parent_category.id),
                    ('product_id', '=', False)
                ], limit=1)
                if category_rules:
                    return category_rules[0]
                parent_category = parent_category.parent_id
        
        # Return default rule if exists
        default_rule = self.search(domain + [
            ('product_id', '=', False),
            ('product_category_id', '=', False)
        ], limit=1)
        
        return default_rule if default_rule else False