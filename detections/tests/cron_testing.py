import requests
import urllib3
import json
import os
from datetime import datetime, timedelta
from croniter import croniter
import matplotlib.pyplot as plt
from collections import defaultdict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def get_scheduled_searches(config, headers):
    url = f"{config['host']}/servicesNS/admin/{config['app']}/saved/searches?output_mode=json&count=0"
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve saved searches:\n{response.text}")
    
    entries = response.json().get("entry", [])
    searches = []
    
    for entry in entries:
        content = entry.get("content", {})
        if not content.get("is_scheduled", False):
            continue
        searches.append({
            "name": entry.get("name"),
            "cron": content.get("cron_schedule", None),
            "disabled": content.get("disabled", True)
        })
    return searches

def simulate_cron_runs(searches):
    now = datetime.now()
    end_time = now + timedelta(hours=24)
    run_map = defaultdict(int)

    for s in searches:
        if not s["cron"] or s["disabled"]:
            continue
        try:
            itr = croniter(s["cron"], now)
            while True:
                run_time = itr.get_next(datetime)
                if run_time > end_time:
                    break
                rounded_time = run_time.replace(second=0, microsecond=0)
                run_map[rounded_time] += 1
        except Exception as e:
            print(f"[!] Invalid cron for {s['name']}: {s['cron']}")
    
    return run_map

def get_max_concurrent_limit(config, headers):
    url = f"{config['host']}/servicesNS/nobody/search/configs/conf-limits/search?output_mode=json"
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code != 200:
        print("[!] Could not retrieve limits.conf. Using default max concurrency of 5.")
        return 5

    entries = response.json().get("entry", [])
    for entry in entries:
        content = entry.get("content", {})
        if "max_searches_per_cpu" in content:
            max_per_cpu = int(content["max_searches_per_cpu"])
            num_cpus = 4  # You could fetch this from server/info dynamically
            return max_per_cpu * num_cpus

    print("[!] max_searches_per_cpu not found in limits.conf. Using default of 5.")
    return 5

def plot_run_map(run_map, hard_limit=5, soft_limit=None, save_path=None):
    times = sorted(run_map.keys())
    counts = [run_map[t] for t in times]

    plt.figure(figsize=(14, 6))
    plt.plot(times, counts, marker='o', linestyle='-', color='blue', label='Scheduled Search Count')
    plt.fill_between(times, counts, alpha=0.2, color='blue')

    plt.axhline(y=hard_limit, color='red', linestyle='--', linewidth=2, label=f'Hard Limit ({hard_limit})')
    if soft_limit:
        plt.axhline(y=soft_limit, color='orange', linestyle='--', linewidth=2, label=f'Soft Limit ({soft_limit})')

    over_hard = [t for t in times if run_map[t] > hard_limit]
    if over_hard:
        plt.scatter(over_hard, [run_map[t] for t in over_hard], color='red', label='Over Hard Limit', zorder=5)

    over_soft = [t for t in times if run_map[t] > soft_limit]
    if over_soft:
        plt.scatter(over_soft, [run_map[t] for t in over_soft], color='orange', label='Over Soft Limit', zorder=5)

    plt.title("Concurrent Scheduled Searches Over Next 24 Hours")
    plt.xlabel("Time")
    plt.ylabel("Concurrent Search Count")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        print(f"[+] Chart saved to {save_path}")
    else:
        plt.show()

    plt.close()

def analyze_scheduled_searches(config_path: str):
    config = load_config(config_path)
    headers = build_auth_header(config)
    searches = get_scheduled_searches(config, headers)
    run_map = simulate_cron_runs(searches)
    hard_limit = get_max_concurrent_limit(config, headers)
    soft_limit = int(hard_limit * 0.8)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join("Pushes", f"scheduled_search_load_{timestamp}.png")

    plot_run_map(run_map, hard_limit=hard_limit, soft_limit=soft_limit, save_path=save_path)
