from core.config import load_config


def gate_claims(audited_claims, config=None):
    if config is None:
        config = load_config()

    threshold = config.defense.anomaly_threshold
    approved = []
    rejected = []

    for claim in audited_claims:
        if claim["anomaly_score"] >= threshold:
            rejected.append({**claim, "gate_decision": "rejected"})
        else:
            approved.append({**claim, "gate_decision": "approved"})

    return approved, rejected
