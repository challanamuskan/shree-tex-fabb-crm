PARTS_TAB = "Stock Manager"
CONTACTS_TAB = "Customers & Leads"
PAYMENTS_TAB = "Payments"
PURCHASE_ORDERS_TAB = "Purchase Orders"
SALES_RECORDS_TAB = "Sales_Records"
PURCHASE_RECORDS_TAB = "Purchase_Records"
RETURNS_TAB = "Returns"
EMAIL_LOG_TAB = "Email Log"
EMPLOYEES_TAB = "Employees"
EMPLOYEE_TASKS_TAB = "Employee_Tasks"
DAILY_REPORTS_TAB = "Daily_Reports"
ATTENDANCE_TAB = "Attendance"

PARTS_HEADERS = [
    "Part Number",
    "Part Name",
    "Category",
    "Quantity",
    "Reorder Level",
    "Unit Price",
    "Supplier Name",
    "Purchase Date",
]

SALES_RECORDS_HEADERS = [
    "Date",
    "Part Name",
    "Quantity Sold",
    "Sale Invoice Number",
    "Party Name",
    "Sale Price Per Unit",
    "Total Sale Value",
]

PURCHASE_RECORDS_HEADERS = [
    "Date",
    "Part Name",
    "Quantity Purchased",
    "Purchase Invoice Number",
    "Supplier Name",
    "Purchase Price Per Unit",
    "Total Purchase Value",
]

RETURNS_HEADERS = [
    "Date",
    "Type",
    "Part Name",
    "Quantity",
    "Invoice Number",
    "Party/Supplier Name",
    "Reason",
]

CONTACTS_HEADERS = [
    "Name",
    "Business Name",
    "Phone",
    "Email",
    "Machine Type",
    "Lead Status",
    "Follow-up Date",
    "Notes",
]

PAYMENTS_HEADERS = [
    "Customer Name",
    "Invoice Number",
    "Amount",
    "Due Date",
    "Status",
]

PURCHASE_ORDERS_HEADERS = [
    "Supplier",
    "Invoice Number",
    "Part Name",
    "Quantity Ordered",
    "Unit Price",
    "Line Total",
    "Total Order Value",
    "Order Date",
    "Expected Delivery",
    "Status",
]

EMAIL_LOG_HEADERS = [
    "Timestamp",
    "Email Type",
    "Recipient Name",
    "Recipient Email",
    "Subject",
    "Status",
    "Error",
]

EMPLOYEES_HEADERS = [
    "Name",
    "Role",
    "Phone",
    "WhatsApp",
    "Date Added",
]

EMPLOYEE_TASKS_HEADERS = [
    "Date",
    "Employee Name",
    "Task",
    "Target",
    "Status",
    "Report Submitted",
]

DAILY_REPORTS_HEADERS = [
    "Date",
    "Employee Name",
    "Tasks Completed",
    "Orders Dispatched",
    "Payments Collected",
    "Expenses Incurred",
    "Issues/Remarks",
]

ATTENDANCE_HEADERS = [
    "Date",
    "Employee Name",
    "Time In",
    "Time Out",
    "Total Hours",
    "Status",
]
