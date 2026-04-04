PARTS_TAB = "Parts"
CATEGORIES_TAB = "Categories"
PRICE_HISTORY_TAB = "Price_History"
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
SETTINGS_TAB = "Settings"

PARTS_HEADERS = [
    "cid",
    "Category",
    "Part_Name",
    "Unit_Sale_Price",
    "Quantity",
    "status",
    "Date_Added",
    "Legacy_ID",
    "Price_Type",
    "Box_Number",
    "Supplier_Name",
    "image",
]

CATEGORIES_HEADERS = [
    "Category_Name",
    "Description",
    "Created_Date",
]

PRICE_HISTORY_HEADERS = [
    "Date",
    "Part_Name",
    "Supplier_Name",
    "Old_Price",
    "New_Price",
    "Updated_By",
]

SALES_RECORDS_HEADERS = [
    "Date",
    "Part_Name",
    "Category",
    "Supplier",
    "Quantity_Sold",
    "Sale_Invoice_Number",
    "Party_Name",
    "Sale_Price_Per_Unit",
    "Total_Sale_Value",
    "Sale_Bill_Images",
]

PURCHASE_RECORDS_HEADERS = [
    "Date",
    "Part_Name",
    "Category",
    "Supplier_Name",
    "Quantity_Purchased",
    "Purchase_Invoice_Number",
    "Purchase_Price_Per_Unit",
    "Total_Purchase_Value",
    "Purchase_Bill_Images",
]

RETURNS_HEADERS = [
    "Date",
    "Type",
    "Part_Name",
    "Category",
    "Supplier_Name",
    "Quantity",
    "Invoice_Number",
    "Party_Supplier_Name",
    "Reason",
    "Return_Documents",
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
    "Receipt_Document",
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
    "Invoice_Document",
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

SETTINGS_HEADERS = [
    "key",
    "value",
    "updated_at",
]
