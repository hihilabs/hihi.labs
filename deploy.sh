#!/bin/bash
# HiHi Labs — deploy script
# Run after any git commit that changes static files or Python code.
set -e

APP=/var/www/vhosts/communityplaylist.com/tokyo7.communityplaylist.com
cd 
source venv/bin/activate

echo → collectstatic...
python3 manage.py collectstatic --noinput

echo → migrate...
python3 manage.py migrate --run-syncdb

echo → reloading gunicorn...
kill -HUP 1988509

HASH=?
echo ✓ done — CSS ver: 
