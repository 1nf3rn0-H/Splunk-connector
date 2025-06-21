import requests
import urllib3
import argparse
import json
import yaml
import os
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----- Config & Auth ----- #
def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r') as f:
        return json.load(f)

def get_session_key(base_url, username, password):
    login_url = f"{base_url}/services/auth/login"
    data = {"username": username, "password": password}
    response = requests.post(login_url, data=data, verify=False)
    if response.status_code != 200 or "<sessionKey>" not in response.text:
        raise Exception(f"Login failed: {response.text}")
    return "Splunk " + response.text.split("<sessionKey>")[1].split("</sessionKey>")[0]

def build_auth_header(config):
    if config.get("token"):
        return {"Authorization": f"Splunk {config['token']}"}
    elif config.get("username") and config.get("password"):
        return {"Authorization": get_session_key(config["host"], config["username"], config["password"])}
    else:
        raise ValueError("No valid authentication method found in config.")

# ----- Saved Search Operations ----- #
def toggle_saved_search(config, search_name, action, headers):
    encoded_name = requests.utils.quote(search_name)
    url = f"{config['host']}/servicesNS/admin/{config['app']}/saved/searches/{encoded_name}"
    data = {"disabled": "0" if action == "enable" else "1"}
    response = requests.post(url, headers=headers, data=data, verify=False)

    if response.status_code != 200:
        raise Exception(f"Failed to {action} saved search:\n{response.text}")

    print(f"[+] Successfully {action}d saved search: '{search_name}'")

def list_saved_searches(config, headers):
    url = f"{config['host']}/servicesNS/admin/{config['app']}/saved/searches?output_mode=json"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code != 200:
        raise Exception(f"Failed to retrieve saved searches:\n{response.text}")

    entries = response.json().get("entry", [])
    if not entries:
        print("[!] No saved searches found.")
        return

    print(f"\nSaved Searches in app '{config['app']}':")
    print("-" * 60)
    for entry in entries:
        name = entry.get("name")
        disabled = entry.get("content", {}).get("disabled", True)
        status = "DISABLED" if disabled else "ENABLED"
        print(f"[{status:<8}] {name}")
    print("-" * 60)
    print(f"[+] Total: {len(entries)}")

# ----- YAML Rule Support ----- #
def load_rule_yaml(rule_path):
    if not os.path.exists(rule_path):
        raise FileNotFoundError(f"Rule YAML file not found: {rule_path}")
    with open(rule_path, 'r') as f:
        return yaml.safe_load(f)

def create_saved_search_from_yaml(config, rule_data, headers):
    url = f"{config['host']}/servicesNS/admin/{config['app']}/saved/searches"

    # Fix prefixing logic
    search_query = rule_data["search"]
    if not search_query.strip().startswith(("search", "|", "tstats", "inputlookup", "from")):
        search_query = f"search {search_query}"

    data = {
        "name": rule_data["name"],
        "search": search_query,
        "cron_schedule": rule_data["cron"],
        "description": rule_data.get("description", ""),
        "dispatch.earliest_time": rule_data.get("earliest_time", "-5m"),
        "dispatch.latest_time": rule_data.get("latest_time", "now"),
        "is_scheduled": "1",
        "alert_type": rule_data.get("alert_type", "always"),
        "alert.track": "1" if rule_data.get("alert.track", True) else "0",
        "alert.severity": str(rule_data.get("alert.severity", 3)),
    }

    for key in rule_data:
        if key.startswith("action.") or key.startswith("alert.") or key in ["is_scheduled"]:
            data[key] = str(rule_data[key])

    response = requests.post(url, headers=headers, data=data, verify=False)

    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to create saved search:\n{response.text}")

    print(f"[+] Alert saved search '{rule_data['name']}' created successfully.")

    if rule_data.get("disabled", False):
        toggle_saved_search(config, rule_data["name"], "disable", headers)

# ----- Search Query Execution ----- #
def run_search_query(config, query, headers):
    search_url = f"{config['host']}/services/search/jobs"
    if not query.strip().startswith(("search", "|", "tstats", "inputlookup", "from")):
        query = f"search {query}"

    data = {
        "search": query,
        "earliest_time": "-24h",
        "latest_time": "now",
        "output_mode": "json"
    }

    print(f"[>] Starting async search job: {query}")
    response = requests.post(search_url, headers=headers, data=data, verify=False)
    if response.status_code != 201:
        raise Exception(f"Failed to create search job:\n{response.text}")

    sid = response.json().get("sid")
    if not sid:
        raise Exception("No SID returned for search job.")

    print(f"[+] Search SID: {sid}. Waiting for completion...")

    # Poll for job completion
    job_url = f"{config['host']}/services/search/jobs/{sid}"
    for _ in range(60):
        job_status = requests.get(job_url, headers=headers, verify=False, params={"output_mode": "json"}).json()
        if job_status["entry"][0]["content"]["isDone"]:
            print("[+] Search job completed.")
            break
        time.sleep(2)
    else:
        raise TimeoutError("Search job did not complete in time.")

    # Get results
    results_url = f"{job_url}/results"
    result_resp = requests.get(results_url, headers=headers, verify=False, params={"output_mode": "json", "count": 10})  # limit results
    if result_resp.status_code != 200:
        raise Exception(f"Failed to fetch results:\n{result_resp.text}")

    results = result_resp.json().get("results", [])
    if not results:
        print("[!] No results found.")
        return

    print(f"[+] Top {len(results)} results:\n")
    for row in results:
        print(json.dumps(row, indent=2))


# ----- Main Entry Point ----- #
def main():
    parser = argparse.ArgumentParser(description="Manage Splunk saved searches and run queries.")
    parser.add_argument("--config", default="config.json", help="Path to Splunk config JSON file")
    parser.add_argument("--action", choices=["list", "enable", "disable", "create", "search"], required=True)
    parser.add_argument("--search", help="Saved search name (for enable/disable)")
    parser.add_argument("--rule", help="Path to YAML file for creating a saved search")
    parser.add_argument("--query", help="Raw SPL to execute (for action=search)")

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        headers = build_auth_header(config)

        if args.action == "list":
            list_saved_searches(config, headers)
        elif args.action in ["enable", "disable"]:
            if not args.search:
                raise ValueError("You must provide --search for enable/disable.")
            toggle_saved_search(config, args.search, args.action, headers)
        elif args.action == "create":
            if not args.rule:
                raise ValueError("You must provide --rule for creating a saved search.")
            rule_data = load_rule_yaml(args.rule)
            create_saved_search_from_yaml(config, rule_data, headers)
        elif args.action == "search":
            if not args.query:
                raise ValueError("You must provide --query for search action.")
            run_search_query(config, args.query, headers)
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
