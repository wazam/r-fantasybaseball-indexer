#!/bin/sh
set -e

# uvicorn reads FORWARDED_ALLOW_IPS itself, before the app starts, and trusts every address only when the value
# is exactly *. So spaces come out here, since config.py's check ignores them too. An empty value would make
# uvicorn trust no proxy; unset, it uses its default, 127.0.0.1,::1, so an empty value means unset like every
# other setting.
value=$(printf '%s' "${FORWARDED_ALLOW_IPS-}" | tr -d ' \t')
if [ -z "$(printf '%s' "$value" | tr -d ',')" ]; then
    unset FORWARDED_ALLOW_IPS
else
    export FORWARDED_ALLOW_IPS="$value"
fi

exec "$@"
