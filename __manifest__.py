# -*- coding: utf-8 -*-
{
    'name': 'Supply Chain Management',
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Supply Chain Management Module',
    'description': """
        Supply Chain Management Module for Odoo 17
        =========================================
        
        This module provides comprehensive supply chain management functionality including:
        - Purchase Request Management
        - Purchase Request Consolidation
        - Inventory Validation
        - Purchase Order Creation
        - Change Management
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail',
        'purchase',
        'purchase_request',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/scm_consolidation_views.xml',
        'views/scm_consolidated_line_views.xml',
        'views/scm_change_log_views.xml',
        'views/scm_change_log_mail_templates.xml',
        'views/scm_inventory_rule_views.xml',
        'views/scm_forecast_template_views.xml',
        'wizards/scm_consolidation_wizard_views.xml',
        'wizards/validate_inventory_wizard_views.xml',
        'wizards/select_pr_lines_wizard_views.xml',
        'wizards/create_po_wizard_views.xml',
        'wizards/fulfillment_suggestion_wizard_views.xml',
        'views/fulfillment_plan_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
