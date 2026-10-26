"""Sandbox server: Vendor Portal + FinanceHub in one FastAPI app.
Simulates a real company environment with login, sessions, invoices, and bill creation."""
import os
import random
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Request, Response, Form, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
import io

from opsagent.sandbox.invoice_generator import (
    VENDORS, generate_invoices_for_vendor, generate_invoice_pdf, DATE_FORMATS
)
from opsagent.config import SANDBOX_USERNAME, SANDBOX_PASSWORD

app = FastAPI(title="Sandbox Company World", version="1.0.0")

# ---------- In-memory state ----------
sessions: dict[str, dict] = {}   # token -> {user, expires_at, created_at}
invoices_cache: list[dict] = []  # generated invoices
bills_db: list[dict] = []        # created bill records
first_submit_done: dict[str, bool] = {}  # per-session track of 503 injection
SESSION_DURATION_SECONDS = 300  # 5 min sessions (expire mid-task)

# Due dates for overdue tracking
OVERDUE_INVOICES: dict[str, str] = {}  # invoice_number -> due_date


def _init_invoices():
    """Generate all vendor invoices on startup."""
    global invoices_cache
    if invoices_cache:
        return
    random.seed(42)  # Reproducible for testing
    for vendor in VENDORS:
        vendor_invoices = generate_invoices_for_vendor(vendor, count=6)
        for inv in vendor_invoices:
            # Strip pdf_bytes for the list view, store separately
            inv_copy = {k: v for k, v in inv.items() if k != 'pdf_bytes'}
            # Assign due dates (some overdue for Beta Traders)
            inv_date = datetime.strptime(inv['date'], '%Y-%m-%d')
            if vendor['name'] == 'Beta Traders':
                due = inv_date + timedelta(days=30)
                if due < datetime(2024, 10, 1):
                    inv_copy['due_date'] = due.strftime('%Y-%m-%d')
                    inv_copy['overdue'] = True
                    OVERDUE_INVOICES[inv['invoice_number']] = due.strftime('%Y-%m-%d')
                else:
                    inv_copy['due_date'] = due.strftime('%Y-%m-%d')
                    inv_copy['overdue'] = False
            else:
                due = inv_date + timedelta(days=45)
                inv_copy['due_date'] = due.strftime('%Y-%m-%d')
                inv_copy['overdue'] = due < datetime(2024, 10, 1)

            invoices_cache.append(inv_copy)

    random.seed()  # Reset seed


_init_invoices()


# ---------- Auth middleware ----------
def _check_session(token: str) -> dict | None:
    if not token:
        return None
    sess = sessions.get(token)
    if not sess:
        return None
    if datetime.now(timezone.utc).isoformat() > sess['expires_at']:
        del sessions[token]
        return None
    return sess


def get_token(request: Request) -> str | None:
    """Extract session token from cookie or Authorization header."""
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token


# ---------- Vendor Portal Routes ----------

