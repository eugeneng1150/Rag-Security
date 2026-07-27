#!/usr/bin/env python3
"""Initialize and verify the employee database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_config
from core.database import init_db, execute_query

config = load_config()

print("Initializing database...")
init_db(config)
print(f"Database created at: {config.database.abs_path}")

print("\n--- Public Table (employees) ---")
print(execute_query("SELECT * FROM employees LIMIT 5", config, role="finance"))

print("\n--- Private Table (employee_salary) ---")
print(execute_query("SELECT * FROM employee_salary LIMIT 5", config, role="finance"))

print("\n--- Row Counts ---")
print(f"Employees: {execute_query('SELECT COUNT(*) as count FROM employees', config, role='finance')}")
print(f"Salaries: {execute_query('SELECT COUNT(*) as count FROM employee_salary', config, role='finance')}")

print("\nDatabase setup complete.")
