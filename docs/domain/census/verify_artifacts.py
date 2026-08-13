"""Post-run verification: JSON parse, handoff schema validation, DB immutability."""
import hashlib
import json
import os
import sqlite3

WORKTREE = r"A:\EAP Agent Project\worktrees\l2-writing"
DB_PATH = r"A:\EAP Agent Project\writing-feedback-mvp\data\writing_feedback.db"
PINNED_DB_SHA = "20c609ee0a091dce22114adb08233081993c517dba50c854fe163fa0b16b1d0c"

files = [
    r"docs\domain\census\L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json",
    r"docs\domain\D-22_legacy_genre_mapping_manifest.v1.0.0.qualified.json",
    r"docs\domain\L2_VALIDITY_V1_DISPOSITION.json",
    r"handoff.L2-D22-CENSUS-AND-V1.json",
]

ok = True
for rel in files:
    p = os.path.join(WORKTREE, rel)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    print("JSON OK:", rel, "| keys:", len(data))

# schema validation
schema_path = r"A:\EAP Agent Project\program-control\schemas\handoff.schema.json"
with open(os.path.join(WORKTREE, r"handoff.L2-D22-CENSUS-AND-V1.json"), encoding="utf-8") as f:
    handoff = json.load(f)
with open(schema_path, encoding="utf-8") as f:
    schema = json.load(f)

required = schema["required"]
missing = [k for k in required if k not in handoff]
extra = [k for k in handoff if k not in schema["properties"]]
enum_checks = []
if handoff["owner"] not in schema["properties"]["owner"]["enum"]:
    enum_checks.append("owner")
if handoff["verdict"] not in schema["properties"]["verdict"]["enum"]:
    enum_checks.append("verdict")
if handoff["gate_authority"] is not None and handoff["gate_authority"] not in schema["properties"]["gate_authority"]["enum"]:
    enum_checks.append("gate_authority")
if handoff["repair_owner"] is not None and handoff["repair_owner"] not in schema["properties"]["repair_owner"]["enum"]:
    enum_checks.append("repair_owner")
import re
sha_ok = all(re.fullmatch(r"[0-9a-f]{40}", handoff[k]) for k in ("starting_sha", "final_sha"))
print("handoff required missing:", missing)
print("handoff extra keys:", extra)
print("handoff enum failures:", enum_checks)
print("handoff sha pattern ok:", sha_ok)
for t in handoff["tests"]:
    assert t["result"] in ("PASS", "FAIL", "SKIP", "NOT_RUN"), t
print("test result enums OK")
if missing or extra or enum_checks or not sha_ok:
    ok = False

# DB immutability
h = hashlib.sha256()
with open(DB_PATH, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
db_sha = h.hexdigest()
print("DB sha256 now:", db_sha)
print("DB sha256 pinned:", PINNED_DB_SHA)
print("DB unchanged:", db_sha == PINNED_DB_SHA)
if db_sha != PINNED_DB_SHA:
    ok = False

# read-only re-query smoke check
con = sqlite3.connect(f"file:{DB_PATH.replace(os.sep, '/')}?mode=ro", uri=True)
print("row count re-check:", con.execute("SELECT COUNT(*) FROM essays").fetchone()[0])
con.close()

print("ALL VERIFICATIONS PASS" if ok else "VERIFICATION FAILURES PRESENT")
