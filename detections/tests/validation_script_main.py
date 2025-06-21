import os
import sys
import glob
import yaml
import json
from cerberus import Validator
from auth import get_session_key
from spl_validator import validate_spl
from spl_linter import lint_spl
from volume_testing import test_alert_volume


# === CONFIG LOAD ===
BASE_DIR = os.getcwd()
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SCHEMA_PATH = os.path.join(BASE_DIR, "detections", "tests", "rule_schema.yaml")
RULES_DIR = os.path.join(BASE_DIR, "detections", "rules")

with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

with open(SCHEMA_PATH, "r") as f:
    SCHEMA = yaml.safe_load(f)

v = Validator(SCHEMA)

# === RULE VALIDATOR ===
def validate_detection_rule(rule, config, headers):
    spl = rule.get("search", "")
    all_passed = True
    
    # === SPL Validation ===
    print(f"\n[>] Validating SPL: {spl[:60]}...")
    if not validate_spl(spl, config, headers):
        all_passed = False

    # === Lint Validation ===
    lint_issues = lint_spl(spl)
    if lint_issues:
        all_passed = False
        print("[!] SPL Linting Issues:")
        for issue in lint_issues:
            print(f"  - {issue}")

    # === ALERT VOLUME TESTING ===
    print("[>>] Running alert volume test over past 14 days...")
    volume = test_alert_volume(spl, config, headers)
    if volume is None:
        print("[!] Alert volume test could not complete")
        all_passed = False
    else:
        print(f"[i] Estimated alerts in last 14 days: {volume}")
        if volume == 0:
            print("[!] No alerts triggered — check logic/data")
            all_passed = False
        elif volume > 10:
            all_passed = False
            print("[!!] High volume — consider filtering or thresholds")
        else:
            print("[+] Alert volume looks reasonable")

    return all_passed

# === MAIN ===
def main():
    headers = get_session_key(CONFIG)
    valid_count = 0
    invalid_count = 0

    for file in glob.glob(os.path.join(RULES_DIR, "**/*.yaml"), recursive=True):
        with open(file, "r") as f:
            rule = yaml.safe_load(f)
        print(f"\n[>>] Validating rule: {file}")

        if not v.validate(rule):
            print("[!] Invalid YAML schema:")
            for field, errors in v.errors.items():
                print(f"  - {field}: {errors}")
            invalid_count += 1
            continue
        print("[+] YAML schema valid")

        if validate_detection_rule(rule, CONFIG, headers):
            valid_count += 1
        else:
            invalid_count += 1

    print(f"\n===== SUMMARY =====")
    print(f"[+] Valid rules: {valid_count}")
    print(f"[!] Invalid rules: {invalid_count}")

    if invalid_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
