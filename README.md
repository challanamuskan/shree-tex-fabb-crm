# Satyam Tex Fabb CRM

An internal CRM for Satyam Tex Fabb — a 30-year-old textile machinery parts dealer in Bhilwara, Rajasthan. Built to replace Tally + WhatsApp chaos with a single, organised system for stock, sales, customers, staff, and analytics.

**Live:** [satyam-tex-fabb.streamlit.app](https://satyam-tex-fabb.streamlit.app)
**Repo:** [challanamuskan/shree-tex-fabb-crm](https://github.com/challanamuskan/shree-tex-fabb-crm)

---

## Features

| Module | Description |
|--------|-------------|
| 📦 Stock Manager | Category → Part → Supplier hierarchy, price history, inline image upload |
| 🖼️ Part Images | Full image catalogue — browse all 49 categories, filter, view uploaded images |
| 💰 Sales | Record sales with invoice number, stock auto-decrements, party from customer list |
| 📥 Purchases | Record purchases, stock auto-increments, new parts auto-added to inventory |
| ↩️ Returns | Sale and purchase returns with document upload |
| 💳 Payments | Payment tracking with overdue highlighting, receipt upload |
| 🛒 Purchase Orders | Create POs with supplier dropdown, send via Email or WhatsApp |
| 👥 Customers & Leads | CRM contacts with lead status, follow-up dates, auto-added from supplier entries |
| 📧 Email Alerts | Low-stock email alerts, bulk promotional emails, payment reminders (7 templates) |
| 📊 MIS Analytics | Monthly revenue, top products, top customers, customer × product matrix |
| 📅 Calendar | Payment due dates and follow-up dates in a single view |
| 👤 Employee Management | Add/remove staff, role assignment, attendance tracking |
| 📋 Daily Reports | Per-employee daily activity logs |
| 🔐 User Management | Role-based access (Admin / Employee), SHA-256 password hashing, forced password reset |
| 📤 Data Export/Import | Excel + CSV export, bulk import with progress bar, Tally-compatible format |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Language | Python 3.11 |
| Database | Supabase (PostgreSQL) |
| Image Processing | Pillow (PIL) — resize, compress, base64 encode |
| Auth | SHA-256 hashing, role-based access control |
| Email | Gmail API (OAuth2) |
| WhatsApp | Click-to-chat links |
| OCR | pytesseract + pdfplumber |
| Export | openpyxl + xlsxwriter |
| Deployment | Streamlit Community Cloud |

---

## Image Upload

- Accepts **JPG, JPEG, PNG, WEBP**
- Compressed and resized to **150 × 150 px JPEG** (quality 30) before storage
- Stored as **base64 in the `parts.image` TEXT column** in Supabase — no separate file storage needed
- Two upload paths: inline in the Current Stock expander, and via Admin Controls → Upload Part Image (form-based)
- Displayed in the Part Images catalogue page with per-category filtering

---

## Setup

```bash
git clone https://github.com/challanamuskan/shree-tex-fabb-crm
cd shree-tex-fabb-crm
pip install -r requirements.txt
```

Add Streamlit secrets — create `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-or-service-role-key"
admin_email  = "your-gmail-address"
```

Run the database schema in the Supabase SQL Editor (paste `supabase_schema.sql`), then start the app:

```bash
streamlit run app.py
```

---

## Deployment

Hosted on **Streamlit Community Cloud**, connected to the `main` branch of this repository. Pushes to `main` trigger an automatic redeploy.

Secrets (`SUPABASE_URL`, `SUPABASE_KEY`, `admin_email`) are configured in the Streamlit Cloud dashboard under **App settings → Secrets**.

---

## Context

Small textile machinery parts businesses in Rajasthan traditionally run on Tally + WhatsApp — no central system for stock, customers, payments, or staff. Data is fragmented, follow-ups are missed, and there is no way to track business health in real time.

This CRM addresses that for a **2,000+ part inventory** with multiple suppliers, field staff, and customers spread across Rajasthan.

---

## Built by

**Muskan Challana** — AI builder & freelance CRM developer, Jaipur
[muskanchallana.vercel.app](https://muskanchallana.vercel.app)
