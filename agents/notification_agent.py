import json
import os
from core.config import load_config


def run_notification_agent(to, subject, body, config=None):
    if config is None:
        config = load_config()
    email_log_path = os.path.join(config.logging.abs_results_dir, "email_log.jsonl")
    os.makedirs(os.path.dirname(email_log_path), exist_ok=True)

    record = {"to": to, "subject": subject, "body": body}
    with open(email_log_path, "a") as f:
        f.write(json.dumps(record) + "\n")

    return f"Email sent successfully to {to}."
