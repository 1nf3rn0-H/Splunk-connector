import re

def lint_spl(spl):
    issues = []
    if "index=" not in spl:
        issues.append("Missing 'index=' clause.")
    if re.search(r"index=\*", spl):
        issues.append("Avoid 'index=*' - use specific indexes.")
    if re.search(r"sourcetype\\s*=\\s*\\*", spl):
        issues.append("Avoid 'sourcetype=*' - use specific sourcetypes.")
    if "stats count" not in spl and "table" not in spl and "eval" not in spl and "tstats" not in spl:
        issues.append("Query lacks stats/tstats/table/eval - may not produce fields.")
    if "| search " in spl:
        issues.append("Avoid post-filtering with '| search'. Prefer filtering earlier.")
    if "join" in spl:
        issues.append("Consider avoiding 'join' - it's costly. Use 'lookup' or 'append' if possible.")
    return issues
