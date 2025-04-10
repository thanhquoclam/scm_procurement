# -*- coding: utf-8 -*-

from . import scm_consolidation
from . import scm_consolidated_line
from . import purchase_request
from . import purchase_order
from . import purchase_order_line
from . import blanket_order

# Phase 2 additions
from . import scm_inventory_rule
from . import scm_forecast
from . import stock_quant
from ..wizards import validate_inventory_wizard
from ..wizards import scm_consolidation_wizard
