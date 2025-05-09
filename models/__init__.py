# -*- coding: utf-8 -*-

# Base models
from . import scm_consolidation
from . import scm_consolidated_line
from . import scm_change_log
from . import scm_inventory_rule
from . import scm_forecast
from . import stock_quant

# Purchase related models
from . import purchase_order
from . import stock_picking
from . import stock_move
from . import purchase_request
from . import purchase_order_line
from . import blanket_order

# New import
from . import scm_forecast_template
from . import fulfillment_plan
