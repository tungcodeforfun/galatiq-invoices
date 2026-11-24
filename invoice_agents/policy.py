"""Business rules from policy.yaml and the deterministic gate that stands between any decision and payment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from invoice_agents.schema import Decision, Disposition, Finding, Severity

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "policy.yaml"


class FindingRule(BaseModel):
    """How one finding code affects the outcome."""

    severity: Severity
    disposition: Disposition | None = None


class Policy(BaseModel):
    """Thresholds and finding rules the business can change without touching code."""

    approval_threshold: float
    near_threshold_pct: float
    total_tolerance: float
    price_tolerance_pct: float
    currencies: list[str]
    max_rounds: int
    payment_attempts: int
    human_signoff_over: float | None = None
    findings: dict[str, FindingRule]

    def finding(self, code: str, message: str, source: str, subject: str = "", **evidence: Any) -> Finding:
        """Build a finding whose severity comes from policy, never from the caller."""
        return Finding(
            code=code,
            severity=self.findings[code].severity,
            message=message,
            subject=subject,
            evidence=evidence,
            source=source,
        )


class GateResult(BaseModel):
    """Whether payment may proceed, and every reason it may not."""

    approved: bool
    blocked_by: list[str]
    overridden: bool


def load_policy(path: Path = DEFAULT_POLICY) -> Policy:
    """Read policy.yaml."""
    return Policy.model_validate(yaml.safe_load(path.read_text()))


def gate(
    decision: Decision | None,
    findings: list[Finding],
    total: float | None,
    critic_rounds: int,
    degraded: bool,
    policy: Policy,
) -> GateResult:
    """Allow payment only if the approver approved and no rule forbids it. Agents can be stricter, never looser."""
    if decision is None or decision.action == "reject":
        return GateResult(approved=False, blocked_by=["approver rejected"], overridden=False)
    blocked_by = [f"{f.id} {f.code}" for f in findings if f.severity == Severity.REJECT]
    if total is None or total <= 0:
        blocked_by.append("no positive total to pay")
    elif total > policy.approval_threshold and critic_rounds == 0:
        blocked_by.append(f"over ${policy.approval_threshold:,.0f} without critic review")
    # Without a model nobody has read the free text, so rules alone may only pay small, spotless invoices.
    if degraded and (
        (total or 0) > policy.approval_threshold or any(f.severity != Severity.INFO for f in findings)
    ):
        blocked_by.append("degraded mode pays only clean invoices under the approval threshold")
    return GateResult(approved=not blocked_by, blocked_by=blocked_by, overridden=bool(blocked_by))


def required_disposition(findings: list[Finding], policy: Policy) -> Disposition | None:
    """Disposition forced by findings: void beats return_to_vendor; None when no finding decides it."""
    dispositions = {policy.findings[f.code].disposition for f in findings}
    if "void" in dispositions:
        return "void"
    if "return_to_vendor" in dispositions:
        return "return_to_vendor"
    return None
