# -*- coding: utf-8 -*-
{
    'name': 'Supply Chain Management',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Advanced supply chain management with PR consolidation',
    'description': """
Supply Chain Management
======================
This module extends Odoo's procurement capabilities with:
- Purchase Request consolidation
- Inventory validation
- Purchase Order suggestions based on Purchase Agreements
- PR fulfillment tracking
- Change management for procurement processes
    """,
    'author': 'Thanh Lam',
    'website': 'https://suno.vn',
    'depends': [
        'base',
        'mail',
        'product',
        'stock',
        'purchase',
        'purchase_request'
    ],
    'data': [
        # Security
        'security/scm_security.xml',
        'security/ir.model.access.csv',
        
        # Models and Data
        'data/scm_sequence.xml',
        'data/scm_inventory_data.xml',
        
        # Views
        'views/scm_consolidation_views.xml',
        'views/scm_consolidated_line_views.xml',
        'views/purchase_request_views.xml',
        'views/scm_inventory_rule_views.xml',
        'views/scm_forecast_views.xml',
        'views/purchase_order_views.xml',
        
        # Wizards
        'wizards/validate_inventory_wizard_views.xml',
        'wizards/scm_consolidation_wizard_views.xml',
        
        # Reports
        'report/scm_consolidation_report.xml',
        # 'report/scm_report.xml',  # Add base report file
        # 'report/scm_inventory_validation_report.xml',
        
        # Menu (always last)
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
