import requests
import json

def test_alert_volume(spl, config, headers, earliest="-14d@d", latest="now"):
    url = f"{config['host']}/services/search/jobs/export"

    wrapped_spl = spl.strip()
    if not wrapped_spl.lower().startswith("search "):
        wrapped_spl = f"search {wrapped_spl}"
    wrapped_spl += " | stats count"

    # print(f"[DEBUG] Query: {wrapped_spl}")

    data = {
        "search": wrapped_spl,
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json"
    }

    try:
        response = requests.post(url, headers=headers, data=data, verify=False)

        # print(f"[DEBUG] HTTP Status: {response.status_code}")
        if response.status_code != 200:
            # print(f"[DEBUG] Response text: {response.text}")
            return None

        for line in response.iter_lines():
            if line:
                try:
                    result = json.loads(line.decode("utf-8"))
                    count = int(result.get("result", {}).get("count", 0))
                    return count
                except Exception as e:
                    # print(f"[DEBUG] Failed to parse line: {e}")
                    continue

        # print("[DEBUG] No valid lines returned")
        return None

    except Exception as e:
        print(f"[!] Exception during volume test: {e}")
        return None
