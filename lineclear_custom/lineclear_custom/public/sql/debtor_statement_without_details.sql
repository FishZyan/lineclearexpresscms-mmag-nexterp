WITH invoices_and_debits AS (
	-- Get statement without the payment details
	SELECT
		COALESCE(against_voucher, voucher_no) AS reference_name,
		posting_date AS reference_date,
		posting_date AS date,
		voucher_subtype AS source,
		voucher_no AS name,
		remarks AS description,
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
		remarks AS description,
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
outstanding_balances AS (
	SELECT 
		reference_name,
		date,
		source,
		description,
		SUM(debit) AS total_debit,
		SUM(credit) AS total_credit,
		SUM(debit) - SUM(credit) AS oustanding
	FROM debtor_statements
	GROUP BY reference_name
	HAVING oustanding > 0
)
SELECT 
    date AS reference_date,
	reference_name AS name,
    CASE
        WHEN source = 'Sales Invoice' THEN 'IN'
        WHEN source = 'Receive' THEN 'OR'
        WHEN source = 'Debit Note' THEN 'DN'
        WHEN source = 'Credit Note' THEN 'CN'
        ELSE source
    END AS source,
    DATE_FORMAT(date, '%%d/%%m/%%Y') AS date,
    description,
    total_debit AS debit,
    total_credit AS credit,
	SUM(total_debit - total_credit) OVER (
        ORDER BY reference_date
    	ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS balance
FROM outstanding_balances;