"""Policy engine: enforces security policies IN CODE before every tool call.
Reads rules from policy.yaml, checks domains, risk levels, approval thresholds,
and content safety. This is NOT just a prompt instruction - it's a hard code gate."""
import re
import yaml
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from opsagent.config import POLICY_FILE, APPROVAL_THRESHOLD


class PolicyDecision:
    """Result of a policy check."""
    def __init__(self, allowed: bool, reason: str = "",
                 requires_approval: bool = False, approval_context: str = ""):
        self.allowed = allowed
        self.reason = reason
        self.requires_approval = requires_approval
        self.approval_context = approval_context

    def __bool__(self):
        return self.allowed

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "approval_context": self.approval_context,
        }


class PolicyEngine:
    """Enforces security policies from YAML config before tool execution."""

    def __init__(self, policy_path: str | Path = None):
        path = Path(policy_path) if policy_path else POLICY_FILE
        with open(path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.allowed_domains = set(self.config.get('allowed_domains', []))
        self.risk_levels = self.config.get('risk_levels', {})
        self.tool_policies = self.config.get('tool_policies', {})
        self.approval_rules = self.config.get('approval_rules', [])
        self.content_safety = self.config.get('content_safety', {})
        self.injection_patterns = [
            p.lower() for p in self.content_safety.get('injection_patterns', [])
        ]

    def check_tool_call(self, tool_name: str, args: dict = None,
                         context: dict = None) -> PolicyDecision:
        """Check if a tool call is allowed by policy. Called BEFORE every execution."""
        args = args or {}
        context = context or {}

        # 1. Check if tool is known
        tool_policy = self.tool_policies.get(tool_name)
        if not tool_policy:
            return PolicyDecision(False, f"Unknown tool '{tool_name}' not in policy registry")

        # 2. Check risk level
        risk = tool_policy.get('risk', 'read')
        risk_config = self.risk_levels.get(risk, {})

        if not risk_config.get('allowed', True):
            return PolicyDecision(
                False,
                risk_config.get('message', f"Actions with risk level '{risk}' are blocked by policy"),
            )

        # 3. Check domain restrictions
        if tool_policy.get('domain_check', False):
            url = args.get('url', '')
            if url:
                decision = self._check_domain(url)
                if not decision:
                    return decision

        # 4. Check for destructive operations
        if risk == 'destructive':
            return PolicyDecision(
                False,
                "Destructive operations are forbidden by policy. Must escalate to supervisor.",
                requires_approval=False,
            )

        # 5. Check amount threshold for write operations
        if risk == 'write':
            amount = self._extract_amount(args, context)
            if amount and amount > APPROVAL_THRESHOLD:
                return PolicyDecision(
                    True,
                    f"Amount Rs {amount:,.2f} exceeds threshold of Rs {APPROVAL_THRESHOLD:,.2f}",
                    requires_approval=True,
                    approval_context=f"Transaction of Rs {amount:,.2f} requires human approval "
                                    f"(threshold: Rs {APPROVAL_THRESHOLD:,.2f})"
                )

        # 6. Check content safety for any data being processed
        content_to_check = args.get('content', '') or args.get('text', '') or ''
        if content_to_check:
            safety = self.check_content_safety(content_to_check)
            if not safety:
                return safety

        return PolicyDecision(True, f"Allowed: {tool_name} (risk: {risk})")

    def _check_domain(self, url: str) -> PolicyDecision:
        """Verify URL is in the allowed domains list."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ''
            if not any(hostname == d or hostname.endswith('.' + d)
                       for d in self.allowed_domains):
                return PolicyDecision(
                    False,
                    f"Domain '{hostname}' is not in the allowed list: {self.allowed_domains}"
                )
        except Exception as e:
            return PolicyDecision(False, f"Invalid URL '{url}': {e}")
        return PolicyDecision(True, "Domain allowed")

    def _extract_amount(self, args: dict, context: dict) -> Optional[float]:
        """Try to extract a monetary amount from the tool args or context."""
        for source in [args, context]:
            for key in ['amount', 'total', 'value']:
                val = source.get(key)
                if val is not None:
                    try:
                        cleaned = str(val).replace(',', '').replace('Rs', '').replace('₹', '').strip()
                        return float(cleaned)
                    except (ValueError, TypeError):
                        continue
        return None

    def check_content_safety(self, content: str) -> PolicyDecision:
        """Check content for prompt injection or manipulation attempts."""
        if not content:
            return PolicyDecision(True, "No content to check")

        content_lower = content.lower()
        for pattern in self.injection_patterns:
            if pattern in content_lower:
                return PolicyDecision(
                    False,
                    f"Content safety violation: detected injection pattern '{pattern}'. "
                    f"Treating content as untrusted data, not as instructions."
                )
        return PolicyDecision(True, "Content safety check passed")

    def check_delete_request(self) -> PolicyDecision:
        """Explicitly check if delete is allowed (it never is)."""
        return PolicyDecision(
            False,
            "DELETE operations are forbidden by company policy. "
            "This request must be escalated to a supervisor.",
        )

    def get_policy_summary(self) -> dict:
        """Return a summary of active policies for display."""
        return {
            "allowed_domains": list(self.allowed_domains),
            "risk_levels": {k: {"allowed": v.get("allowed", True),
                                "requires_approval": v.get("requires_approval", False)}
                           for k, v in self.risk_levels.items()},
            "approval_threshold": APPROVAL_THRESHOLD,
            "injection_patterns_count": len(self.injection_patterns),
            "tools_registered": len(self.tool_policies),
        }
