#!/bin/bash
set -e
APP=/var/www/vhosts/communityplaylist.com/tokyo7.communityplaylist.com
PYTHON=$APP/venv/bin/python3
echo running collectstatic
$PYTHON $APP/manage.py collectstatic --noinput
echo running migrate
$PYTHON $APP/manage.py migrate --run-syncdb
echo reloading gunicorn
kill -HUP $(pgrep -f gunicorn.*tokyo7 | head -1)
HASH=$(cd $APP && git rev-parse --short HEAD 2>/dev/null || echo ?)
echo done commit: $HASH
