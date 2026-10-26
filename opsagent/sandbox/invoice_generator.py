"""PDF invoice generator for sandbox vendor portal.
Generates text-PDF invoices with different layouts and date formats."""
import io
import random
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors


VENDORS = [
    {"id": "V001", "name": "Acme Supplies Pvt Ltd", "address": "123 Industrial Area, Mumbai"},
    {"id": "V002", "name": "Acme Supply Co", "address": "456 Trade Center, Delhi"},
    {"id": "V003", "name": "Beta Traders", "address": "789 Commerce Park, Bangalore"},
    {"id": "V004", "name": "Gamma Electronics Ltd", "address": "321 Tech Hub, Hyderabad"},
    {"id": "V005", "name": "Delta Services Inc", "address": "654 Business Bay, Chennai"},
]

DATE_FORMATS = [
    "%d/%m/%Y",       # 25/10/2024
    "%m-%d-%Y",       # 10-25-2024
    "%d %B %Y",       # 25 October 2024
    "%Y.%m.%d",       # 2024.10.25
    "%d-%b-%Y",       # 25-Oct-2024
]

LAYOUTS = ["standard", "compact", "detailed"]


def generate_invoice_pdf(vendor: dict, invoice_num: str, date: datetime,
                         amount: float, layout: str = "standard",
                         date_format_idx: int = 0) -> bytes:
    """Generate a PDF invoice with the specified parameters."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    date_str = date.strftime(DATE_FORMATS[date_format_idx % len(DATE_FORMATS)])

    if layout == "compact":
        _draw_compact(c, w, h, vendor, invoice_num, date_str, amount)
    elif layout == "detailed":
        _draw_detailed(c, w, h, vendor, invoice_num, date_str, amount)
    else:
        _draw_standard(c, w, h, vendor, invoice_num, date_str, amount)

    c.save()
    return buf.getvalue()


def _draw_standard(c, w, h, vendor, inv_num, date_str, amount):
    """Standard invoice layout."""
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, h - 60, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(40, h - 80, f"Invoice No: {inv_num}")
    c.drawString(40, h - 95, f"Date: {date_str}")

    # Vendor info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, h - 130, "From:")
    c.setFont("Helvetica", 10)
    c.drawString(40, h - 145, vendor["name"])
    c.drawString(40, h - 160, vendor["address"])
    c.drawString(40, h - 175, f"Vendor ID: {vendor['id']}")

    # Bill to
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, h - 130, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(350, h - 145, "OpsAgent Corp")
    c.drawString(350, h - 160, "100 Main Street, Mumbai")

    # Line items table
    y = h - 220
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Description")
    c.drawString(300, y, "Qty")
    c.drawString(370, y, "Rate")
    c.drawString(450, y, "Amount")
    c.line(40, y - 5, 530, y - 5)

    items = _generate_line_items(amount)
    c.setFont("Helvetica", 10)
    for item in items:
        y -= 20
        c.drawString(40, y, item["desc"])
        c.drawString(300, y, str(item["qty"]))
        c.drawString(370, y, f"Rs {item['rate']:,.2f}")
        c.drawString(450, y, f"Rs {item['amount']:,.2f}")

    # Total
    y -= 30
    c.line(40, y + 10, 530, y + 10)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(370, y, "Total:")
    c.drawString(450, y, f"Rs {amount:,.2f}")

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(40, 40, f"Generated invoice for {vendor['name']} | {inv_num}")


def _draw_compact(c, w, h, vendor, inv_num, date_str, amount):
    """Compact single-section layout."""
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, h - 50, f"Invoice {inv_num}")

    c.setFont("Helvetica", 10)
    c.drawString(40, h - 75, f"Vendor: {vendor['name']} ({vendor['id']})")
    c.drawString(40, h - 90, f"Address: {vendor['address']}")
    c.drawString(40, h - 105, f"Invoice Date: {date_str}")
    c.drawString(40, h - 120, f"Total Amount: Rs {amount:,.2f}")

    # Simple items
    y = h - 155
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Items:")
    items = _generate_line_items(amount)
    c.setFont("Helvetica", 9)
    for item in items:
        y -= 18
        c.drawString(50, y, f"- {item['desc']}: {item['qty']} x Rs {item['rate']:,.2f} = Rs {item['amount']:,.2f}")

    c.setFont("Helvetica", 8)
    c.drawString(40, 40, f"Compact invoice | {vendor['name']}")


def _draw_detailed(c, w, h, vendor, inv_num, date_str, amount):
    """Detailed layout with extra fields."""
    # Header with box
    c.setStrokeColor(colors.navy)
    c.setLineWidth(2)
    c.rect(30, h - 100, w - 60, 80)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(45, h - 55, "TAX INVOICE")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 45, h - 40, f"No: {inv_num}")
    c.drawRightString(w - 45, h - 55, f"Date: {date_str}")
    c.drawRightString(w - 45, h - 70, f"Due: Net 30 Days")

    # Vendor section
    y = h - 130
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Supplier Details")
    c.line(40, y - 3, 250, y - 3)
    c.setFont("Helvetica", 10)
    c.drawString(40, y - 18, f"Name: {vendor['name']}")
    c.drawString(40, y - 33, f"ID: {vendor['id']}")
    c.drawString(40, y - 48, f"Address: {vendor['address']}")
    c.drawString(40, y - 63, f"GSTIN: 27AAA{vendor['id']}1Z5")

    # Buyer
    c.setFont("Helvetica-Bold", 11)
    c.drawString(350, y, "Buyer Details")
    c.line(350, y - 3, 530, y - 3)
    c.setFont("Helvetica", 10)
    c.drawString(350, y - 18, "OpsAgent Corp")
    c.drawString(350, y - 33, "100 Main Street")
    c.drawString(350, y - 48, "Mumbai 400001")

    # Items table
    y -= 95
    c.setFont("Helvetica-Bold", 9)
    headers = [("S.No", 40), ("Description", 80), ("HSN", 250), ("Qty", 300),
               ("Rate (Rs)", 350), ("Tax %", 420), ("Amount (Rs)", 470)]
    for label, x in headers:
        c.drawString(x, y, label)
    c.line(35, y - 5, 555, y - 5)

    items = _generate_line_items(amount)
    c.setFont("Helvetica", 9)
    subtotal = 0
    for i, item in enumerate(items):
        y -= 18
        c.drawString(40, y, str(i + 1))
        c.drawString(80, y, item["desc"])
        c.drawString(250, y, "8471")
        c.drawString(300, y, str(item["qty"]))
        c.drawString(350, y, f"{item['rate']:,.2f}")
        c.drawString(420, y, "18%")
        c.drawString(470, y, f"{item['amount']:,.2f}")
        subtotal += item['amount']

    # Totals
    y -= 25
    c.line(35, y + 10, 555, y + 10)
    tax = amount - subtotal
    c.setFont("Helvetica", 10)
    c.drawString(370, y, f"Subtotal: Rs {subtotal:,.2f}")
    c.drawString(370, y - 15, f"GST (18%): Rs {tax:,.2f}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(370, y - 35, f"Grand Total: Rs {amount:,.2f}")

    c.setFont("Helvetica", 8)
    c.drawString(40, 40, f"Tax Invoice | {vendor['name']} | {inv_num}")


def _generate_line_items(total_amount: float) -> list:
    """Generate realistic line items that sum close to total."""
    items_pool = [
        "Office Supplies Bundle", "Printer Cartridges (Black)", "A4 Paper (5 reams)",
        "Desk Organizer Set", "USB-C Cables (10-pack)", "Wireless Mouse",
        "Monitor Stand", "Cable Management Kit", "Whiteboard Markers (12)",
        "Ergonomic Keyboard", "Network Switch 8-Port", "External SSD 500GB",
        "Server Maintenance Q4", "Cloud Hosting Monthly", "Software License Annual",
    ]
    n = random.randint(2, 5)
    selected = random.sample(items_pool, min(n, len(items_pool)))

    base_amount = total_amount / 1.18  # remove tax portion for detailed layout
    portions = [random.random() for _ in selected]
    total_p = sum(portions)
    portions = [p / total_p for p in portions]

    items = []
    running = 0
    for i, desc in enumerate(selected):
        qty = random.randint(1, 10)
        item_total = round(base_amount * portions[i], 2)
        if i == len(selected) - 1:
            item_total = round(base_amount - running, 2)
        rate = round(item_total / qty, 2)
        item_total = round(rate * qty, 2)
        running += item_total
        items.append({"desc": desc, "qty": qty, "rate": rate, "amount": item_total})
    return items


def generate_invoices_for_vendor(vendor: dict, count: int = 5) -> list:
    """Generate a set of invoices for a vendor."""
    invoices = []
    base_date = datetime(2024, 1, 1)
    for i in range(count):
        inv_num = f"INV-{vendor['id']}-{2024}-{str(i+1).zfill(4)}"
        date = base_date + timedelta(days=random.randint(0, 365))
        amount = round(random.uniform(5000, 150000), 2)
        layout = LAYOUTS[i % len(LAYOUTS)]
        date_fmt_idx = i % len(DATE_FORMATS)
        pdf_bytes = generate_invoice_pdf(vendor, inv_num, date, amount, layout, date_fmt_idx)

        invoices.append({
            "invoice_number": inv_num,
            "vendor_id": vendor["id"],
            "vendor_name": vendor["name"],
            "date": date.strftime("%Y-%m-%d"),
            "date_display": date.strftime(DATE_FORMATS[date_fmt_idx]),
            "amount": amount,
            "layout": layout,
            "pdf_bytes": pdf_bytes,
            "status": "pending" if i >= count - 2 else "processed",
        })
    return invoices
