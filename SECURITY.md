# Security policy

## Supported versions

Only the latest release receives security fixes.

| Version | Supported |
|---|---|
| latest 0.x | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Please do not open a public issue.** Report it privately through
[GitHub private vulnerability reporting](https://github.com/mikysal78/openwisp-luci/security/advisories/new)
(Security → Report a vulnerability).

Include, if possible: affected version, a description of the issue and its
impact, steps to reproduce or a proof of concept, and a suggested fix.

What to expect:

- acknowledgement within **7 days**;
- an assessment and, if confirmed, a fix and a new release as soon as
  possible (target: 30 days for high/critical issues);
- a [GitHub Security Advisory](https://github.com/mikysal78/openwisp-luci/security/advisories)
  published with the release; a **CVE** is requested through GitHub, which is a
  CVE Numbering Authority, when the issue warrants one;
- credit in the advisory, unless you prefer to stay anonymous.

## Scope

In scope: this package (the LuCI button, the single-use link, the proxy views
called by nginx) and the example nginx virtual host in `examples/ansible`.

Out of scope: OpenWISP itself, nginx, LuCI, uhttpd and the router firmware
(report those to their projects), and the documented known limits (see the
README, "Security"): the router certificate is not verified, and the router
pages share the site with OpenWISP when the proxy uses a subdomain of the same
domain.

## Hardening already in place

See the "Security" section of the [README](README.md#security): one origin per
router, single-use signed links bound to user, device and password, permission
and management IP checked again on every request, allowed networks for the
router address, proxy cookie never forwarded to the router.
