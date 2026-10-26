"""Independent verifier: re-fetches created records from FinanceHub API and
compares with source invoice values. If they differ, sends discrepancy back."""
import json
import httpx
from opsagent.config import SANDBOX_BASE_URL, SANDBOX_USERNAME, SANDBOX_PASSWORD
from opsagent.database import get_db, update_task, add_audit_entry, get_task


async def verify_task(task_id: str) -> dict:
    """Verify the outcome of a completed task by re-fetching from FinanceHub.

    Returns a verification report with pass/fail and discrepancies.
    """
    db = await get_db()
    task = await get_task(db, task_id)

    if not task:
        await db.close()
        return {"verified": False, "error": "Task not found"}

    if task['status'] != 'completed':
        await db.close()
        return {"verified": False, "error": f"Task not completed (status: {task['status']})"}

    report = {
        "task_id": task_id,
        "verified": False,
        "checks": [],
        "discrepancies": [],
        "evidence": task.get('evidence', []),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Login to get token
            login_resp = await client.post(
                f"{SANDBOX_BASE_URL}/api/login",
                json={"username": SANDBOX_USERNAME, "password": SANDBOX_PASSWORD}
            )
            if login_resp.status_code != 200:
                report["error"] = "Failed to login for verification"
                await db.close()
                return report

            token = login_resp.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Get all bills
            bills_resp = await client.get(
                f"{SANDBOX_BASE_URL}/api/financehub/bills",
                headers=headers
            )
            if bills_resp.status_code != 200:
                report["error"] = "Failed to fetch bills for verification"
                await db.close()
                return report

            bills = bills_resp.json().get("bills", [])

            if not bills:
                report["checks"].append({
                    "check": "bills_exist",
                    "passed": False,
                    "message": "No bills found in FinanceHub"
                })
                await add_audit_entry(db, task_id, "verification",
                                      action="verify", output_data="No bills found")
                await db.close()
                return report

            report["checks"].append({
                "check": "bills_exist",
                "passed": True,
                "message": f"Found {len(bills)} bill(s) in FinanceHub"
            })

            # Get invoices to cross-reference
            invoices_resp = await client.get(
                f"{SANDBOX_BASE_URL}/api/invoices?per_page=50",
                headers=headers
            )
            invoices = invoices_resp.json().get("invoices", []) if invoices_resp.status_code == 200 else []

            # Verify each bill against its source invoice
            all_match = True
            for bill in bills:
                inv_num = bill.get("invoice_number", "")
                source_inv = next((i for i in invoices if i["invoice_number"] == inv_num), None)

                if source_inv:
                    check_result = _compare_bill_to_invoice(bill, source_inv)
                    report["checks"].append(check_result)
                    if not check_result["passed"]:
                        all_match = False
                        report["discrepancies"].extend(check_result.get("discrepancies", []))
                else:
                    report["checks"].append({
                        "check": f"invoice_match_{inv_num}",
                        "passed": False,
                        "message": f"Source invoice {inv_num} not found for verification"
                    })
                    all_match = False

            # Verify date format
            for bill in bills:
                date = bill.get("date", "")
                try:
                    from datetime import datetime as dt
                    dt.strptime(date, "%Y-%m-%d")
                    report["checks"].append({
                        "check": f"date_format_{bill['id']}",
                        "passed": True,
                        "message": f"Date {date} is in correct YYYY-MM-DD format"
                    })
                except ValueError:
                    report["checks"].append({
                        "check": f"date_format_{bill['id']}",
                        "passed": False,
                        "message": f"Date {date} is NOT in YYYY-MM-DD format"
                    })
                    all_match = False

            report["verified"] = all_match
            report["bill_count"] = len(bills)
            report["bills"] = bills

    except Exception as e:
        report["error"] = str(e)

    await add_audit_entry(db, task_id, "verification",
                          action="verify_complete",
                          output_data=json.dumps(report)[:2000])
    await db.close()
    return report


def _compare_bill_to_invoice(bill: dict, invoice: dict) -> dict:
    """Compare a created bill record with its source invoice."""
    discrepancies = []
    inv_num = bill.get("invoice_number", "")

    # Compare vendor name
    if bill.get("vendor_name", "").lower() != invoice.get("vendor_name", "").lower():
        discrepancies.append({
            "field": "vendor_name",
            "bill_value": bill.get("vendor_name"),
            "invoice_value": invoice.get("vendor_name"),
        })

    # Compare vendor ID
    if bill.get("vendor_id", "") != invoice.get("vendor_id", ""):
        discrepancies.append({
            "field": "vendor_id",
            "bill_value": bill.get("vendor_id"),
            "invoice_value": invoice.get("vendor_id"),
        })

    # Compare amount (allow small floating point differences)
    bill_amount = float(bill.get("amount", 0))
    inv_amount = float(invoice.get("amount", 0))
    if abs(bill_amount - inv_amount) > 0.01:
        discrepancies.append({
            "field": "amount",
            "bill_value": bill_amount,
            "invoice_value": inv_amount,
            "difference": abs(bill_amount - inv_amount),
        })

    return {
        "check": f"bill_vs_invoice_{inv_num}",
        "passed": len(discrepancies) == 0,
        "message": f"Bill matches invoice {inv_num}" if not discrepancies
                   else f"Discrepancies found for {inv_num}: {discrepancies}",
        "discrepancies": discrepancies,
    }


async def verify_and_loop_back(task_id: str) -> dict:
    """Verify and if discrepancies found, send back into the agent loop."""
    report = await verify_task(task_id)

    if not report.get("verified") and report.get("discrepancies"):
        # Send discrepancy back into the loop
        from opsagent.runtime.agent import AgentRuntime, emit_event
        db = await get_db()
        await update_task(db, task_id, status='running',
                         error=f"Verification failed: {json.dumps(report['discrepancies'])[:500]}")
        await emit_event(task_id, "verification_failed", {
            "discrepancies": report["discrepancies"],
            "message": "Verification failed - sending back for correction"
        })
        await db.close()

        # Re-run with correction instructions
        correction_desc = (
            f"VERIFICATION FAILED for the previous task. "
            f"Discrepancies found: {json.dumps(report['discrepancies'])}. "
            f"Please correct the bill entry in FinanceHub."
        )
        runtime = AgentRuntime()
        await runtime.run_task(task_id, correction_desc)

        # Re-verify after correction
        return await verify_task(task_id)

    return report
