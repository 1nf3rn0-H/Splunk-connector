import requests

def validate_spl(spl_query, config, headers):
    search_str = f"search {spl_query}"

    # === First try: /parser endpoint ===
    parser_url = f"{config['host']}/services/search/parser"
    parser_data = {
        "q": search_str,
        "output_mode": "json"
    }

    try:
        parser_resp = requests.post(
            parser_url,
            headers=headers,
            data=parser_data,
            verify=False
        )

        if parser_resp.status_code == 200:
            payload = parser_resp.json()
            if "messages" in payload and payload["messages"]:
                print(f"[!] SPL Parser Issues:")
                for msg in payload["messages"]:
                    print(f"  - {msg.get('text', 'Unknown error')}")
                return False
            print(f"[+] SPL syntax valid (via parser)")
            return True
        if parser_resp.status_code == 400:
            try:
                payload = parser_resp.json()
                print(f"[!] SPL Parser Error:")
                for msg in payload.get("messages", []):
                    print(f"  - {msg.get('text', 'Unknown error')}")
            except Exception:
                print(f"[!!] SPL returned 400 Bad Request and could not be parsed.")
            return False

        else:
            print(parser_resp.status_code)
            print("[!] Parser endpoint failed or inaccessible, falling back to job export...")
    except Exception as e:
        print(f"[!] Exception during parser validation: {e}")
        print("[!] Falling back to job export...")

    # === Fallback: /jobs/export ===
    export_url = f"{config['host']}/services/search/jobs/export"
    export_data = {
        "search": search_str,
        "earliest_time": "-5m",
        "latest_time": "now",
        "output_mode": "json"
    }

    try:
        export_resp = requests.post(
            export_url,
            headers=headers,
            data=export_data,
            verify=False
        )
        if export_resp.status_code == 200:
            content = export_resp.text.strip()
            if "Error in" in content or "Unable to" in content:
                print(f"[!] SPL Error returned from export:\n  {content[:200]}...")
                return False
            print(f"[+] SPL syntax valid (via export fallback)")
            return True
        else:
            print(f"[!] SPL Export HTTP Error:\n  {export_resp.text.strip()}")
            return False
    except Exception as e:
        print(f"[!!] SPL validation failed during export fallback: {e}")
        return False
