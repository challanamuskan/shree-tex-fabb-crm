# Satyam Tex Fabb CRM

> Full-stack CRM for a 30-year Indian textile machinery parts dealer — stock, sales, payments, WhatsApp automation, and MIS analytics on Streamlit + Supabase.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![Gmail API](https://img.shields.io/badge/Gmail_API-EA4335?style=flat-square&logo=gmail&logoColor=white)](https://developers.google.com/gmail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen?style=flat-square)](https://satyamtexfab-crm.streamlit.app)

**[🌐 Live App](https://satyamtexfab-crm.streamlit.app)** · **[Builder Portfolio](https://muskanchallana.vercel.app)**

---

## What This Is

Internal CRM built for Satyam Tex Fabb — a 30-year-old textile machinery parts dealer in Bhilwara, Rajasthan. Replaces Tally + WhatsApp chaos with a single organised system for stock, sales, customers, staff, and analytics.

Manages **2,000+ part inventory** across 49 categories, multiple suppliers, field staff, and customers spread across Rajasthan.

---

## Features

| Module | What It Does |
|--------|-------------|
| 📦 Stock Manager | Category → Part → Supplier hierarchy; price history; inline image upload |
| 🖼️ Part Images | Image catalogue across all 49 categories — browse, filter, upload |
| 💰 Sales | Record with invoice number; stock auto-decrements; party from customer list |
| 📥 Purchases | Stock auto-increments; new parts auto-added to inventory |
| ↩️ Returns | Sale and purchase returns with document upload |
| 💳 Payments | Overdue highlighting; receipt upload; 7 reminder email templates |
| 🛒 Purchase Orders | Create POs with supplier dropdown; send via Email or WhatsApp |
| 👥 Customers & Leads | CRM contacts; lead status; follow-up dates |
| 📧 Email Alerts | Low-stock alerts; bulk promotional emails; payment reminders |
| 📊 MIS Analytics | Monthly revenue; top products; top customers; customer × product matrix |
| 📅 Calendar | Payment dues and follow-up dates in one view |
| 👤 Employee Management | Add/remove staff; roles; attendance tracking; daily activity logs |
| 🔐 User Management | Admin/Employee RBAC; SHA-256 hashing; forced password reset |
| 📤 Export/Import | Excel + CSV export; bulk import with progress bar; Tally-compatible format |
| 💬 WhatsApp Chat Parser | Upload WhatsApp Business .txt exports. Auto-detects lead intents (Order Inquiry, Price Inquiry, Follow Up, Complaint). All messages stored in Supabase with date, sender, and phone extraction. |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Language | Python 3.11 |
| Database | Supabase (PostgreSQL) |
| Image Processing | Pillow — resize, compress, base64 encode to DB |
| Auth | SHA-256 hashing, role-based access control |
| Email | Gmail API (OAuth2) |
| WhatsApp | Click-to-chat links |
| OCR | pytesseract + pdfplumber |
| Export | openpyxl + xlsxwriter |
| Deployment | Streamlit Community Cloud |

---

## Live Demo

**[satyamtexfab-crm.streamlit.app](https://satyamtexfab-crm.streamlit.app)**

---

## Key Results

- Replaced fragmented Tally + WhatsApp operations for a 30-year family business
- 2,000+ SKUs with full supplier price history tracked in real time
- Automated low-stock email alerts — no manual stock checks on 1st/15th
- Part image catalogue across 49 categories stored directly in Supabase (no file storage needed)
- Field staff daily reports and attendance tracked from one dashboard

---

## Setup

```bash
git clone https://github.com/challanamuskan/shree-tex-fabb-crm
cd shree-tex-fabb-crm
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-or-service-role-key"
admin_email  = "your-gmail-address"
```

Run `supabase_schema.sql` in Supabase SQL Editor, then:
```bash
streamlit run app.py
```

---

## Deployment

Hosted on Streamlit Community Cloud. Pushes to `main` trigger automatic redeploy. Secrets configured under App settings → Secrets.

---

## Related

- **[indian-sme-crm-template](https://github.com/challanamuskan/indian-sme-crm-template)** — Earlier version with Google Sheets backend — easier to fork and adapt
- **[sme-inbox-parser](https://github.com/challanamuskan/sme-inbox-parser)** — Parse WhatsApp + Gmail + website leads into CRM CSV
- **[awesome-indian-sme-tools](https://github.com/challanamuskan/awesome-indian-sme-tools)** — Curated toolkit for Indian SME software builders

---

---

## Changelog

### v2.1 — May 2026
- Added WhatsApp Business Chat Parser with Supabase storage, dual-format parsing, and intent detection

---

[Portfolio](https://muskanchallana.vercel.app) · [LinkedIn](https://www.linkedin.com/in/muskan-challana-408234163/) · [Email](mailto:cmuskan2068@gmail.com) · [GitHub](https://github.com/challanamuskan)
