# ⚙️ Satyam Tex Fabb CRM

[![Python 3.9](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-FF4B4B?style=flat-square)](https://streamlit.io/)
[![Google Sheets](https://img.shields.io/badge/Database-Google%20Sheets-34A853?style=flat-square)](https://sheets.google.com/)
[![Deployed](https://img.shields.io/badge/Deployed-Streamlit%20Cloud-FF4B4B?style=flat-square)](https://satyam-tex-fabb.streamlit.app)

## Overview

Satyam Tex Fabb CRM is a comprehensive Customer Relationship Management system designed specifically for textile machinery parts businesses. Built with Python and Streamlit, this application provides an intuitive interface for managing inventory, customers, payments, and communications—all backed by Google Sheets as a live, accessible database.

## ✨ Features

- **🔐 Secure Login** — Role-based access control for Admin and Employee users
- **📦 Stock Manager** — Track purchases, sales, and returns with real-time inventory updates
- **👥 Customer & Lead Management** — Maintain customer profiles and nurture sales opportunities
- **💰 Payment Tracking** — Monitor payments with automated overdue alerts
- **📧 Email & WhatsApp Reminders** — Send automated payment reminders and promotional messages
- **📅 Calendar System** — Colour-coded events for better visual organization
- **📊 MIS System** — Employee attendance tracking and comprehensive daily reports
- **🤖 AI-Powered Email Composer** — Generate professional promotional emails with AI assistance
- **🗂️ Google Sheets Integration** — Live database syncing for seamless multi-user access

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit |
| **Backend** | Python 3.9+ |
| **Database** | Google Sheets + gspread |
| **Notifications** | Gmail API, PyWhatKit (WhatsApp) |
| **Authentication** | Google Service Account |
| **Deployment** | Streamlit Cloud |

## 🚀 Live Demo

Experience the application live: [Satyam Tex Fabb CRM](https://satyam-tex-fabb.streamlit.app)

## 📸 Screenshots

Screenshots coming soon

## 🏗️ Setup Instructions

### Prerequisites
- Python 3.9 or higher
- Google Cloud Project with Sheets API enabled
- Gmail API credentials

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/challanamuskan/shree-tex-fabb-crm.git
   cd shree-tex-fabb-crm
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**
   - Place your Google Service Account JSON file as `textile-part-crm-credentials.json`
   - Set up Gmail and WhatsApp API credentials as needed

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

The app will open at `http://localhost:8501`

## 📋 Project Structure

```
.
├── app.py                          # Main Streamlit application
├── pages/                          # Multi-page application modules
│   ├── 0_🔐_Login.py              # Authentication
│   ├── 1_Stock_Manager.py         # Inventory management
│   ├── 2_Customers_Leads.py       # Customer database
│   ├── 3_Payments.py              # Payment tracking
│   ├── 4_Payment_Reminders.py     # Automated reminders
│   ├── 4_Purchase_Orders.py       # PO management
│   ├── 5_Promotional_Emails.py    # Email campaigns
│   ├── 6_Calendar.py              # Event calendar
│   ├── 7_MIS.py                   # Management information system
│   ├── 8_User_Management.py       # Admin controls
│   └── 9_Change_Password.py       # User settings
├── utils/                          # Utility modules
│   ├── auth.py                    # Authentication logic
│   ├── constants.py               # Application constants
│   ├── gmail_sender.py            # Email integration
│   ├── sheets_db.py               # Google Sheets database
│   ├── theme.py                   # UI theming
│   ├── ui.py                      # UI components
│   └── whatsapp_sender.py         # WhatsApp integration
├── requirements.txt               # Python dependencies
└── README.md                       # This file
```

## 📝 License

This project is confidential and proprietary to Satyam Tex Fabb.

---

**Built by** — Muskan Challana | [github.com/challanamuskan](https://github.com/challanamuskan)
