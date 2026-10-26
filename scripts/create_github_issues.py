"""Create GitHub issues from lumi_backlog_jira.csv using the GitHub CLI (gh).
Usage:  gh auth login   (once)
        python create_github_issues.py OWNER/REPO
Fill in GITHUB_USERS with each member's GitHub username first."""
import csv, os, subprocess, sys
GITHUB_USERS = {
    "Temur Erkinov": "",
    "Shohruh Mamatov": "",
    "Abdurahmon Abdurazzoqov": "",
    "Shamsiddinxoja Abduraximov": "",
}
repo = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(os.path.dirname(__file__), "..", "docs", "lumi_backlog_jira.csv"), encoding="utf-8")))
labels = {l for r in rows for l in r["Labels"].split()}
for l in labels:
    subprocess.run(["gh", "label", "create", l, "--repo", repo, "--force"], check=False)
for r in rows:
    body = f"{r['Description']}\n\n**Type:** {r['Issue Type']}  \n**Priority:** {r['Priority']}  \n**Story points:** {r['Story Points']}  \n**Sprint:** {r['Sprint']}"
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", r["Summary"], "--body", body]
    for l in r["Labels"].split():
        cmd += ["--label", l]
    user = GITHUB_USERS.get(r["Assignee"])
    if user:
        cmd += ["--assignee", user]
    subprocess.run(cmd, check=True)
    print("created:", r["Summary"])
