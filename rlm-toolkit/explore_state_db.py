"""Check history.entries and jetski data in workspace storage."""

import sqlite3
import os
import json
from pathlib import Path

appdata = os.environ["APPDATA"]
# Use the latest workspace we found
ws_db = (
    Path(appdata)
    / "Antigravity"
    / "User"
    / "workspaceStorage"
    / "6e658e117cccadb590575224f146a97e"
    / "state.vscdb"
)

conn = sqlite3.connect(str(ws_db))
cursor = conn.cursor()

print("=== history.entries ===")
cursor.execute("SELECT value FROM ItemTable WHERE key = 'history.entries'")
row = cursor.fetchone()
if row and row[0]:
    try:
        data = json.loads(row[0])
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            # Look for entries
            entries = data.get("entries", [])
            print(f"Entries count: {len(entries)}")
            if entries:
                print(f"\nLast 3 entries:")
                for e in entries[-3:]:
                    print(f"  {json.dumps(e, indent=2)[:200]}...")
    except Exception as ex:
        print(f"Error: {ex}")
        print(f"Raw: {row[0][:300]}")

print("\n=== memento/antigravity.jetskiArtifactsEditor ===")
cursor.execute(
    "SELECT value FROM ItemTable WHERE key = 'memento/antigravity.jetskiArtifactsEditor'"
)
row = cursor.fetchone()
if row and row[0]:
    try:
        data = json.loads(row[0])
        print(f"Type: {type(data)}, Size: {len(row[0])} bytes")
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())[:10]}")
            # Print sample
            print(f"\nSample: {json.dumps(data, indent=2)[:500]}")
    except Exception as ex:
        print(f"Raw: {row[0][:300]}")

conn.close()