@app.get("/", response_class=HTMLResponse)
async def portal_home():
    return """
    <html><head><title>Vendor Portal</title></head><body>
    <h1>Vendor Portal</h1>
    <p>Welcome to the vendor invoice portal.</p>
    <p><a href="/login">Login</a> | <a href="/api/docs">API Docs</a></p>
    </body></html>
    """


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
    <html><head><title>Login - Vendor Portal</title></head><body>
    <h1>Vendor Portal Login</h1>
    <form method="post" action="/login">
        <label for="username">Username:</label><br>
        <input type="text" id="username" name="username"><br><br>
        <label for="password">Password:</label><br>
        <input type="password" id="password" name="password"><br><br>
        <button type="submit" id="login-button">Login</button>
    </form>
    </body></html>
    """


@app.post("/login")
async def do_login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == SANDBOX_USERNAME and password == SANDBOX_PASSWORD:
        token = secrets.token_hex(16)
        expires = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_DURATION_SECONDS)).isoformat()
        sessions[token] = {
            "user": username,
            "expires_at": expires,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        resp = HTMLResponse(f"""
        <html><head><title>Login Success</title></head><body>
        <h1>Login Successful</h1>
        <p>Welcome, {username}! Session expires in {SESSION_DURATION_SECONDS} seconds.</p>
        <p><a href="/invoices">View Invoices</a></p>
        </body></html>
        """)
        resp.set_cookie("session_token", token, max_age=SESSION_DURATION_SECONDS)
        return resp
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/login")
async def api_login(request: Request):
    """API login endpoint returning JSON with token."""
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")
    if username == SANDBOX_USERNAME and password == SANDBOX_PASSWORD:
        token = secrets.token_hex(16)
        expires = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_DURATION_SECONDS)).isoformat()
        sessions[token] = {
            "user": username,
            "expires_at": expires,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return {"token": token, "expires_at": expires}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/invoices", response_class=HTMLResponse)
async def invoices_page(request: Request, page: int = Query(1, ge=1),
                         vendor: str = Query("", description="Filter by vendor name")):
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        return HTMLResponse("""
        <html><body>
        <h1>Session Expired or Not Logged In</h1>
        <p>Please <a href="/login">login again</a>.</p>
        </body></html>
        """, status_code=401)

    # Filter & paginate
    filtered = invoices_cache
    if vendor:
        filtered = [i for i in filtered if vendor.lower() in i['vendor_name'].lower()]

    per_page = 5
    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_items = filtered[start:start + per_page]

    rows = ""
    for inv in page_items:
        overdue_mark = " ⚠️ OVERDUE" if inv.get('overdue') else ""
        rows += f"""
        <tr>
            <td>{inv['invoice_number']}</td>
            <td>{inv['vendor_name']}</td>
            <td>{inv['vendor_id']}</td>
            <td>{inv['date_display']}</td>
            <td>{inv['due_date']}{overdue_mark}</td>
            <td>Rs {inv['amount']:,.2f}</td>
            <td>{inv['status']}</td>
            <td><a href="/invoices/{inv['invoice_number']}/pdf">Download PDF</a></td>
        </tr>
        """

    # Pagination links
    prev_link = f'<a href="/invoices?page={page-1}&vendor={vendor}">Previous</a>' if page > 1 else ""
    next_link = f'<a href="/invoices?page={page+1}&vendor={vendor}">Next</a>' if page < total_pages else ""

    return f"""
    <html><head><title>Invoices - Vendor Portal</title></head><body>
    <h1>Invoice List</h1>
    <p>Logged in as: {sess['user']}</p>
    <form method="get" action="/invoices">
        <label>Filter by vendor: </label>
        <input type="text" name="vendor" value="{vendor}" id="vendor-filter">
        <button type="submit">Filter</button>
    </form>
    <table border="1" cellpadding="5">
        <thead><tr>
            <th>Invoice #</th><th>Vendor</th><th>Vendor ID</th>
            <th>Date</th><th>Due Date</th><th>Amount</th><th>Status</th><th>PDF</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <p>Page {page} of {total_pages} | Total: {total} invoices</p>
    <p>{prev_link} {next_link}</p>
    <p><a href="/logout">Logout</a></p>
    </body></html>
    """


@app.get("/api/invoices")
async def api_invoices(request: Request, page: int = Query(1, ge=1),
                       per_page: int = Query(10, ge=1, le=50),
                       vendor: str = Query("", description="Filter by vendor name")):
    """REST API for invoice listing with pagination."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized. Please login first.")

    filtered = invoices_cache
    if vendor:
        filtered = [i for i in filtered if vendor.lower() in i['vendor_name'].lower()]

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_items = filtered[start:start + per_page]

    return {
        "invoices": page_items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


@app.get("/invoices/{invoice_number}/pdf")
async def download_invoice_pdf(invoice_number: str, request: Request):
    """Download the PDF for a specific invoice."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")

    inv = next((i for i in invoices_cache if i['invoice_number'] == invoice_number), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    vendor = next((v for v in VENDORS if v['id'] == inv['vendor_id']), None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    date = datetime.strptime(inv['date'], '%Y-%m-%d')
    layout_idx = invoices_cache.index(inv) % 3
    layouts = ["standard", "compact", "detailed"]
    pdf_bytes = generate_invoice_pdf(vendor, invoice_number, date, inv['amount'],
                                      layouts[layout_idx], invoices_cache.index(inv) % 5)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice_number}.pdf"}
    )


@app.get("/api/invoices/{invoice_number}")
async def api_get_invoice(invoice_number: str, request: Request):
    """Get details of a specific invoice."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")

    inv = next((i for i in invoices_cache if i['invoice_number'] == invoice_number), None)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@app.get("/logout")
