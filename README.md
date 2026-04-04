# Satyam Tex Fabb CRM

## Problem
Small textile machinery parts businesses in Rajasthan run on Tally + WhatsApp - no central system for stock, customers, payments, or staff. Data is fragmented, follow-ups are missed, and there is no way to track business health in real time.

## What it does
Complete CRM for Satyam Tex Fabb - 30-year-old textile machinery parts dealer in Bhilwara, Rajasthan:
- 📦 Stock Manager - Category -> Part -> Supplier hierarchy, multi-supplier price tracking
- 💰 Sales - Record sales with bill upload, stock auto-reduces
- 📥 Purchases - Record purchases with bill upload, stock auto-increases
- ↩️ Returns - Sale and purchase returns with document upload
- 💳 Payments - Payment tracking with receipt upload and overdue alerts
- 📧 Email + WhatsApp - Payment reminders and purchase orders sent automatically
- 📅 Calendar - Colour-coded payment dues and follow-up dates
- 📊 MIS - Daily task assignment, employee attendance, performance dashboard
- 🔐 Login - Role-based access (Admin/Employee) with password management
- 📤 Export/Import - Excel, CSV, PDF export; Tally import support
- 🔍 OCR Bill Scanning - Upload a photo of a bill, data auto-fills form fields
- ⚠️ Low Stock Alerts - Real-time reorder notifications when stock hits threshold
- 💰 Price History - Full supplier price history tracked forever, update anytime

## Live link
🔗 https://satyam-tex-fabb.streamlit.app

## Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | Python 3.9+ |
| Database | Google Sheets (gspread) |
| Email | Gmail API (OAuth2) |
| WhatsApp | click-to-chat links |
| OCR | pytesseract + pdfplumber |
| Export | openpyxl + xlsxwriter |
| Auth | SHA-256 hashing |
| Deployment | Streamlit Community Cloud |

## How to run
1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies with pip install -r requirements.txt.
4. Add your Google service account JSON and Gmail credentials in the project root.
5. Run streamlit run app.py.
