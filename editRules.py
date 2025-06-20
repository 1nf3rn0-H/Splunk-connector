import splunklib.client as client
import argparse
import os
from getpass import getpass
from tabulate import tabulate


def connect_splunk(host, port, username, password, app="search", scheme="https"):
    return client.connect(
        host=host,
        port=port,
        username=username,
        password=password,
        app=app,
        scheme=scheme
    )


def list_alerts(service, only_enabled=False, search_filter=None):
    alerts = []
    for saved_search in service.saved_searches:
        if saved_search.content.get("alert_type") and saved_search.content["alert_type"] != "always":
            if search_filter and search_filter.lower() not in saved_search.name.lower():
                continue

            # conversion from string to boolean
            disabled_val = saved_search.content.get("disabled", "0") in ("1", 1, True)

            if only_enabled and disabled_val:
                continue

            alerts.append([
                saved_search.name,
                saved_search.content.get("alert_type"),
                saved_search.content.get("search")[:60] + "...",
                saved_search.content.get("cron_schedule"),
                saved_search.content.get("alert.severity"),
                "Yes" if not disabled_val else "No",
                saved_search.content.get("disabled")  # just for debugging
            ])
    print(tabulate(alerts, headers=["Name", "Type", "Query", "Cron", "Severity", "Enabled", "Raw disabled"]))




def push_alert(service, name, query, cron, desc):
    if name in service.saved_searches:
        print(f"[!] Alert '{name}' already exists.")
        return
    service.saved_searches.create(
        name=name,
        search=query,
        is_scheduled=True,
        cron_schedule=cron,
        alert_type="number of events",
        alert_comparator="greater than",
        alert_threshold="0",
        actions="",  # SPL handles output
        alert_digest_mode=False,
        description=desc
    )
    print(f"[+] Alert '{name}' created successfully.")


def delete_alert(service, name):
    if name in service.saved_searches:
        service.saved_searches[name].delete()
        print(f"[-] Alert '{name}' deleted.")
    else:
        print(f"[!] Alert '{name}' not found.")


def toggle_alert(service, name, disable=True):
    if name in service.saved_searches:
        alert = service.saved_searches[name]
        alert.update({"disabled": str(disable).lower()})
        print(f"[~] Alert '{name}' {'disabled' if disable else 'enabled'}.")
    else:
        print(f"[!] Alert '{name}' not found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Splunk Scheduled Alert Manager")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8089)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", help="Splunk password (optional, will prompt if not provided)")

    parser.add_argument("--list", action="store_true", help="List all scheduled alerts")
    parser.add_argument("--push", action="store_true", help="Push a new alert")
    parser.add_argument("--delete", metavar="ALERT_NAME", help="Delete an alert")
    parser.add_argument("--disable", metavar="ALERT_NAME", help="Disable an alert")
    parser.add_argument("--enable", metavar="ALERT_NAME", help="Enable an alert")

    parser.add_argument("--name", help="Alert name")
    parser.add_argument("--query", help="SPL query for alert")
    parser.add_argument("--cron", help="Cron schedule")
    parser.add_argument("--desc", default="Pushed via CLI", help="Description for alert")
    parser.add_argument("--only-enabled", action="store_true", help="List only enabled alerts")
    parser.add_argument("--search", metavar="FILTER", help="Filter alert names")

    args = parser.parse_args()

    if not args.password:
        args.password = getpass("Splunk password: ")

    service = connect_splunk(args.host, args.port, args.user, args.password)

    if args.list:
        list_alerts(service, only_enabled=args.only_enabled, search_filter=args.search)

    elif args.push:
        if not all([args.name, args.query, args.cron]):
            print("[!] --name, --query, and --cron are required for --push")
        else:
            push_alert(service, args.name, args.query, args.cron, args.desc)

    elif args.delete:
        delete_alert(service, args.delete)

    elif args.disable:
        toggle_alert(service, args.disable, disable=True)

    elif args.enable:
        toggle_alert(service, args.enable, disable=False)

    else:
        parser.print_help()
