# Satyam Tex Fabb CRM

A complete business management CRM for Satyam Tex Fabb — a 30-year-old textile machinery parts dealer in Bhilwara, Rajasthan. Built to replace Tally + WhatsApp chaos with a single, organised system.

## What it does

| Module | Description |
|--------|-------------|
| 📦 Stock Manager | Category → Part → Supplier hierarchy, price history tracking, part image upload |
| 💰 Sales | Record sales with invoice, stock auto-reduces, party from existing customers |
| 📥 Purchases | Record purchases, stock auto-increases, new parts auto-added to inventory |
| ↩️ Returns | Sale and purchase returns with document upload |
| 💳 Payments | Payment tracking with customer dropdown, overdue highlighting, receipt upload |
| 🛒 Purchase Orders | Create POs with supplier dropdown, send via Email or WhatsApp |
| 👥 Customers & Leads | CRM contacts, lead status, follow-up dates, auto-added from supplier entries |
| 📧 Promotional Emails | Bulk email + WhatsApp campaigns with 7 templates, audience filtering |
| 💬 Payment Reminders | Automated email + WhatsApp payment reminders |
| 📊 Analytics | Monthly revenue bars, top products, top customers, customer × product matrix, communication channel analysis |
| 📅 Calendar | Payment due dates and follow-up dates in one view |
| 🔐 Login | Role-based access (Admin / Employee), SHA-256 password hashing |
| 👤 User Management | Add/remove employees, reset passwords |
| 📤 Data Export/Import | Excel + CSV export, bulk import with progress bar, Tally-compatible |
| 🖼️ Part Images | Upload per-part images, stored in Supabase + organised Google Drive catalogue by category |

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | Python 3.11 |
| Database | Supabase (PostgreSQL) |
| Auth | SHA-256 hashing (role-based) |
| Email | Gmail API (OAuth2) |
| WhatsApp | Click-to-chat links |
| Image Storage | Supabase text column (base64) + Google Drive catalogue |
| OCR | pytesseract + pdfplumber with image preprocessing |
| Export | openpyxl + xlsxwriter |
| Deployment | Streamlit Community Cloud |

## Setup

```bash
git clone https://github.com/challanamuskan/shree-tex-fabb-crm
cd shree-tex-fabb-crm
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "your-project-url"
SUPABASE_KEY = "your-service-role-key"
admin_email  = "your-gmail-address"
```

Run the schema in Supabase SQL Editor: paste contents of `supabase_schema.sql`

```bash
streamlit run app.py
```

## Live

🔗 **https://satyam-tex-fabb.streamlit.app**

## Context

Small textile machinery parts businesses in Rajasthan traditionally run on Tally + WhatsApp — no central system for stock, customers, payments, or staff. Data is fragmented, follow-ups are missed, and there is no way to track business health in real time.

This CRM solves that for a 2,000+ part inventory with multiple suppliers, field staff, and customers spread across Rajasthan.

## Built by

**Muskan Challana** — AI builder & freelance CRM developer, Jaipur
[muskanchallana.vercel.app](https://muskanchallana.vercel.app)
