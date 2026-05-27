# apps/messaging/templates/

Untracked from git — messaging app templates that live inside the app
directory rather than the top-level templates/ folder.

## What is it
Django templates for the internal messaging / chat features:
- `messaging/thread.html` — individual message thread view

## Why untracked
These were added directly on VPS during a session that didn't get committed.
The main messaging templates (inbox.html etc.) are in top-level templates/messaging/
and ARE tracked. This subdirectory is the local-app-level override.

## To track
```bash
git add apps/messaging/templates/
git commit -m "track messaging app-level templates"
git push origin master
```
Safe to add — no secrets in HTML templates.
