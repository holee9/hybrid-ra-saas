"""Safe applicability rule evaluator — no eval/exec.

# @MX:NOTE: [AUTO] ApplicabilityRule safe evaluator — no eval/exec
#           Supports: field == "value", field != "value",
#                     field == true/false, field contains "value"
"""

from __future__ import annotations

from app.models.applicability_rule import ApplicabilityRule
from app.models.product_profile import ProductProfile


def evaluate_rule(rule: ApplicabilityRule | None, profile: ProductProfile) -> bool:
    """Evaluate an applicability rule against a ProductProfile.

    Returns True if the rule passes (section is applicable).
    Returns True if rule is None (always applicable).

    Supports conditions:
    - field == "value"   (string equality)
    - field != "value"   (string inequality)
    - field == true      (boolean true check)
    - field == false     (boolean false check)
    - field contains "value"  (list membership for JSON array fields)
    """
    if rule is None:
        return True

    field = rule.condition_field
    condition = rule.condition_value.strip()

    # Retrieve field value from product profile
    profile_value = getattr(profile, field, None)

    # --- boolean checks ---
    if condition.lower() == "true":
        return bool(profile_value)
    if condition.lower() == "false":
        return not bool(profile_value)

    # --- contains check for list fields ---
    if condition.startswith("contains "):
        target = condition[len("contains "):].strip().strip('"').strip("'")
        if isinstance(profile_value, list):
            return target in profile_value
        return False

    # --- equality / inequality ---
    # Strip surrounding quotes from value
    stripped = condition.strip('"').strip("'")

    if condition.startswith("!= ") or condition.startswith("!="):
        neg_value = condition.lstrip("!=").strip().strip('"').strip("'")
        return str(profile_value) != neg_value

    # default: equality
    return str(profile_value) == stripped
