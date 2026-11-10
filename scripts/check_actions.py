"""Fail if the pinned reusable actions' documented interfaces drift."""
from urllib.request import urlopen, Request
import re
import sys

ACTIONS = [
    ("vhick/Portable-Package-Builder", "v1.0.0",
     {"source-dir", "output-dir", "engine", "running-exe", "timeout-seconds", "package-revision", "official-tool-url", "official-tool-sha256"},
     {"installer-file", "installer-sha256", "app-id", "app-version"}),
    ("vhick/portable-release-publisher", "v1.1.1",
     {"files", "tag", "release-title", "tag-prefix", "keep-releases", "prune", "dry-run"}, set()),
]
for repo, tag, input_names, output_names in ACTIONS:
    raw = f"https://raw.githubusercontent.com/{repo}/{tag}/action.yml"
    with urlopen(Request(raw, headers={"User-Agent": "wmrai-builder-b1r1"}), timeout=40) as stream:
        text = stream.read().decode("utf-8-sig")
    # Exact field names at column two (not comments, descriptions or example uses).
    ins = set(re.findall(r"^  ([\w-]+):\s*$", text.split("inputs:", 1)[1].split("outputs:", 1)[0].split("runs:", 1)[0], re.M))
    outs = set(re.findall(r"^  ([\w-]+):\s*$", text.split("outputs:", 1)[1].split("runs:", 1)[0], re.M)) if "outputs:" in text else set()
    if not input_names <= ins or not output_names <= outs:
        raise RuntimeError(f"Action interface changed: {repo}@{tag}; inputs={ins}, outputs={outs}")
    if "using: composite" not in text:
        raise RuntimeError(f"Action is no longer composite: {repo}@{tag}")
    print(f"SOURCE-INSPECTED {repo}@{tag} inputs={sorted(ins)} outputs={sorted(outs)}")
