#!/bin/bash
# gm-site-art.sh - show the official color map for an adventure site (a file:// link).
# Usage:  bash tools/gm-site-art.sh "Weatherstone"     # link for one site
#         bash tools/gm-site-art.sh                      # list all mapped sites
source "$(dirname "$0")/common.sh"
CDIR=$(get_campaign_dir)
[ -z "$CDIR" ] && { echo "No active campaign."; exit 1; }
REG="$CDIR/site-images.json"
[ -f "$REG" ] || { echo "No site-images.json in $CDIR"; exit 1; }
$PYTHON_CMD - "$CDIR" "$REG" "$1" <<'PY'
import json, sys, os
cdir, reg = sys.argv[1], sys.argv[2]
q = sys.argv[3] if len(sys.argv) > 3 else ""
d = json.load(open(reg)); sites = d.get("sites", {})
def link(rel):
    p = os.path.abspath(os.path.join(cdir, rel))
    return "file:///" + p.replace("\\", "/").lstrip("/")
if not q:
    print("Mapped adventure-site maps:")
    for k, v in sites.items():
        print(f"  {k}: {link(v)}")
    if d.get("world_map"):
        print(f"  [World Map]: {link(d['world_map'])}")
    sys.exit(0)
ql = q.lower().strip()
hit = [k for k in sites if ql == k.lower()] or [k for k in sites if ql in k.lower()]
if hit:
    print(link(sites[hit[0]]))
else:
    print(f"No mapped art for '{q}'. Known sites: {', '.join(sites)}")
    sys.exit(2)
PY
