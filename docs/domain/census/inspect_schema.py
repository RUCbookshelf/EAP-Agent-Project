"""DP-4 read-only schema inspection for the product essays table (no writes)."""
import sqlite3, sys, hashlib, os, json

DB = r"A:\EAP Agent Project\writing-feedback-mvp\data\writing_feedback.db"

con = sqlite3.connect(f"file:{DB.replace(chr(92), '/')}?mode=ro", uri=True)
cur = con.cursor()

print("sqlite_version:", sqlite3.sqlite_version)
print("integrity_check:", cur.execute("PRAGMA integrity_check").fetchone()[0])
print("journal_mode:", cur.execute("PRAGMA journal_mode").fetchone()[0])

tables = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
).fetchall()
print("\nTABLES:", [t[0] for t in tables])

for (t,) in tables:
    cols = cur.execute(f'PRAGMA table_info("{t}")').fetchall()
    print(f"\n== {t} ==")
    for c in cols:
        print(f"  {c[1]} ({c[2]}) notnull={c[3]} pk={c[5]}")

con.close()

# file provenance (read-only hash)
st = os.stat(DB)
h = hashlib.sha256()
with open(DB, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
print("\nDB sha256:", h.hexdigest())
print("DB size:", st.st_size, "mtime:", st.st_mtime)
