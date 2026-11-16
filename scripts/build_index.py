#!/usr/bin/env python3
"""Regenerates index.json from tools/*/manifest.json. Run it after changing any tool.

    python3 scripts/build_index.py           # write index.json
    python3 scripts/build_index.py --check   # exit 1 if index.json is out of date (used by CI)
"""
import hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
MAX = 200 * 1024 * 1024


def tool(folder):
    base = os.path.join(ROOT, "tools", folder)
    with open(os.path.join(base, "manifest.json"), encoding="utf-8") as f:
        m = json.load(f)
    for k in ("id", "name", "version"):
        if not m.get(k):
            sys.exit(f"tools/{folder}/manifest.json: missing \"{k}\"")
    if not ID.match(m["id"]):
        sys.exit(f"tools/{folder}: invalid id {m['id']!r}")
    if m["id"] != folder:
        sys.exit(f"tools/{folder}: folder name must equal the id {m['id']!r}")
    entry = m.get("entry", "index.html")
    if not os.path.isfile(os.path.join(base, entry)):
        sys.exit(f"tools/{folder}: entry page {entry} is missing")
    files = []
    for d, dirs, names in os.walk(base):
        dirs[:] = sorted(x for x in dirs if not x.startswith("."))
        for n in sorted(names):
            if n.startswith("."):
                continue
            p = os.path.join(d, n)
            data = open(p, "rb").read()
            files.append({
                "path": os.path.relpath(p, base).replace(os.sep, "/"),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
    if sum(f["size"] for f in files) > MAX:
        sys.exit(f"tools/{folder}: larger than 200 MB")
    out = {k: m[k] for k in ("id", "name", "description", "icon", "version", "author", "category", "minApp") if k in m}
    out["path"] = f"tools/{folder}"
    out["files"] = files
    return out


def build():
    folders = sorted(d for d in os.listdir(os.path.join(ROOT, "tools")) if os.path.isdir(os.path.join(ROOT, "tools", d)))
    tools = [tool(f) for f in folders]
    tools.sort(key=lambda t: t["name"].lower())
    return json.dumps({"format": 1, "tools": tools}, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    text = build()
    path = os.path.join(ROOT, "index.json")
    if "--check" in sys.argv:
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if current != text:
            sys.exit("index.json is out of date: run python3 scripts/build_index.py and commit it")
        print("index.json is up to date")
    else:
        open(path, "w", encoding="utf-8").write(text)
        print(f"wrote index.json ({text.count('\"path\": \"tools/')} tools)")
