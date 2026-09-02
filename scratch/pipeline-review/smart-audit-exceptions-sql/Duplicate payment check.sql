
Select vendor_id, amount, invoice_number ,
Count (*) as occurence_count
from transactions

Group By 
Vendor_id, amount, Invoice_number

Having Count(*) > 1;
