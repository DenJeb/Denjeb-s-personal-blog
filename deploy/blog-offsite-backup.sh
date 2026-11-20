#!/bin/sh
set -eu

: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"

exec /usr/bin/rclone \
    --config /etc/rclone.conf \
    sync /var/www/Denjeb-s-personal-blog/backups/ "${RCLONE_REMOTE}:/blog-backups" \
    --delete-after
