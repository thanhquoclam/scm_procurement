from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SCMForecastTemplate(models.Model):
    _name = 'scm.forecast.template'
    _description = 'Forecast Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Template Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    product_category_id = fields.Many2one('product.category', string='Product Category', tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', tracking=True)
    
    forecast_method = fields.Selection([
        ('ma', 'Moving Average'),
        ('es', 'Exponential Smoothing'),
    ], string='Forecast Method', required=True, tracking=True)
    forecast_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Forecast Period', required=True, tracking=True)
    seasonality_factor = fields.Float(string='Seasonality Factor', tracking=True)
    trend_factor = fields.Float(string='Trend Factor', tracking=True)
    
    # Moving Average Parameters
    ma_period = fields.Integer(string='MA Period', tracking=True)
    ma_weight = fields.Float(string='MA Weight', tracking=True)
    
    # Exponential Smoothing Parameters
    alpha = fields.Float(string='Alpha (Level)', tracking=True)
    beta = fields.Float(string='Beta (Trend)', tracking=True)
    gamma = fields.Float(string='Gamma (Seasonality)', tracking=True)
    
    historical_data_ids = fields.One2many('scm.forecast.historical.data', 'template_id', string='Historical Data')
    
    @api.constrains('product_id', 'product_category_id')
    def _check_product_category(self):
        for record in self:
            if record.product_id and record.product_category_id:
                raise ValidationError(_("You cannot set both Product and Product Category. Please choose one."))
    
    @api.constrains('forecast_method', 'ma_period', 'ma_weight', 'alpha', 'beta', 'gamma')
    def _check_forecast_parameters(self):
        for record in self:
            if record.forecast_method == 'ma':
                if not record.ma_period or not record.ma_weight:
                    raise ValidationError(_("Moving Average method requires both Period and Weight parameters."))
            elif record.forecast_method == 'es':
                if not record.alpha or not record.beta or not record.gamma:
                    raise ValidationError(_("Exponential Smoothing method requires Alpha, Beta, and Gamma parameters."))

class SCMForecastHistoricalData(models.Model):
    _name = 'scm.forecast.historical.data'
    _description = 'Forecast Historical Data'
    _order = 'date desc'

    template_id = fields.Many2one('scm.forecast.template', string='Template', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    
    @api.constrains('date', 'template_id')
    def _check_unique_date(self):
        for record in self:
            duplicate = self.search([
                ('template_id', '=', record.template_id.id),
                ('date', '=', record.date),
                ('id', '!=', record.id)
            ])
            if duplicate:
                raise ValidationError(_("Duplicate date found for this template.")) 