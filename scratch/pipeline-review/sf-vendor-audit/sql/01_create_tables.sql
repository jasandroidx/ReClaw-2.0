/*
SF Vendor Payments - Table Creation (PostgreSQL)
Run this first, then import vendor_payments_fy2020.csv via pgAdmin Import/Export.
*/

DROP TABLE IF EXISTS vendor_payments;

CREATE TABLE vendor_payments (
    fiscal_year             INTEGER,
    purchase_order          TEXT,
    vendor                  TEXT,
    related_govt_units      TEXT,
    organization_group_code INTEGER,
    organization_group      TEXT,
    department_code         TEXT,
    department              TEXT,
    program_code            TEXT,
    program                 TEXT,
    character_code          TEXT,
    character               TEXT,
    object_code             TEXT,
    object                  TEXT,
    sub_object_code         TEXT,
    sub_object              TEXT,
    fund_type_code          TEXT,
    fund_type               TEXT,
    fund_code               TEXT,
    fund                    TEXT,
    fund_category_code      NUMERIC,
    fund_category           TEXT,
    vouchers_paid           NUMERIC,
    vouchers_pending        NUMERIC,
    vouchers_pending_retainage NUMERIC,
    encumbrance_balance     NUMERIC
);

-- Indexes for audit query performance
CREATE INDEX idx_vendor_paid ON vendor_payments (vendor, vouchers_paid);
CREATE INDEX idx_purchase_order ON vendor_payments (purchase_order);
CREATE INDEX idx_dept ON vendor_payments (department_code);
CREATE INDEX idx_vouchers_paid ON vendor_payments (vouchers_paid);
