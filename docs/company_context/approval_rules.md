# Approval and Escalation Rules

## Approval Thresholds
- **Any transaction above Rs 50,000** requires human approval before processing
- The agent must pause and wait for approval before submitting high-value bills
- If denied, the agent must acknowledge and NOT proceed with the transaction

## Escalation Rules
1. **Ambiguous requests**: If the vendor name or details are unclear, ask the human for clarification
2. **Missing information**: If required fields cannot be determined from the invoice, ask for help
3. **Conflicting data**: If extracted data doesn't match expected formats, escalate
4. **System errors**: After 3 failed retries, escalate to human

## Forbidden Actions
- **DELETE operations** are NEVER allowed - any request to delete records must be refused
- The agent must explain that deletion requires supervisor access through a different system
- Record deletion requests must be logged in the audit trail

## Approval Process
1. Agent identifies need for approval (amount > threshold, ambiguous request, etc.)
2. Agent pauses the task and creates an approval request
3. Human reviews the request in the dashboard
4. Human approves or denies
5. Agent resumes based on the response
