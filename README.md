# Rise Archived Status

A micro-addon for [RiseCRM](https://www.rise.biz/) that adds an **Archived** project status.

Built by [HiHi Labs](https://hihi.communityplaylist.com/portfolio.html).

## Problem

RiseCRM ships with: Open, Completed, Hold, Canceled, Prospect.  
There's no status for projects that were abandoned due to non-payment or scope collapse — but you still need them in the system for tax records, billing history, and reference.

Deleting them loses the paper trail. Marking them "Canceled" is misleading. **Archived** is the honest answer.

## Install

```bash
mysql -u USER -pPASS DBNAME < sql/up.sql
```

Or with env vars:
```bash
DB_HOST=localhost DB_USER=u DB_PASS=p DB_NAME=db bash install.sh
```

## What it adds

| id | key_name | title | icon |
|----|----------|-------|------|
| 6 | archived | Archived | archive |

The status appears in the RiseCRM project status dropdown immediately after install. No core files modified.

## Rollback

```bash
mysql -u USER -pPASS DBNAME < sql/down.sql
```

## License

MIT
