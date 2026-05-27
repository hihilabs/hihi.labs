# tldraw_src/

Untracked from git (node_modules too large to commit).

## What is it
TLDraw whiteboard integration — likely the frontend source for the `whiteboards`
app (whiteboards_whiteboard table exists in DB). node_modules is the npm install.

## Status
- DB table `whiteboards_whiteboard` exists with data
- Source app code (`apps/whiteboards/`) was deleted with the other CRM apps
- This directory is the JS/React side — the Django side needs rebuilding

## Next steps
1. Rebuild `apps/whiteboards/` (similar pattern to clients/proposals)
2. Check if there's a built bundle somewhere (tldraw_src/dist/ ?)
3. Wire back into urls.py + nav

## To rebuild the Django app
Same approach as the CRM apps: check DB schema, write models/views/urls,
fake-migrate (table already exists).

```bash
sqlite3 db.sqlite3 'PRAGMA table_info(whiteboards_whiteboard)'
```
