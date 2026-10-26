# Vendor Directory

## Known Vendors

| Vendor ID | Vendor Name | Address | Notes |
|-----------|-------------|---------|-------|
| V001 | Acme Supplies Pvt Ltd | 123 Industrial Area, Mumbai | Primary office supplies vendor |
| V002 | Acme Supply Co | 456 Trade Center, Delhi | Different from "Acme Supplies Pvt Ltd" - similar names! |
| V003 | Beta Traders | 789 Commerce Park, Bangalore | Electronics and IT equipment |
| V004 | Gamma Electronics Ltd | 321 Tech Hub, Hyderabad | Specialized electronics |
| V005 | Delta Services Inc | 654 Business Bay, Chennai | Service provider |

## Important: Vendor Name Disambiguation
- "Acme Supplies Pvt Ltd" (V001) and "Acme Supply Co" (V002) are DIFFERENT vendors
- When a request mentions "Acme" without full name, ALWAYS clarify which vendor is meant
- Use vendor ID to confirm the correct vendor
- Never assume - ask for clarification if the vendor name is ambiguous

## Vendor Portal Access
- URL: Check environment for SANDBOX_BASE_URL
- Login: Use credentials from environment variables
- Session expires after 5 minutes - re-login when session expires
