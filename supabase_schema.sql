-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS parts (
    id SERIAL PRIMARY KEY,
    cid TEXT,
    category TEXT,
    part_name TEXT,
    unit_sale_price TEXT,
    quantity TEXT,
    status TEXT,
    date_added TEXT,
    legacy_id TEXT,
    price_type TEXT,
    box_number TEXT,
    supplier_name TEXT,
    part_number TEXT,
    supplier_phone TEXT,
    supplier_email TEXT,
    reorder_level TEXT,
    unit_purchase_price TEXT,
    purchase_date TEXT,
    product_image TEXT,
    part_documents TEXT,
    image TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    category_name TEXT UNIQUE,
    description TEXT,
    created_date TEXT
);

CREATE TABLE IF NOT EXISTS sales_records (
    id SERIAL PRIMARY KEY,
    date TEXT,
    part_name TEXT,
    category TEXT,
    supplier TEXT,
    quantity_sold TEXT,
    sale_invoice_number TEXT,
    party_name TEXT,
    sale_price_per_unit TEXT,
    total_sale_value TEXT,
    sale_bill_images TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_records (
    id SERIAL PRIMARY KEY,
    date TEXT,
    part_name TEXT,
    category TEXT,
    supplier_name TEXT,
    quantity_purchased TEXT,
    purchase_invoice_number TEXT,
    purchase_price_per_unit TEXT,
    total_purchase_value TEXT,
    purchase_bill_images TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT,
    business_name TEXT,
    phone TEXT,
    email TEXT,
    machine_type TEXT,
    lead_status TEXT,
    follow_up_date TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    customer_name TEXT,
    invoice_number TEXT,
    amount TEXT,
    due_date TEXT,
    status TEXT,
    receipt_document TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier TEXT,
    invoice_number TEXT,
    part_name TEXT,
    quantity_ordered TEXT,
    unit_price TEXT,
    line_total TEXT,
    total_order_value TEXT,
    order_date TEXT,
    expected_delivery TEXT,
    status TEXT,
    invoice_document TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    date TEXT,
    part_name TEXT,
    supplier_name TEXT,
    old_price TEXT,
    new_price TEXT,
    updated_by TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name TEXT,
    role TEXT,
    phone TEXT,
    whatsapp TEXT,
    date_added TEXT
);

CREATE TABLE IF NOT EXISTS employee_tasks (
    id SERIAL PRIMARY KEY,
    date TEXT,
    employee_name TEXT,
    task TEXT,
    target TEXT,
    status TEXT,
    report_submitted TEXT
);

CREATE TABLE IF NOT EXISTS email_log (
    id SERIAL PRIMARY KEY,
    timestamp TEXT,
    email_type TEXT,
    recipient_name TEXT,
    recipient_email TEXT,
    subject TEXT,
    status TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    role TEXT,
    full_name TEXT,
    email TEXT,
    must_change_password TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS returns (
    id SERIAL PRIMARY KEY,
    date TEXT,
    type TEXT,
    part_name TEXT,
    category TEXT,
    supplier_name TEXT,
    quantity TEXT,
    invoice_number TEXT,
    party_supplier_name TEXT,
    reason TEXT,
    return_documents TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id SERIAL PRIMARY KEY,
    date TEXT,
    employee_name TEXT,
    tasks_completed TEXT,
    orders_dispatched TEXT,
    payments_collected TEXT,
    expenses_incurred TEXT,
    issues_remarks TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    date TEXT,
    employee_name TEXT,
    time_in TEXT,
    time_out TEXT,
    total_hours TEXT,
    status TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE,
    value TEXT,
    updated_at TEXT
);

-- Enable Row Level Security (basic protection)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_records ENABLE ROW LEVEL SECURITY;

-- Allow anon read/write for app (we handle auth in Streamlit)
CREATE POLICY "Allow all for anon" ON parts FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON categories FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON sales_records FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON purchase_records FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON customers FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON payments FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON purchase_orders FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON price_history FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON employees FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON employee_tasks FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON email_log FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON users FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON returns FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON daily_reports FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON attendance FOR ALL USING (true);
CREATE POLICY "Allow all for anon" ON settings FOR ALL USING (true);
