import requests
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def get_session_key(config):
    if config.get("token"):
        return {"Authorization": f"Bearer {config['token']}"}
    login_url = f"{config['host']}/services/auth/login"
    response = requests.post(login_url, data={
        "username": config["username"],
        "password": config["password"]
    }, verify=False)
    if response.status_code != 200:
        raise Exception("[!] Login failed.")
    key = response.text.split("<sessionKey>")[1].split("</sessionKey>")[0]
    return {"Authorization": f"Splunk {key}"}
