"""Deterministic authorization and construction of post-synthesis actions."""

from defense.action_agent import trusted_email_recipients


def authorize_action(proposal, original_query, approved_claims, role="employee"):
    action = str((proposal or {}).get("action", "none")).lower()
    if action == "none":
        return {
            "approved": False,
            "decision": "no_action",
            "reason": str((proposal or {}).get("reason", "no action proposed")),
        }
    if action != "email":
        return {
            "approved": False,
            "decision": "rejected",
            "reason": "unsupported action type",
        }

    trusted_recipients = {
        recipient.lower(): recipient
        for recipient in trusted_email_recipients(original_query)
    }
    proposed_recipient = str((proposal or {}).get("to", "")).strip()
    if not trusted_recipients:
        return {
            "approved": False,
            "decision": "rejected",
            "reason": "trusted user query did not explicitly authorize email",
        }
    if proposed_recipient.lower() not in trusted_recipients:
        return {
            "approved": False,
            "decision": "rejected",
            "reason": "recipient did not originate in the trusted user query",
        }

    requested_ids = (proposal or {}).get("claim_ids", [])
    if not isinstance(requested_ids, list) or not requested_ids:
        return {
            "approved": False,
            "decision": "rejected",
            "reason": "email proposal did not select approved claims",
        }

    approved_by_id = {
        str(claim.get("claim_id")): claim
        for claim in approved_claims
        if claim.get("claim_id") is not None
    }
    selected = []
    for claim_id in requested_ids:
        canonical_id = str(claim_id)
        if canonical_id not in approved_by_id:
            return {
                "approved": False,
                "decision": "rejected",
                "reason": f"claim {canonical_id!r} was not approved",
            }
        if approved_by_id[canonical_id] not in selected:
            selected.append(approved_by_id[canonical_id])

    body_lines = [
        f"{claim.get('field', 'value')}: {claim.get('value', '')}"
        for claim in selected
    ]
    return {
        "approved": True,
        "decision": "approved",
        "reason": "trusted request, recipient, and claim provenance verified",
        "to": trusted_recipients[proposed_recipient.lower()],
        "subject": "Requested employee report",
        "body": "\n".join(body_lines),
        "claim_ids": [str(claim.get("claim_id")) for claim in selected],
        "role": role,
    }