async def logout(request: Request, response: Response):
    token = get_token(request)
    if token and token in sessions:
        del sessions[token]
    resp = HTMLResponse("""
    <html><body><h1>Logged Out</h1><p><a href="/login">Login again</a></p></body></html>
    """)
    resp.delete_cookie("session_token")
    return resp


# ---------- FinanceHub Routes ----------

@app.get("/financehub", response_class=HTMLResponse)
async def financehub_home(request: Request):
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        return HTMLResponse('<html><body><h1>Please <a href="/login">login</a></h1></body></html>', status_code=401)

    bill_rows = ""
    for b in bills_db:
        bill_rows += f"""
        <tr>
            <td>{b['id']}</td><td>{b['vendor_name']}</td><td>{b['vendor_id']}</td>
            <td>{b['invoice_number']}</td><td>{b['date']}</td>
            <td>Rs {b['amount']:,.2f}</td><td>{b['status']}</td>
        </tr>"""

    return f"""
    <html><head><title>FinanceHub</title></head><body>
    <h1>FinanceHub - Bill Management</h1>
    <h2>Create New Bill</h2>
    <form method="post" action="/financehub/bills" id="create-bill-form">
        <label>Vendor Name: <input type="text" name="vendor_name" id="vendor_name"></label><br><br>
        <label>Vendor ID: <input type="text" name="vendor_id" id="vendor_id"></label><br><br>
        <label>Invoice Number: <input type="text" name="invoice_number" id="invoice_number"></label><br><br>
        <label>Date (YYYY-MM-DD): <input type="text" name="date" id="date" placeholder="2024-01-15"></label><br><br>
        <label>Amount (Rs): <input type="text" name="amount" id="amount"></label><br><br>
        <label>Description: <input type="text" name="description" id="description"></label><br><br>
        <button type="submit" id="submit-bill">Create Bill</button>
    </form>
    <h2>Existing Bills</h2>
    <table border="1" cellpadding="5">
        <thead><tr><th>ID</th><th>Vendor</th><th>Vendor ID</th><th>Invoice #</th>
        <th>Date</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody>{bill_rows}</tbody>
    </table>
    </body></html>
    """


@app.post("/financehub/bills")
async def create_bill_form(request: Request,
                           vendor_name: str = Form(...),
                           vendor_id: str = Form(...),
                           invoice_number: str = Form(...),
                           date: str = Form(...),
                           amount: str = Form(...),
                           description: str = Form("")):
    """HTML form submission for bill creation."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")

    result = _create_bill(vendor_name, vendor_id, invoice_number, date, amount,
                          description, token)
    if "error" in result:
        return HTMLResponse(f"""
        <html><body>
        <h1>Error</h1><p style="color:red">{result['error']}</p>
        <p><a href="/financehub">Go back</a></p>
        </body></html>
        """, status_code=result.get("status_code", 400))

    return HTMLResponse(f"""
    <html><body>
    <h1>Bill Created Successfully</h1>
    <p>Bill ID: {result['bill']['id']}</p>
    <p>Invoice: {result['bill']['invoice_number']}</p>
    <p>Amount: Rs {result['bill']['amount']:,.2f}</p>
    <p><a href="/financehub">Back to FinanceHub</a></p>
    </body></html>
    """)


@app.post("/api/financehub/bills")
async def api_create_bill(request: Request):
    """REST API for bill creation with validation."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    result = _create_bill(
        body.get("vendor_name", ""),
        body.get("vendor_id", ""),
        body.get("invoice_number", ""),
        body.get("date", ""),
        str(body.get("amount", "")),
        body.get("description", ""),
        token,
    )
    if "error" in result:
        raise HTTPException(status_code=result.get("status_code", 400), detail=result["error"])
    return result


