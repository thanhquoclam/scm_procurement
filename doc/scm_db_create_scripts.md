-- Table: public.scm_pr_consolidation_session

-- DROP TABLE IF EXISTS public.scm_pr_consolidation_session;

CREATE TABLE IF NOT EXISTS public.scm_pr_consolidation_session
(
    id integer NOT NULL DEFAULT nextval('scm_pr_consolidation_session_id_seq'::regclass),
    user_id integer,
    company_id integer,
    warehouse_id integer NOT NULL,
    inventory_validated_by integer,
    total_stockout_items integer,
    total_below_safety integer,
    total_below_reorder integer,
    create_uid integer,
    write_uid integer,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    state character varying COLLATE pg_catalog."default",
    inventory_status character varying COLLATE pg_catalog."default",
    date_from date NOT NULL,
    date_to date NOT NULL,
    notes text COLLATE pg_catalog."default",
    inventory_validation_notes text COLLATE pg_catalog."default",
    inventory_validated boolean,
    has_inventory_issues boolean,
    has_critical_shortages boolean,
    pending_approval boolean,
    creation_date timestamp without time zone,
    validation_date timestamp without time zone,
    po_creation_date timestamp without time zone,
    inventory_validation_date timestamp without time zone,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    total_amount double precision,
    CONSTRAINT scm_pr_consolidation_session_pkey PRIMARY KEY (id),
    CONSTRAINT scm_pr_consolidation_session_company_id_fkey FOREIGN KEY (company_id)
        REFERENCES public.res_company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_pr_consolidation_session_create_uid_fkey FOREIGN KEY (create_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_pr_consolidation_session_inventory_validated_by_fkey FOREIGN KEY (inventory_validated_by)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_pr_consolidation_session_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_pr_consolidation_session_warehouse_id_fkey FOREIGN KEY (warehouse_id)
        REFERENCES public.stock_warehouse (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_pr_consolidation_session_write_uid_fkey FOREIGN KEY (write_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_pr_consolidation_session
    OWNER to odoo;

COMMENT ON TABLE public.scm_pr_consolidation_session
    IS 'Purchase Request Consolidation Session';

COMMENT ON COLUMN public.scm_pr_consolidation_session.user_id
    IS 'Responsible';

COMMENT ON COLUMN public.scm_pr_consolidation_session.company_id
    IS 'Company';

COMMENT ON COLUMN public.scm_pr_consolidation_session.warehouse_id
    IS 'Warehouse';

COMMENT ON COLUMN public.scm_pr_consolidation_session.inventory_validated_by
    IS 'Validated By';

COMMENT ON COLUMN public.scm_pr_consolidation_session.total_stockout_items
    IS 'Total Stockout Items';

COMMENT ON COLUMN public.scm_pr_consolidation_session.total_below_safety
    IS 'Items Below Safety Stock';

COMMENT ON COLUMN public.scm_pr_consolidation_session.total_below_reorder
    IS 'Items Below Reorder Point';

COMMENT ON COLUMN public.scm_pr_consolidation_session.create_uid
    IS 'Created by';

COMMENT ON COLUMN public.scm_pr_consolidation_session.write_uid
    IS 'Last Updated by';

COMMENT ON COLUMN public.scm_pr_consolidation_session.name
    IS 'Reference';

COMMENT ON COLUMN public.scm_pr_consolidation_session.state
    IS 'Status';

COMMENT ON COLUMN public.scm_pr_consolidation_session.inventory_status
    IS 'Inventory Status';

COMMENT ON COLUMN public.scm_pr_consolidation_session.date_from
    IS 'Start Date';

COMMENT ON COLUMN public.scm_pr_consolidation_session.date_to
    IS 'End Date';

COMMENT ON COLUMN public.scm_pr_consolidation_session.notes
    IS 'Notes';

COMMENT ON COLUMN public.scm_pr_consolidation_session.inventory_validation_notes
    IS 'Validation Notes';

COMMENT ON COLUMN public.scm_pr_consolidation_session.inventory_validated
    IS 'Inventory Validated';

COMMENT ON COLUMN public.scm_pr_consolidation_session.has_inventory_issues
    IS 'Has Inventory Issues';

COMMENT ON COLUMN public.scm_pr_consolidation_session.has_critical_shortages
    IS 'Has Critical Shortages';

COMMENT ON COLUMN public.scm_pr_consolidation_session.pending_approval
    IS 'Pending Inventory Approval';

COMMENT ON COLUMN public.scm_pr_consolidation_session.creation_date
    IS 'Creation Date';

COMMENT ON COLUMN public.scm_pr_consolidation_session.validation_date
    IS 'Validation Date';

COMMENT ON COLUMN public.scm_pr_consolidation_session.po_creation_date
    IS 'PO Creation Date';

COMMENT ON COLUMN public.scm_pr_consolidation_session.inventory_validation_date
    IS 'Inventory Validation Date';

COMMENT ON COLUMN public.scm_pr_consolidation_session.create_date
    IS 'Created on';

COMMENT ON COLUMN public.scm_pr_consolidation_session.write_date
    IS 'Last Updated on';

COMMENT ON COLUMN public.scm_pr_consolidation_session.total_amount
    IS 'Total Amount';


-- Table: public.scm_consolidated_pr_line

-- DROP TABLE IF EXISTS public.scm_consolidated_pr_line;

CREATE TABLE IF NOT EXISTS public.scm_consolidated_pr_line
(
    id integer NOT NULL DEFAULT nextval('scm_consolidated_pr_line_id_seq'::regclass),
    consolidation_id integer NOT NULL,
    product_id integer NOT NULL,
    product_uom_id integer NOT NULL,
    suggested_vendor_id integer,
    purchase_suggestion_id integer,
    company_id integer,
    exception_approved_by integer,
    warehouse_id integer,
    create_uid integer,
    write_uid integer,
    state character varying COLLATE pg_catalog."default" NOT NULL,
    priority character varying COLLATE pg_catalog."default",
    inventory_status character varying COLLATE pg_catalog."default",
    procurement_recommendation character varying COLLATE pg_catalog."default",
    earliest_date_required date,
    last_purchase_date date,
    notes text COLLATE pg_catalog."default",
    inventory_notes text COLLATE pg_catalog."default",
    total_quantity numeric NOT NULL,
    available_quantity numeric,
    quantity_to_purchase numeric,
    purchase_price numeric,
    subtotal numeric,
    turnover_rate numeric,
    quantity numeric,
    last_purchase_price numeric,
    avg_monthly_usage numeric,
    inventory_exception boolean,
    exception_approval_date timestamp without time zone,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    stock_coverage double precision,
    CONSTRAINT scm_consolidated_pr_line_pkey PRIMARY KEY (id),
    CONSTRAINT scm_consolidated_pr_line_consolidation_product_uniq UNIQUE (consolidation_id, product_id),
    CONSTRAINT scm_consolidated_pr_line_company_id_fkey FOREIGN KEY (company_id)
        REFERENCES public.res_company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_consolidated_pr_line_consolidation_id_fkey FOREIGN KEY (consolidation_id)
        REFERENCES public.scm_pr_consolidation_session (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT scm_consolidated_pr_line_create_uid_fkey FOREIGN KEY (create_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_consolidated_pr_line_exception_approved_by_fkey FOREIGN KEY (exception_approved_by)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_consolidated_pr_line_product_id_fkey FOREIGN KEY (product_id)
        REFERENCES public.product_product (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_consolidated_pr_line_product_uom_id_fkey FOREIGN KEY (product_uom_id)
        REFERENCES public.uom_uom (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_consolidated_pr_line_suggested_vendor_id_fkey FOREIGN KEY (suggested_vendor_id)
        REFERENCES public.res_partner (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_consolidated_pr_line_warehouse_id_fkey FOREIGN KEY (warehouse_id)
        REFERENCES public.stock_warehouse (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_consolidated_pr_line_write_uid_fkey FOREIGN KEY (write_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_consolidated_pr_line
    OWNER to odoo;

COMMENT ON TABLE public.scm_consolidated_pr_line
    IS 'Consolidated Purchase Request Line';

COMMENT ON COLUMN public.scm_consolidated_pr_line.consolidation_id
    IS 'Consolidation Session';

COMMENT ON COLUMN public.scm_consolidated_pr_line.product_id
    IS 'Product';

COMMENT ON COLUMN public.scm_consolidated_pr_line.product_uom_id
    IS 'Unit of Measure';

COMMENT ON COLUMN public.scm_consolidated_pr_line.suggested_vendor_id
    IS 'Suggested Vendor';

COMMENT ON COLUMN public.scm_consolidated_pr_line.purchase_suggestion_id
    IS 'Purchase Suggestion';

COMMENT ON COLUMN public.scm_consolidated_pr_line.company_id
    IS 'Company';

COMMENT ON COLUMN public.scm_consolidated_pr_line.exception_approved_by
    IS 'Exception Approved By';

COMMENT ON COLUMN public.scm_consolidated_pr_line.warehouse_id
    IS 'Warehouse';

COMMENT ON COLUMN public.scm_consolidated_pr_line.create_uid
    IS 'Created by';

COMMENT ON COLUMN public.scm_consolidated_pr_line.write_uid
    IS 'Last Updated by';

COMMENT ON COLUMN public.scm_consolidated_pr_line.state
    IS 'Status';

COMMENT ON COLUMN public.scm_consolidated_pr_line.priority
    IS 'Priority';

COMMENT ON COLUMN public.scm_consolidated_pr_line.inventory_status
    IS 'Inventory Status';

COMMENT ON COLUMN public.scm_consolidated_pr_line.procurement_recommendation
    IS 'Recommendation';

COMMENT ON COLUMN public.scm_consolidated_pr_line.earliest_date_required
    IS 'Earliest Date Required';

COMMENT ON COLUMN public.scm_consolidated_pr_line.last_purchase_date
    IS 'Last Purchase Date';

COMMENT ON COLUMN public.scm_consolidated_pr_line.notes
    IS 'Notes';

COMMENT ON COLUMN public.scm_consolidated_pr_line.inventory_notes
    IS 'Inventory Notes';

COMMENT ON COLUMN public.scm_consolidated_pr_line.total_quantity
    IS 'Total Quantity';

COMMENT ON COLUMN public.scm_consolidated_pr_line.available_quantity
    IS 'Available Quantity';

COMMENT ON COLUMN public.scm_consolidated_pr_line.quantity_to_purchase
    IS 'Quantity to Purchase';

COMMENT ON COLUMN public.scm_consolidated_pr_line.purchase_price
    IS 'Estimated Price';

COMMENT ON COLUMN public.scm_consolidated_pr_line.subtotal
    IS 'Subtotal';

COMMENT ON COLUMN public.scm_consolidated_pr_line.turnover_rate
    IS 'Turnover Rate';

COMMENT ON COLUMN public.scm_consolidated_pr_line.quantity
    IS 'Quantity';

COMMENT ON COLUMN public.scm_consolidated_pr_line.last_purchase_price
    IS 'Last Purchase Price';

COMMENT ON COLUMN public.scm_consolidated_pr_line.avg_monthly_usage
    IS 'Avg Monthly Usage';

COMMENT ON COLUMN public.scm_consolidated_pr_line.inventory_exception
    IS 'Inventory Exception';

COMMENT ON COLUMN public.scm_consolidated_pr_line.exception_approval_date
    IS 'Exception Approval Date';

COMMENT ON COLUMN public.scm_consolidated_pr_line.create_date
    IS 'Created on';

COMMENT ON COLUMN public.scm_consolidated_pr_line.write_date
    IS 'Last Updated on';

COMMENT ON COLUMN public.scm_consolidated_pr_line.stock_coverage
    IS 'Stock Coverage (Days)';

COMMENT ON CONSTRAINT scm_consolidated_pr_line_consolidation_product_uniq ON public.scm_consolidated_pr_line
    IS 'unique(consolidation_id, product_id)';
-- Index: scm_consolidated_pr_line__consolidation_id_index

-- DROP INDEX IF EXISTS public.scm_consolidated_pr_line__consolidation_id_index;

CREATE INDEX IF NOT EXISTS scm_consolidated_pr_line__consolidation_id_index
    ON public.scm_consolidated_pr_line USING btree
    (consolidation_id ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.scm_pr_consolidation_request_rel

-- DROP TABLE IF EXISTS public.scm_pr_consolidation_request_rel;

CREATE TABLE IF NOT EXISTS public.scm_pr_consolidation_request_rel
(
    consolidation_id integer NOT NULL,
    request_id integer NOT NULL,
    CONSTRAINT scm_pr_consolidation_request_rel_pkey PRIMARY KEY (consolidation_id, request_id),
    CONSTRAINT scm_pr_consolidation_request_rel_consolidation_id_fkey FOREIGN KEY (consolidation_id)
        REFERENCES public.scm_pr_consolidation_session (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT scm_pr_consolidation_request_rel_request_id_fkey FOREIGN KEY (request_id)
        REFERENCES public.purchase_request (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_pr_consolidation_request_rel
    OWNER to odoo;

COMMENT ON TABLE public.scm_pr_consolidation_request_rel
    IS 'RELATION BETWEEN scm_pr_consolidation_session AND purchase_request';
-- Index: scm_pr_consolidation_request_re_request_id_consolidation_id_idx

-- DROP INDEX IF EXISTS public.scm_pr_consolidation_request_re_request_id_consolidation_id_idx;

CREATE INDEX IF NOT EXISTS scm_pr_consolidation_request_re_request_id_consolidation_id_idx
    ON public.scm_pr_consolidation_request_rel USING btree
    (request_id ASC NULLS LAST, consolidation_id ASC NULLS LAST)
    TABLESPACE pg_default;

-- Table: public.scm_create_consolidation_wizard

-- DROP TABLE IF EXISTS public.scm_create_consolidation_wizard;

CREATE TABLE IF NOT EXISTS public.scm_create_consolidation_wizard
(
    id integer NOT NULL DEFAULT nextval('scm_create_consolidation_wizard_id_seq'::regclass),
    user_id integer,
    company_id integer,
    create_uid integer,
    write_uid integer,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    date_from date NOT NULL,
    date_to date NOT NULL,
    notes text COLLATE pg_catalog."default",
    auto_start boolean,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    CONSTRAINT scm_create_consolidation_wizard_pkey PRIMARY KEY (id),
    CONSTRAINT scm_create_consolidation_wizard_company_id_fkey FOREIGN KEY (company_id)
        REFERENCES public.res_company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_create_consolidation_wizard_create_uid_fkey FOREIGN KEY (create_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_create_consolidation_wizard_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_create_consolidation_wizard_write_uid_fkey FOREIGN KEY (write_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_create_consolidation_wizard
    OWNER to odoo;

COMMENT ON TABLE public.scm_create_consolidation_wizard
    IS 'Create Consolidation Session Wizard';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.user_id
    IS 'Responsible';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.company_id
    IS 'Company';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.create_uid
    IS 'Created by';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.write_uid
    IS 'Last Updated by';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.name
    IS 'Session Name';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.date_from
    IS 'Start Date';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.date_to
    IS 'End Date';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.notes
    IS 'Notes';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.auto_start
    IS 'Auto Start Consolidation';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.create_date
    IS 'Created on';

COMMENT ON COLUMN public.scm_create_consolidation_wizard.write_date
    IS 'Last Updated on';

-- Table: public.scm_inventory_rule

-- DROP TABLE IF EXISTS public.scm_inventory_rule;

CREATE TABLE IF NOT EXISTS public.scm_inventory_rule
(
    id integer NOT NULL DEFAULT nextval('scm_inventory_rule_id_seq'::regclass),
    company_id integer NOT NULL,
    product_id integer,
    product_category_id integer,
    lead_time integer,
    warehouse_id integer,
    create_uid integer,
    write_uid integer,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    priority character varying COLLATE pg_catalog."default",
    active boolean,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    safety_stock_qty double precision,
    min_stock_qty double precision,
    reorder_point double precision,
    max_stock_qty double precision,
    avg_daily_usage double precision,
    CONSTRAINT scm_inventory_rule_pkey PRIMARY KEY (id),
    CONSTRAINT scm_inventory_rule_company_id_fkey FOREIGN KEY (company_id)
        REFERENCES public.res_company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_inventory_rule_create_uid_fkey FOREIGN KEY (create_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_inventory_rule_product_category_id_fkey FOREIGN KEY (product_category_id)
        REFERENCES public.product_category (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_inventory_rule_product_id_fkey FOREIGN KEY (product_id)
        REFERENCES public.product_product (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_inventory_rule_warehouse_id_fkey FOREIGN KEY (warehouse_id)
        REFERENCES public.stock_warehouse (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_inventory_rule_write_uid_fkey FOREIGN KEY (write_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_inventory_rule
    OWNER to odoo;

COMMENT ON TABLE public.scm_inventory_rule
    IS 'Safety Stock Rules';

COMMENT ON COLUMN public.scm_inventory_rule.company_id
    IS 'Company';

COMMENT ON COLUMN public.scm_inventory_rule.product_id
    IS 'Product';

COMMENT ON COLUMN public.scm_inventory_rule.product_category_id
    IS 'Product Category';

COMMENT ON COLUMN public.scm_inventory_rule.lead_time
    IS 'Lead Time (Days)';

COMMENT ON COLUMN public.scm_inventory_rule.warehouse_id
    IS 'Warehouse';

COMMENT ON COLUMN public.scm_inventory_rule.create_uid
    IS 'Created by';

COMMENT ON COLUMN public.scm_inventory_rule.write_uid
    IS 'Last Updated by';

COMMENT ON COLUMN public.scm_inventory_rule.name
    IS 'Rule Name';

COMMENT ON COLUMN public.scm_inventory_rule.priority
    IS 'Priority';

COMMENT ON COLUMN public.scm_inventory_rule.active
    IS 'Active';

COMMENT ON COLUMN public.scm_inventory_rule.create_date
    IS 'Created on';

COMMENT ON COLUMN public.scm_inventory_rule.write_date
    IS 'Last Updated on';

COMMENT ON COLUMN public.scm_inventory_rule.safety_stock_qty
    IS 'Safety Stock Quantity';

COMMENT ON COLUMN public.scm_inventory_rule.min_stock_qty
    IS 'Minimum Stock Quantity';

COMMENT ON COLUMN public.scm_inventory_rule.reorder_point
    IS 'Reorder Point';

COMMENT ON COLUMN public.scm_inventory_rule.max_stock_qty
    IS 'Maximum Stock Quantity';

COMMENT ON COLUMN public.scm_inventory_rule.avg_daily_usage
    IS 'Average Daily Usage';

-- Table: public.scm_forecast

-- DROP TABLE IF EXISTS public.scm_forecast;

CREATE TABLE IF NOT EXISTS public.scm_forecast
(
    id integer NOT NULL DEFAULT nextval('scm_forecast_id_seq'::regclass),
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    warehouse_id integer NOT NULL,
    create_uid integer,
    write_uid integer,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    forecast_period character varying COLLATE pg_catalog."default",
    state character varying COLLATE pg_catalog."default",
    date date NOT NULL,
    notes text COLLATE pg_catalog."default",
    is_template boolean,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    forecast_qty double precision NOT NULL,
    actual_qty double precision,
    variance double precision,
    variance_percent double precision,
    CONSTRAINT scm_forecast_pkey PRIMARY KEY (id),
    CONSTRAINT scm_forecast_company_id_fkey FOREIGN KEY (company_id)
        REFERENCES public.res_company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_forecast_create_uid_fkey FOREIGN KEY (create_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_forecast_product_id_fkey FOREIGN KEY (product_id)
        REFERENCES public.product_product (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_forecast_warehouse_id_fkey FOREIGN KEY (warehouse_id)
        REFERENCES public.stock_warehouse (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_forecast_write_uid_fkey FOREIGN KEY (write_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_forecast
    OWNER to odoo;

COMMENT ON TABLE public.scm_forecast
    IS 'Inventory Forecast';

COMMENT ON COLUMN public.scm_forecast.company_id
    IS 'Company';

COMMENT ON COLUMN public.scm_forecast.product_id
    IS 'Product';

COMMENT ON COLUMN public.scm_forecast.warehouse_id
    IS 'Warehouse';

COMMENT ON COLUMN public.scm_forecast.create_uid
    IS 'Created by';

COMMENT ON COLUMN public.scm_forecast.write_uid
    IS 'Last Updated by';

COMMENT ON COLUMN public.scm_forecast.name
    IS 'Reference';

COMMENT ON COLUMN public.scm_forecast.forecast_period
    IS 'Forecast Period';

COMMENT ON COLUMN public.scm_forecast.state
    IS 'Status';

COMMENT ON COLUMN public.scm_forecast.date
    IS 'Forecast Date';

COMMENT ON COLUMN public.scm_forecast.notes
    IS 'Notes';

COMMENT ON COLUMN public.scm_forecast.is_template
    IS 'Is Template';

COMMENT ON COLUMN public.scm_forecast.create_date
    IS 'Created on';

COMMENT ON COLUMN public.scm_forecast.write_date
    IS 'Last Updated on';

COMMENT ON COLUMN public.scm_forecast.forecast_qty
    IS 'Forecasted Quantity';

COMMENT ON COLUMN public.scm_forecast.actual_qty
    IS 'Actual Quantity';

COMMENT ON COLUMN public.scm_forecast.variance
    IS 'Variance';

COMMENT ON COLUMN public.scm_forecast.variance_percent
    IS 'Variance %';

-- Table: public.scm_forecast_line

-- DROP TABLE IF EXISTS public.scm_forecast_line;

CREATE TABLE IF NOT EXISTS public.scm_forecast_line
(
    id integer NOT NULL DEFAULT nextval('scm_forecast_line_id_seq'::regclass),
    forecast_id integer NOT NULL,
    product_id integer NOT NULL,
    warehouse_id integer NOT NULL,
    create_uid integer,
    write_uid integer,
    state character varying COLLATE pg_catalog."default",
    date date NOT NULL,
    notes text COLLATE pg_catalog."default",
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    forecast_qty double precision NOT NULL,
    actual_qty double precision,
    expected_inventory double precision,
    CONSTRAINT scm_forecast_line_pkey PRIMARY KEY (id),
    CONSTRAINT scm_forecast_line_create_uid_fkey FOREIGN KEY (create_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL,
    CONSTRAINT scm_forecast_line_forecast_id_fkey FOREIGN KEY (forecast_id)
        REFERENCES public.scm_forecast (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT scm_forecast_line_product_id_fkey FOREIGN KEY (product_id)
        REFERENCES public.product_product (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_forecast_line_warehouse_id_fkey FOREIGN KEY (warehouse_id)
        REFERENCES public.stock_warehouse (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE RESTRICT,
    CONSTRAINT scm_forecast_line_write_uid_fkey FOREIGN KEY (write_uid)
        REFERENCES public.res_users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.scm_forecast_line
    OWNER to odoo;

COMMENT ON TABLE public.scm_forecast_line
    IS 'Inventory Forecast Line';

COMMENT ON COLUMN public.scm_forecast_line.forecast_id
    IS 'Forecast';

COMMENT ON COLUMN public.scm_forecast_line.product_id
    IS 'Product';

COMMENT ON COLUMN public.scm_forecast_line.warehouse_id
    IS 'Warehouse';

COMMENT ON COLUMN public.scm_forecast_line.create_uid
    IS 'Created by';

COMMENT ON COLUMN public.scm_forecast_line.write_uid
    IS 'Last Updated by';

COMMENT ON COLUMN public.scm_forecast_line.state
    IS 'Status';

COMMENT ON COLUMN public.scm_forecast_line.date
    IS 'Forecast Date';

COMMENT ON COLUMN public.scm_forecast_line.notes
    IS 'Notes';

COMMENT ON COLUMN public.scm_forecast_line.create_date
    IS 'Created on';

COMMENT ON COLUMN public.scm_forecast_line.write_date
    IS 'Last Updated on';

COMMENT ON COLUMN public.scm_forecast_line.forecast_qty
    IS 'Forecasted Quantity';

COMMENT ON COLUMN public.scm_forecast_line.actual_qty
    IS 'Actual Quantity';

COMMENT ON COLUMN public.scm_forecast_line.expected_inventory
    IS 'Expected Inventory';

-- Table: public._unknown_scm_create_consolidation_wizard_rel

-- DROP TABLE IF EXISTS public._unknown_scm_create_consolidation_wizard_rel;

CREATE TABLE IF NOT EXISTS public._unknown_scm_create_consolidation_wizard_rel
(
    scm_create_consolidation_wizard_id integer NOT NULL,
    _unknown_id integer NOT NULL,
    CONSTRAINT _unknown_scm_create_consolidation_wizard_rel_pkey PRIMARY KEY (scm_create_consolidation_wizard_id, _unknown_id),
    CONSTRAINT _unknown_scm_create_consolida_scm_create_consolidation_wiz_fkey FOREIGN KEY (scm_create_consolidation_wizard_id)
        REFERENCES public.scm_create_consolidation_wizard (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public._unknown_scm_create_consolidation_wizard_rel
    OWNER to odoo;

COMMENT ON TABLE public._unknown_scm_create_consolidation_wizard_rel
    IS 'RELATION BETWEEN scm_create_consolidation_wizard AND _unknown';
-- Index: _unknown_scm_create_consolida__unknown_id_scm_create_consol_idx

-- DROP INDEX IF EXISTS public._unknown_scm_create_consolida__unknown_id_scm_create_consol_idx;

CREATE INDEX IF NOT EXISTS _unknown_scm_create_consolida__unknown_id_scm_create_consol_idx
    ON public._unknown_scm_create_consolidation_wizard_rel USING btree
    (_unknown_id ASC NULLS LAST, scm_create_consolidation_wizard_id ASC NULLS LAST)
    TABLESPACE pg_default;

-- Table: public._unknown_scm_pr_consolidation_session_rel

-- DROP TABLE IF EXISTS public._unknown_scm_pr_consolidation_session_rel;

CREATE TABLE IF NOT EXISTS public._unknown_scm_pr_consolidation_session_rel
(
    scm_pr_consolidation_session_id integer NOT NULL,
    _unknown_id integer NOT NULL,
    CONSTRAINT _unknown_scm_pr_consolidation_session_rel_pkey PRIMARY KEY (scm_pr_consolidation_session_id, _unknown_id),
    CONSTRAINT _unknown_scm_pr_consolidation_scm_pr_consolidation_session_fkey FOREIGN KEY (scm_pr_consolidation_session_id)
        REFERENCES public.scm_pr_consolidation_session (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public._unknown_scm_pr_consolidation_session_rel
    OWNER to odoo;

COMMENT ON TABLE public._unknown_scm_pr_consolidation_session_rel
    IS 'RELATION BETWEEN scm_pr_consolidation_session AND _unknown';
-- Index: _unknown_scm_pr_consolidation__unknown_id_scm_pr_consolidat_idx

-- DROP INDEX IF EXISTS public._unknown_scm_pr_consolidation__unknown_id_scm_pr_consolidat_idx;

CREATE INDEX IF NOT EXISTS _unknown_scm_pr_consolidation__unknown_id_scm_pr_consolidat_idx
    ON public._unknown_scm_pr_consolidation_session_rel USING btree
    (_unknown_id ASC NULLS LAST, scm_pr_consolidation_session_id ASC NULLS LAST)
    TABLESPACE pg_default;