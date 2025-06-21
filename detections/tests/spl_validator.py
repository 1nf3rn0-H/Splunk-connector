import requests

def validate_spl(spl_query, config, headers):
    data = {
        "search": f"search {spl_query}",
        "earliest_time": "-5m",
        "latest_time": "now",
        "output_mode": "json"
    }
    response = requests.post(
        f"{config['host']}/services/search/jobs/export",
        headers=headers,
        data=data,
        verify=False
    )
    if response.status_code != 200:
        print(f"[!] SPL SYNTAX ERROR:\n    {spl_query}\n    {response.text.strip()}")
        return False
    print(f"[+] SPL syntax valid")
    return True
