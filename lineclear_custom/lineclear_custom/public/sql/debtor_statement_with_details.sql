WITH invoices_and_debits AS (
	-- Get statement without the payment details
	SELECT
		COALESCE(against_voucher, voucher_no) AS reference_name,
		posting_date AS reference_date,
		posting_date AS date,
		voucher_subtype AS source,
		voucher_no AS name,
		'' AS description,
		SUM(debit) AS debit,
		SUM(credit) AS credit
	FROM `tabGL Entry`
	WHERE posting_date BETWEEN %s AND %s
		AND is_cancelled = 0
		AND party = %s
		AND (
	        voucher_type = 'Sales Invoice'
	        OR
	        (voucher_type = 'Journal Entry' AND voucher_subtype = 'Debit Note')
	    )
	GROUP BY posting_date, voucher_type, voucher_no, remarks, against_voucher
),
payments_and_credits AS (
	-- Get payment/credit statement via Sales Invoice & Journal Entry
	SELECT
		against_voucher AS reference_name,
		NULL AS reference_date,
		posting_date AS date,
		voucher_subtype AS source,
		voucher_no AS name,
		'' AS description,
		SUM(debit) AS debit,
		SUM(credit) AS credit
	FROM `tabGL Entry`
	WHERE against_voucher IN (SELECT reference_name FROM invoices_and_debits)
		AND (
			(voucher_type IN ('Payment Entry'))
			OR
			(voucher_type = 'Journal Entry' AND voucher_subtype = 'Credit Note')
		)
		AND posting_date <= %s
		AND is_cancelled = 0
	GROUP BY posting_date, voucher_type, voucher_no, remarks, against_voucher
),
debtor_statements AS (
	SELECT * FROM invoices_and_debits
	UNION ALL
	SELECT * FROM payments_and_credits
),
reference_dates AS (
    SELECT
        reference_name,
        COALESCE(
            DS.reference_date,
            MAX(DS.reference_date) OVER (
                PARTITION BY DS.reference_name
                ORDER BY DS.date
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            )
        ) AS reference_date,
        DS.date,
        DS.source,
        DS.name,
        DS.description,
        DS.debit,
        DS.credit
    FROM debtor_statements AS DS
),
row_indexes AS (
	SELECT
        reference_name,
        reference_date,
        ROW_NUMBER() OVER (
            PARTITION BY reference_name
            ORDER BY reference_name, reference_date
        ) AS row_index,
        date,
        source,
        name,
        description,
        debit,
        credit
    FROM reference_dates
),
calculate_balance AS (
    SELECT
    	reference_date,
        reference_name,
        row_index,
        DATE_FORMAT(date, '%%d/%%m/%%Y') AS date,
        CASE
            WHEN source = 'Sales Invoice' THEN 'IN'
            WHEN source = 'Receive' THEN 'OR'
            WHEN source = 'Debit Note' THEN 'DN'
            WHEN source = 'Credit Note' THEN 'CN'
            ELSE source
        END AS source,
        name,
        description,
        debit,
        credit,
        SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) OVER (
            ORDER BY reference_date, reference_name, row_index
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS balance
    FROM row_indexes
)
SELECT *
FROM calculate_balance
ORDER BY reference_date, reference_name, row_index;