# System Configuration Guide

## FinanceHub
- **Bill creation form**: `/financehub` (web) or `/api/financehub/bills` (API)
- **Required fields**: vendor_name, vendor_id, invoice_number, date (YYYY-MM-DD), amount
- **Validation**: Date must be YYYY-MM-DD, vendor must exist, amount must be positive decimal
- **Duplicate check**: Same invoice_number cannot be submitted twice
- **API auth**: Use Bearer token from login

## API Endpoints
- `POST /api/login` - Get auth token (JSON: {username, password})
- `GET /api/invoices?page=1&per_page=10&vendor=name` - List invoices
- `GET /api/invoices/{number}` - Get specific invoice details
- `GET /invoices/{number}/pdf` - Download invoice PDF
- `POST /api/financehub/bills` - Create a bill (JSON body)
- `GET /api/financehub/bills` - List all bills
- `GET /api/financehub/bills/{id}` - Get specific bill
- `GET /api/financehub/vendors` - List known vendors

## Overdue Invoice Management
- Invoices have due dates
- An invoice is overdue if the due date has passed
- To flag overdue invoices, check the `overdue` field or compare `due_date` with today
- Overdue invoices for a vendor can be retrieved by filtering the invoice list
