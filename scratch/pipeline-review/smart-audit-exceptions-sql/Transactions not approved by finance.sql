Select  
transactions.transaction_id, transactions.amount, transactions.approved_by, employees.department

From transactions
INNER JOIN employees

On 
transactions.approved_by = employees.employee_id

Where department <> 'Finance'