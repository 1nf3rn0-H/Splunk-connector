import splunklib.client as client
import splunklib.results as results

# Splunk connection details
HOST = "localhost"
PORT = 8089
USERNAME = "admin"
PASSWORD = "password"  # Replace with your actual password
APP = "search"

# Connect to Splunk
service = client.connect(
    host=HOST,
    port=PORT,
    username=USERNAME,
    password=PASSWORD,
    app=APP,
    scheme="https"  # Use "http" if not using SSL
)


def getRules():
# Get all saved searches
    saved_searches = service.saved_searches
    alerts = []

    # Loop through and filter alerts (not alert_type="always")
    for saved_search in saved_searches:
        if (saved_search.content.get("alert_type") and saved_search.content["alert_type"] != "always"):
            alerts.append({
                "name": saved_search.name,
                "alert_type": saved_search.content.get("alert_type"),
                "search": saved_search.content.get("search"),
                "disabled": saved_search.content.get("disabled", False),
                "cron": saved_search.content.get("cron_schedule"),
                "severity": saved_search.content.get("alert.severity")
            })
    return alerts


def pushRule(search_name, search_query, cron, desc):
    # Create as scheduled alert
    if search_name not in service.saved_searches:
        alert = service.saved_searches.create(
            name=search_name,
            search=search_query,
            is_scheduled=True,
            cron_schedule=cron,       
            alert_type="number of events",     
            alert_comparator="greater than",
            alert_threshold="0",               
            actions="",                        
            description=desc
        )
        print(f"Alert '{search_name}' created.")
    else:
        print(f"Alert '{search_name}' already exists.")





# --------------------------------------------------------
rule_name = "New Rule"
rule = """
index=windows EventCode=4625
    | stats count by src_ip
    | where count > 10
    | collect index=my_alerts marker="custom_alert"
"""
cron="*/50 * * * *"
description = "A new rule which saves it to custom index"




pushRule(search_name=rule_name, search_query=rule, cron=cron, desc=description)
alerts = getRules()

# Display the alerts
print("Saved Alerts:")
for alert in alerts:
    print("-" * 40)
    for key, value in alert.items():
        print(f"{key}: {value}")

