import os
from cerberus import Validator
import yaml
import glob

BASE_DIR = os.getcwd()
SCHEMA_PATH = os.path.join(BASE_DIR, "detections", "tests", "rule_schema.yaml")

with open(SCHEMA_PATH, "r") as f:
    schema = yaml.safe_load(f)

v = Validator(schema)

def validate_rule(file_path):
    with open(file_path, "r") as f:
        rule = yaml.safe_load(f)
    if v.validate(rule):
        print(f"[✓] VALID: {file_path}")
    else:
        print(f"[✗] INVALID: {file_path}")
        for field, errors in v.errors.items():
            print(f"  - {field}: {errors}")

if __name__ == "__main__":
    rules_dir = os.path.join(BASE_DIR, "detections", "rules")
    matched = False
    for file in glob.glob(os.path.join(rules_dir, "**/*.yaml"), recursive=True):
        matched = True
        validate_rule(file)
    if not matched:
        print("[!] No YAML rule files found under: rules/")
