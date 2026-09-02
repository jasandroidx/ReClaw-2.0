SELECT
transactions.invoice_number, transactions.vendor_id, transactions.transaction_date, vendors.risk_rating, vendors.vendor_name

From transactions
Inner Join vendors

On Transactions.vendor_id = vendors.vendor_id
Where vendors.risk_rating = ('High');
