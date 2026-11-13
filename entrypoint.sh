#!/bin/sh
set -e

if [ ! -w /app/data ]; then
    echo "ERROR: /app/data isn't writable by uid $(id -u), gid $(id -g)." >&2
    echo "Either change the owner of your ./data directory (sudo chown -R $(id -u):$(id -g) ./data)," >&2
    echo "or set user: in compose.yaml to the uid:gid that owns it (ls -n shows it)." >&2
    exit 1
fi

# uvicorn reads FORWARDED_ALLOW_IPS itself, before the app starts. An empty value would make it trust no proxy;
# unset, it uses its default, 127.0.0.1,::1, so an empty value means unset like every other setting.
if [ -z "$(printf '%s' "${FORWARDED_ALLOW_IPS-}" | tr -d ' ,')" ]; then
    unset FORWARDED_ALLOW_IPS
fi

exec "$@"
