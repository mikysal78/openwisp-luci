"""Genera la configurazione nginx dell'esempio per i controlli della CI.

Uso: python ci/nginx_check.py <directory di uscita>
Scrive nginx.conf (che include il vhost di openwisp-luci e un server di prova
che restituisce il Cookie che arriverebbe al router) e un certificato
autofirmato.
"""

import os
import re
import subprocess
import sys

import jinja2

out = os.path.abspath(sys.argv[1])
os.makedirs(out, exist_ok=True)
subprocess.run(
    [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-days",
        "1",
        "-subj",
        "/CN=ci",
        "-keyout",
        os.path.join(out, "key.pem"),
        "-out",
        os.path.join(out, "cert.pem"),
    ],
    check=True,
    capture_output=True,
)
env = jinja2.Environment(loader=jinja2.FileSystemLoader("examples/ansible/roles/luci_proxy/templates"))
env.filters["regex_escape"] = re.escape
vhost = env.get_template("openwisp-luci.conf.j2").render(
    ansible_managed="ci",
    luci_proxy_domain="luci.example.com",
    luci_proxy_ssl_cert=os.path.join(out, "cert.pem"),
    luci_proxy_ssl_key=os.path.join(out, "key.pem"),
    luci_proxy_uwsgi_socket="unix:%s/uwsgi.sock" % out,
    luci_proxy_router_scheme="https",
    luci_proxy_max_body_size="64m",
    luci_proxy_ipv6=False,
)
vhost = vhost.replace("include uwsgi_params;", "include /etc/nginx/uwsgi_params;")
vhost = vhost.replace("/var/log/nginx/", out + "/").replace("listen 443 ssl;", "listen 127.0.0.1:18443 ssl;")
with open(os.path.join(out, "openwisp-luci.conf"), "w") as f:
    f.write(vhost)
with open(os.path.join(out, "nginx.conf"), "w") as f:
    f.write(
        """
pid %(out)s/nginx.pid;
error_log %(out)s/error.log;
events {}
http {
    access_log %(out)s/access.log;
    client_body_temp_path %(out)s/tmp;
    include /etc/nginx/mime.types;
    include %(out)s/openwisp-luci.conf;
    server {
        listen 127.0.0.1:18080;
        location / { return 200 "[$openwisp_luci_router_cookie]"; }
    }
}
"""
        % {"out": out}
    )
print(out)
