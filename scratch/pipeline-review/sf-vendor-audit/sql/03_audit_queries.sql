/*
SF Vendor Payments - Audit SQL Queries (PostgreSQL)
Run after importing vendor_payments_fy2020.csv into the vendor_payments table.
*/


-- Data profiling: top vendors by total spend
SELECT
    vendor,
    COUNT(DISTINCT purchase_order)  AS po_count,
    COUNT(*)                        AS line_items,
    ROUND(SUM(vouchers_paid), 2)    AS total_paid,
    ROUND(AVG(vouchers_paid), 2)    AS avg_payment,
    ROUND(MAX(vouchers_paid), 2)    AS max_payment
FROM vendor_payments
WHERE vouchers_paid > 0
GROUP BY vendor
ORDER BY total_paid DESC
LIMIT 20;


-- TEST 1: Vendor concentration
-- What % of total city spend do the top vendors capture?
WITH vendor_totals AS (
    SELECT
        vendor,
        SUM(vouchers_paid) AS vendor_total,
        (SELECT SUM(vouchers_paid) FROM vendor_payments WHERE vouchers_paid > 0) AS city_total
    FROM vendor_payments
    WHERE vouchers_paid > 0
    GROUP BY vendor
)
SELECT
    vendor,
    ROUND(vendor_total, 2) AS total_paid,
    ROUND(vendor_total / city_total * 100, 2) AS pct_of_city_spend
FROM vendor_totals
WHERE vendor_total / city_total > 0.01
ORDER BY vendor_total DESC;


-- TEST 2: Duplicate payments
-- Same vendor + same exact amount across different purchase orders
SELECT DISTINCT
    a.vendor,
    a.vouchers_paid AS amount,
    a.purchase_order AS po_1,
    b.purchase_order AS po_2,
    a.department_code AS dept_1,
    b.department_code AS dept_2
FROM vendor_payments a
JOIN vendor_payments b
    ON a.vendor = b.vendor
    AND a.vouchers_paid = b.vouchers_paid
    AND a.purchase_order < b.purchase_order
WHERE a.vouchers_paid > 500
ORDER BY a.vouchers_paid DESC
LIMIT 50;


-- TEST 3: Round number analysis
-- MOD() replaces SQLite's % operator
SELECT
    vendor,
    purchase_order,
    vouchers_paid,
    department_code,
    character_code
FROM vendor_payments
WHERE vouchers_paid >= 10000
  AND MOD(CAST(vouchers_paid AS INTEGER), 1000) = 0
ORDER BY vouchers_paid DESC;


-- TEST 4: Single-source department risk
WITH dept_vendor AS (
    SELECT
        department_code,
        vendor,
        SUM(vouchers_paid) AS vendor_dept_total
    FROM vendor_payments
    WHERE vouchers_paid > 0
    GROUP BY department_code, vendor
),
dept_total AS (
    SELECT
        department_code,
        SUM(vouchers_paid) AS dept_total
    FROM vendor_payments
    WHERE vouchers_paid > 0
    GROUP BY department_code
)
SELECT
    dv.department_code,
    dv.vendor,
    ROUND(dv.vendor_dept_total, 2) AS vendor_spend,
    ROUND(dt.dept_total, 2) AS dept_total_spend,
    ROUND(dv.vendor_dept_total / dt.dept_total * 100, 1) AS pct_of_dept
FROM dept_vendor dv
JOIN dept_total dt ON dv.department_code = dt.department_code
WHERE dv.vendor_dept_total / dt.dept_total > 0.50
  AND dv.vendor_dept_total > 100000
ORDER BY dv.vendor_dept_total DESC;


-- TEST 5: Negative payments / credits
SELECT
    vendor,
    purchase_order,
    vouchers_paid,
    department_code,
    character_code
FROM vendor_payments
WHERE vouchers_paid < -10000
ORDER BY vouchers_paid ASC;


-- TEST 6: Statistical outliers (>$16.6K based on 3x IQR)
SELECT
    vendor,
    purchase_order,
    vouchers_paid,
    department_code,
    organization_group
FROM vendor_payments
WHERE vouchers_paid > 16608
ORDER BY vouchers_paid DESC
LIMIT 100;


-- TEST 7: Stale encumbrances
-- PostgreSQL cannot reference aliases in HAVING, so we use a subquery
SELECT *
FROM (
    SELECT
        purchase_order,
        vendor,
        ROUND(SUM(vouchers_paid), 2)        AS total_paid,
        ROUND(SUM(encumbrance_balance), 2)   AS encumbrance_remaining,
        CASE
            WHEN SUM(vouchers_paid) + SUM(vouchers_pending) + SUM(encumbrance_balance) > 0
            THEN ROUND(SUM(vouchers_paid) / (SUM(vouchers_paid) + SUM(vouchers_pending) + SUM(encumbrance_balance)) * 100, 1)
            ELSE 0
        END AS utilization_pct
    FROM vendor_payments
    GROUP BY purchase_order, vendor
) sub
WHERE encumbrance_remaining > 100000
  AND utilization_pct < 20
ORDER BY encumbrance_remaining DESC;


-- TEST 8: Department spend overview
SELECT
    department_code,
    COUNT(DISTINCT vendor)           AS vendor_count,
    COUNT(DISTINCT purchase_order)   AS po_count,
    ROUND(SUM(vouchers_paid), 2)     AS total_paid,
    ROUND(AVG(vouchers_paid), 2)     AS avg_payment,
    ROUND(SUM(encumbrance_balance), 2) AS total_encumbered
FROM vendor_payments
GROUP BY department_code
ORDER BY total_paid DESC;
