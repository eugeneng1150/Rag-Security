from core.database import reset_db, inject_payload


def setup_attack(payload, target_employee_id=1, config=None):
    reset_db(config)
    inject_payload(target_employee_id, payload, config)
