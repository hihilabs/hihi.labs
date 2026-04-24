#!/usr/bin/env bash
# Rise Archived Status — install
# Usage: DB_HOST=localhost DB_USER=u DB_PASS=p DB_NAME=db bash install.sh
set -e

ADDON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ]; then
    echo "Run manually:"
    echo "  mysql -u USER -pPASS DBNAME < $ADDON_DIR/sql/up.sql"
    exit 0
fi

mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$ADDON_DIR/sql/up.sql"
echo "◉ Archived status installed."
