import splunklib.client as client
import os

def get_admin_max_concurrent_saved_searches(
    host="localhost",
    port=8089,
    username="admin",
    password="password",
    scheme="https"
):
    # Connect to Splunk
    service = client.connect(
        host=host,
        port=port,
        username=username,
        password=password,
        scheme=scheme
    )

    # Get general limits
    search_settings = service.confs.get('limits', namespace='search')
    cpu_count = os.cpu_count() or 4
    max_searches_per_cpu = int(search_settings.get('max_searches_per_cpu', 1))
    base_max_searches = int(search_settings.get('base_max_searches', 6))
    max_scheduled_percentage = int(search_settings.get('max_searches_perc', 50))

    max_system_searches = max(cpu_count * max_searches_per_cpu, base_max_searches)
    max_scheduled_concurrent = int((max_system_searches * max_scheduled_percentage) / 100)

    # Get admin role quota
    for role in service.roles:
        role.refresh()
        if role.name == "admin":
            sched_quota = int(role.content.get('scheduleSearchJobsQuota', 0))
            effective_sched = min(max_scheduled_concurrent, sched_quota) if sched_quota else max_scheduled_concurrent
            return effective_sched

    # If admin role not found
    return None

# Example usage
if __name__ == "__main__":
    max_sched = get_admin_max_concurrent_saved_searches()
    if max_sched is not None:
        print(f"[=] Admin max concurrent saved searches: {max_sched}")
    else:
        print("[!] Admin role not found or no value computed.")
