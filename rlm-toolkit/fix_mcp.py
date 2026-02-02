"""Fix corrupted line in mcp_tools_v2.py"""
import re

f = r"rlm_toolkit\memory_bridge\mcp_tools_v2.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

# Find and fix the corrupted line
old = '        # TEMP: Early return to test MCP hang`n        return {"status": "test", "message": "Early return for debugging"}`n        try:`n            # Import extractors (lazy to avoid circular imports)\r\n            import sys'

new = '''        # TEMP: Early return to test MCP hang
        return {"status": "test", "message": "Early return for debugging"}
        
        try:
            # Import extractors (lazy to avoid circular imports)
            import sys'''

content = content.replace(old, new)

with open(f, "w", encoding="utf-8") as file:
    file.write(content)

print("Fixed!")
