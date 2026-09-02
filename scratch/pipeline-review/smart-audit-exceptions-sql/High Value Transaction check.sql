SELECT  invoice_number, amount, status, transaction_id
From transactions

Where 
Amount > 50000.0

Order by 
Amount desc