#!/bin/sh
# Il router non deve ricevere il cookie del proxy: prova la map di nginx
set -eu
check() {
    got=$(curl -s -H "Cookie: $1" http://127.0.0.1:18080/)
    [ "$got" = "[$2]" ] || { echo "Cookie '$1': atteso '[$2]', ottenuto '$got'"; exit 1; }
}
check "__Host-openwisp-luci=abc" ""
check "__Host-openwisp-luci=abc; sysauth_https=s1" "sysauth_https=s1"
check "a=1; __Host-openwisp-luci=abc; sysauth_https=s1" "a=1; sysauth_https=s1"
check "a=1; __Host-openwisp-luci=abc" "a=1"
check "sysauth_https=s1" "sysauth_https=s1"
echo "map del cookie ok"
