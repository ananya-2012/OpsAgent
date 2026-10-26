# Invoice Processing Procedures

## Where to Find Invoices
- All vendor invoices are accessible through the **Vendor Portal** at the sandbox URL
- Login required with company credentials (from environment variables)
- Invoices are listed at `/invoices` with pagination (5 per page)
- PDF downloads available for each invoice at `/invoices/{invoice_number}/pdf`
- API access at `/api/invoices` with Bearer token authentication

## Invoice Filing Process
1. Login to the Vendor Portal
2. Navigate to the invoice list and find the required invoice
3. Download the invoice PDF
4. Extract key fields: vendor name, vendor ID, invoice number, date, amount
5. Convert the date to YYYY-MM-DD format (invoices use various formats)
6. Submit the bill to FinanceHub at `/financehub/bills` or via API at `/api/financehub/bills`
7. Verify the created record matches the source invoice

## Date Format Conversion
Invoices come in various date formats. ALL dates must be converted to **YYYY-MM-DD** when entering into FinanceHub. Examples:
- "25/10/2024" (DD/MM/YYYY) → "2024-10-25"
- "10-25-2024" (MM-DD-YYYY) → "2024-10-25"
- "25 October 2024" → "2024-10-25"
- "2024.10.25" → "2024-10-25"
- "25-Oct-2024" → "2024-10-25"

## Error Handling
- The system may return a 503 on first submission - always retry
- Duplicate invoices will be rejected (409 status)
- Validate vendor exists before submitting
