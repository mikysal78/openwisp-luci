# Changelog

## 0.1.1

- The LuCI button is now in the tab bar of the device page, right after
  "Netconsole" when present, and still opens LuCI in a new tab. Without the tab
  bar (or without JavaScript) it stays among the object tools.

## 0.1.0

First release.

- LuCI button on the device page (object tools), for users who can change the
  device; disabled with an explanation when the management IP is missing or
  outside the allowed networks.
- Single-use signed link (60 seconds) to `<device uuid>.<proxy domain>`, then a
  signed `__Host-` cookie bound to user, device and password.
- `auth` view for nginx `auth_request`: checks user, permission, password,
  device and management IP on every request and returns the router address.
- "Access denied" page with a link back to the device in OpenWISP.
- Example Ansible role `luci_proxy` with the nginx virtual host; CI validates it
  and checks that the router never receives the proxy cookie.
- Italian translation.
