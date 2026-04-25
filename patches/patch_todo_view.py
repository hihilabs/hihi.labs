#!/usr/bin/env python3
"""
Patch app/Views/todo/view.php
Pass seperate_audio=true so recording-*.webm renders as inline <audio>.
"""
import os, sys

RISE_ROOT = os.environ.get("RISE_ROOT", os.getcwd())
TARGET = os.path.join(RISE_ROOT, "app/Views/todo/view.php")

OLD = 'echo view("includes/timeline_preview", array("files" => $files));'
NEW = 'echo view("includes/timeline_preview", array("files" => $files, "seperate_audio" => true));'

with open(TARGET, "r") as f:
    content = f.read()

if NEW in content:
    print(f"  already patched: {TARGET}")
    sys.exit(0)

if OLD not in content:
    print(f"ERROR: injection point not found in {TARGET}")
    sys.exit(1)

content = content.replace(OLD, NEW, 1)
with open(TARGET, "w") as f:
    f.write(content)
print(f"  patched: {TARGET}")
