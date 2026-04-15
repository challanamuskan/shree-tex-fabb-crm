# Satyam Tex Fabb CRM

A complete business management CRM for Satyam Tex Fabb — a 30-year-old textile machinery parts dealer in Bhilwara, Rajasthan.

## What it does

- 📦 Stock Manager — category → part → supplier hierarchy, price history, part images
- 💰 Sales — record sales, stock auto-reduces, party name from existing customers
- 📥 Purchases — record purchases, stock auto-increases, new parts auto-added
- ↩️ Returns — sale and purchase returns
- 💳 Payments — payment tracking with customer dropdown, overdue alerts
- 📧 Promotional Emails — bulk email + WhatsApp campaigns to customer segments
- 💬 Payment Reminders — automated email + WhatsApp reminders
- 🛒 Purchase Orders — create POs with supplier dropdown, send via email or WhatsApp
- 👥 Customers & Leads — CRM contacts, lead status tracking, auto-added from supplier entries
- 📊 Analytics — monthly revenue, top products, customer × product matrix, communication analysis
- 📅 Calendar — payment due dates and follow-up dates
- 📤 Data Export/Import — Excel, CSV export; bulk import with progress bar
- 🔐 Login — role-based access (Admin/Employee), password management
- 👤 User Management — add/remove employees, reset passwords
- 🖼️ Part Images — upload images per part, stored in Supabase + Google Drive catalogue

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | Python 3.11 |
| Database | Supabase (PostgreSQL) |
| Auth | SHA-256 hashing |
| Email | Gmail API (OAuth2) |
| WhatsApp | Click-to-chat links |
| Image Storage | Supabase (base64) + Google Drive catalogue |
| OCR | pytesseract + pdfplumber (with preprocessing) |
| Export | openpyxl + xlsxwriter |
| Deployment | Streamlit Community Cloud |

## Setup

1. Clone the repo
2. `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-service-role-key"
admin_email = "your-gmail"
```
4. Run the Supabase schema: paste `supabase_schema.sql` into Supabase SQL editor
5. `streamlit run app.py`

## Live

🔗 https://satyam-tex-fabb.streamlit.app

## Built by

Muskan Challana — AI builder, freelance CRM developer, Jaipur
