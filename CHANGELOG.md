# Changelog

## 0.3.1

- After the single-use login the proxy enters LuCI with a page that refreshes
  to `/cgi-bin/luci/` instead of an HTTP redirect. When the link comes from
  outside the site (an app, a chat), browsers treat the redirect as cross-site
  and do not send the `SameSite=Strict` cookies just set, so LuCI showed
  "session missing or expired". From the OpenWISP button it already worked.

## 0.3.0

- API for apps: `POST /api/v1/luci/device/<uuid>/link/` with the OpenWISP
  token (`Authorization: Bearer <token>`) returns the same single-use link as
  the button, after the same checks. Used by
  [openwisp-android](https://github.com/mikysal78/openwisp-android) to open
  LuCI from the phone. Include `openwisp_luci.api_urls` under `api/v1/` to
  enable it. Only the Bearer token is accepted (never the browser session), and
  a device the user cannot open answers 404 like a missing one.

## 0.2.0

- Optional automatic LuCI login for superusers (`OPENWISP_LUCI_AUTO_LOGIN`):
  OpenWISP uses the SSH connection it already has to the router to create a
  LuCI session for `OPENWISP_LUCI_AUTO_LOGIN_USER` (default `admin`, a
  dedicated user: root keeps its password) with the same ACLs rpcd would give
  that user at login, and hands it to the browser as the LuCI cookie on the router's own proxy host.
  No router password is stored on the server, the session id never reaches
  the OpenWISP logs. Other users, or anyone who wants to log in as another
  router user, get the usual LuCI login page. If the session cannot be created
  LuCI opens with its login page.

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
