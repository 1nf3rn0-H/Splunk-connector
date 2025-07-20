import requests
from requests.auth import HTTPBasicAuth
import urllib3
from croniter import croniter
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SPLUNK_HOST = "https://localhost:8089"
USERNAME = "admin"
PASSWORD = "password"
MAX_CONCURRENCY = 3  # <-- Set your concurrency threshold here

def list_saved_searches_rest():
    url = f"{SPLUNK_HOST}/servicesNS/-/-/saved/searches?output_mode=json&count=0"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        verify=False
    )

    if response.status_code != 200:
        print(f"[!] Error: {response.status_code} - {response.text}")
        return []

    data = response.json()
    results = []
    for entry in data.get('entry', []):
        name = entry.get('name')
        app = entry.get('acl', {}).get('app')
        content = entry.get('content', {})

        # Add hypothetical attributes
        fidelity = round(random.uniform(0.0, 1.0), 2)
        criticality = random.randint(1, 4)

        results.append({
            'name': name,
            'app': app,
            'cron_schedule': content.get('cron_schedule'),
            'alert_type': content.get('alert_type'),
            'actions': content.get('actions'),
            'fidelity': fidelity,
            'criticality': criticality,
        })
    return results

def simulate_cron_times(cron_expr, hours=6):
    now = datetime.now().replace(second=0, microsecond=0)
    end = now + timedelta(hours=hours)
    times = []

    try:
        cron = croniter(cron_expr, now)
        while True:
            ts = cron.get_next(datetime)
            if ts > end:
                break
            times.append(ts)
    except Exception as e:
        print(f"[!] Invalid cron '{cron_expr}': {e}")
    return times

def build_concurrency_chart(schedule_data):
    concurrency = defaultdict(int)
    for ts_list in schedule_data.values():
        for ts in ts_list:
            concurrency[ts] += 1

    sorted_times = sorted(concurrency)
    counts = [concurrency[ts] for ts in sorted_times]

    time_labels = [ts.strftime("%H:%M") for ts in sorted_times]

    plt.figure(figsize=(16, 6))
    plt.plot(time_labels, counts, label='Concurrent Alerts', color='blue')
    plt.axhline(MAX_CONCURRENCY, color='red', linestyle='--', label=f'Max Concurrency = {MAX_CONCURRENCY}')
    plt.xticks(rotation=45, fontsize=8)
    plt.ylabel("Concurrent Alert Executions")
    plt.title("Splunk Alert Concurrency Simulation (Next 6 Hours)")
    plt.legend()
    plt.tight_layout()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    searches = list_saved_searches_rest()
    schedule_data = {}

    for s in searches:
        if (
            s['alert_type']
            and s['actions'] not in (None, '', 'None')
            and s['app'] == "search"
            and s['cron_schedule']
        ):
            print(f"Simulating for rule: {s['name']}, Fidelity: {s['fidelity']}, Criticality: {s['criticality']}")
            runs = simulate_cron_times(s['cron_schedule'])
            schedule_data[s['name']] = runs

    build_concurrency_chart(schedule_data)
