import json
import requests
import time
import random

# Configuration
splunk_url = "https://localhost:8088"           
splunk_token = "xxxxxxxxx-xxxx-xxxx-xxxxx-xxxxxxxx"    # Your HEC token
splunk_index = "testing_index"
sourcetype = "_json"
log_file = "sample_logs.json"
hosts = ["host01", "host02", "endpoint01", "laptop-user", "dc01"]

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

headers = {
    "Authorization": f"Splunk {splunk_token}",
    "Content-Type": "application/json"
}

def send_log_to_splunk(event, host):
    payload = {
        "event": event,
        "host": host,
        "sourcetype": sourcetype,
        "index": splunk_index
    }
    # print("[DEBUG] Payload:", json.dumps(payload, indent=2))
    response = requests.post(
        f"{splunk_url}/services/collector",
        headers=headers,
        data=json.dumps(payload),
        verify=False
    )
    if response.status_code != 200:
        print(f"[!] Failed: {response.status_code} - {response.text}")
    else:
        print(f"[+] Sent: {event.get('Image', '[no Image]')}")

def main():
    with open(log_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                host = random.choice(hosts)
                send_log_to_splunk(event, host)
                time.sleep(0.2)
            except Exception as e:
                print(f"[!] Error processing log: {e}")

if __name__ == "__main__":
    main()