@app.get("/api/financehub/bills")
async def api_list_bills(request: Request):
    """List all bills via REST API."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"bills": bills_db, "total": len(bills_db)}


@app.get("/api/financehub/bills/{bill_id}")
async def api_get_bill(bill_id: str, request: Request):
    """Get a specific bill by ID."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")

    bill = next((b for b in bills_db if b['id'] == bill_id), None)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@app.delete("/api/financehub/bills/{bill_id}")
async def api_delete_bill(bill_id: str, request: Request):
    """Delete a bill - should be blocked by policy."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")
    raise HTTPException(status_code=403, detail="Deletion not permitted through API")


@app.get("/api/financehub/vendors")
async def api_list_vendors(request: Request):
    """List known vendors."""
    token = get_token(request)
    sess = _check_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"vendors": VENDORS}


# ---------- Health Check ----------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "sandbox", "invoices": len(invoices_cache)}


# ---------- Bill creation logic ----------
def _create_bill(vendor_name: str, vendor_id: str, invoice_number: str,
                 date: str, amount: str, description: str, token: str) -> dict:
    """Validate and create a bill record. Returns dict with 'bill' or 'error'."""

    # Transient 503: first submission per session fails
    session_key = token[:8] if token else "default"
    if session_key not in first_submit_done:
        first_submit_done[session_key] = True
        return {"error": "Service temporarily unavailable. Please retry.", "status_code": 503}

    # Validate vendor exists
    known_vendor = next((v for v in VENDORS if v['id'] == vendor_id), None)
    if not known_vendor:
        # Also try matching by name
        known_vendor = next((v for v in VENDORS if v['name'].lower() == vendor_name.lower()), None)
        if not known_vendor:
            return {"error": f"Vendor '{vendor_name}' (ID: {vendor_id}) not found. "
                            f"Known vendors: {[v['name'] for v in VENDORS]}", "status_code": 400}

    # Validate date format YYYY-MM-DD
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid date format: '{date}'. Expected YYYY-MM-DD (e.g. 2024-01-15)",
                "status_code": 400}

    # Validate amount
    try:
        amt = float(amount.replace(",", "").replace("Rs", "").replace("₹", "").strip())
        if amt <= 0:
            return {"error": "Amount must be positive", "status_code": 400}
    except (ValueError, AttributeError):
        return {"error": f"Invalid amount: '{amount}'. Must be a decimal number.", "status_code": 400}

    # Check for duplicates
    existing = next((b for b in bills_db if b['invoice_number'] == invoice_number), None)
    if existing:
        return {"error": f"Duplicate: Bill for invoice {invoice_number} already exists (ID: {existing['id']})",
                "status_code": 409}

    bill = {
        "id": f"BILL-{str(len(bills_db) + 1).zfill(4)}",
        "vendor_name": known_vendor['name'],
        "vendor_id": known_vendor['id'],
        "invoice_number": invoice_number,
        "date": date,
        "amount": amt,
        "description": description or f"Bill for {invoice_number}",
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    bills_db.append(bill)
    return {"bill": bill, "message": "Bill created successfully"}


# ---------- Reset endpoint for testing ----------
@app.post("/api/reset")
async def reset_sandbox():
    """Reset sandbox state for testing."""
    global bills_db, first_submit_done
    bills_db = []
    first_submit_done = {}
    return {"status": "reset", "message": "Sandbox state cleared"}
