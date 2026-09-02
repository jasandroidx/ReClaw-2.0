SELECT transaction_date, transaction_id from transactions
Where  strftime ('%w', transaction_date) in ('0', '6')