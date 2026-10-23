# openwisp-luci

🇬🇧 English · [🇮🇹 Italiano](README.it.md)

A **LuCI** button on the OpenWISP device page: it opens the web interface of
the router in a new tab, through an nginx proxy on the OpenWISP server. The
router does not need to be reachable from your browser, only from the server
(LAN, mesh, VPN, ZeroTier...).

```
browser ──https──▶ <device uuid>.luci.example.com (nginx on the OpenWISP server)
                     │ auth_request ──▶ Django: valid cookie? which router?
                     └──https──▶ management IP of the router (uhttpd, LuCI)
```

- **One host per router** (`<device uuid without dashes>.luci.example.com`):
  every router is a separate origin, so the cookies and the JavaScript served
  by one router never see those of the other routers.
- **Single-use link**: the button gives a signed token, valid for 60 seconds
  and usable once, bound to the user, the device and the user's password.
- **Every request is checked**: the user must still be active and allowed to
  change the device, the password must not have changed, the device must still
  exist and its management IP must be in the allowed networks.
- The router login is still needed: the proxy only decides *who may reach*
  LuCI, the router password protects the router.

Requirements: OpenWISP with openwisp-controller ≥ 1.1, nginx with the
`auth_request` module (included in the Debian and Ubuntu packages), a DNS
wildcard and a certificate for `*.luci.example.com`.

## Installation

1. **DNS**: a wildcard record that points to the OpenWISP server, for example
   `*.luci.example.com. CNAME openwisp.example.com.`
2. **Certificate** for `*.luci.example.com` (a `*.example.com` certificate
   does not cover it). With acme.sh and DNS-01:
   `acme.sh --issue --dns dns_nsupdate -d luci.example.com -d '*.luci.example.com'`
3. **OpenWISP**, with the [ansible-openwisp2](https://github.com/openwisp/ansible-openwisp2)
   role (full example in [`examples/ansible`](examples/ansible)):

   ```yaml
   openwisp2_extra_python_packages:
     - "openwisp-luci @ https://github.com/mikysal78/openwisp-luci/releases/download/v0.1.0/openwisp_luci-0.1.0-py3-none-any.whl"
   # after the apps that register or extend the device admin
   # (openwisp-monitoring, openwisp-netconsole...)
   openwisp2_extra_django_apps:
     - openwisp_luci
   openwisp2_extra_urls:
     - 'path("__openwisp_luci__/", include("openwisp_luci.urls"))'
   openwisp2_extra_django_settings_instructions:
     - |
       OPENWISP_LUCI_HOST = "{id}.luci.example.com"
       OPENWISP_LUCI_OPENWISP_URL = "https://openwisp.example.com"
       ALLOWED_HOSTS.append(".luci.example.com")
   ```

   and the `luci_proxy` role of the example for the nginx virtual host.
4. **Routers**: uhttpd must answer on the management IP from the server, on
   HTTPS (the default of OpenWrt with `luci-ssl` or `uhttpd` + `px5g`). If the
   management interface is in a firewall zone with `input REJECT` (e.g. `wan`),
   allow TCP 443 from the server only:

   ```json
   {"config_name": "rule", "config_value": "allow_luci_openwisp", "name": "Allow-LuCI-OpenWISP",
    "src": "wan", "src_ip": "192.0.2.10", "proto": "tcp", "dest_port": "443", "target": "ACCEPT"}
   ```

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `OPENWISP_LUCI_HOST` | `None` | Host of the proxy, `{id}` becomes the device UUID without dashes. `None` hides the button. |
| `OPENWISP_LUCI_ALLOWED_NETWORKS` | private IPv4 + `fc00::/7` | Networks where the management IP may be. Narrow it to your network (e.g. `["10.27.0.0/16"]`). |
| `OPENWISP_LUCI_TOKEN_AGE` | `60` | Seconds of validity of the single-use link. |
| `OPENWISP_LUCI_SESSION_AGE` | `14400` | Seconds of validity of the proxy cookie; then the button must be used again. |
| `OPENWISP_LUCI_SUPERUSER_ONLY` | `False` | Only superusers see and use the button. |
| `OPENWISP_LUCI_OPENWISP_URL` | `None` | OpenWISP address, for the link on the "access denied" page. |

Every opening is logged (logger `openwisp_luci`, level INFO) with user, device
and router IP.

## Security

- **Who**: staff users with the `change_device` permission who manage the
  organization of the device, or superusers. The button and the views check it
  again on every request.
- **Where**: the management IP is declared by the router itself, so a
  compromised router could point it anywhere. The proxy refuses loopback,
  link-local, multicast and reserved addresses, and every address outside
  `OPENWISP_LUCI_ALLOWED_NETWORKS`. The scheme and port are fixed in nginx.
- **Cookie**: `__Host-openwisp-luci`, signed, `Secure`, `HttpOnly`,
  `SameSite=Strict`, valid only on the host of its device. nginx removes it
  before forwarding the request, so the router never receives it.
- **Token in the URL**: single use, 60 seconds, not written in the nginx access
  log, `Referrer-Policy: no-referrer`.
- **Router traffic** stays encrypted up to the router (HTTPS). The router
  certificate is self-signed and is not verified.
- **Same site**: the router pages are served on a subdomain of the same
  domain as OpenWISP. Django rejects cross-origin POSTs by checking the
  `Origin` header, but a subdomain can set cookies for the parent domain. Name
  the OpenWISP session cookie with the `__Host-` prefix, which subdomains
  cannot set or overwrite:

  ```python
  SESSION_COOKIE_NAME = "__Host-sessionid"  # logs everybody out once
  ```

  If you can, use a separate domain for the proxy (e.g.
  `{id}.luci.example.net`).

Report vulnerabilities privately: see [SECURITY.md](SECURITY.md).

## Development

```sh
pip install pytest "django~=5.2.0" ruff
pytest
ruff check . && ruff format --check .
```

CI also validates the example nginx virtual host and checks that the router
never receives the proxy cookie.

## License

GPL-3.0-or-later.
