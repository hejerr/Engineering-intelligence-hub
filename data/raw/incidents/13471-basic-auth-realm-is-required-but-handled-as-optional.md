# Incident Report: Basic auth `realm` is REQUIRED but handled as optional

**Source issue:** #13471 (https://github.com/fastapi/fastapi/issues/13471)
**Status:** closed
**Labels:** bug
**Reported:** 2025-03-09
**Resolved:** 2026-01-12
**Discussion comments:** 7

## Reported Problem

According to https://datatracker.ietf.org/doc/html/rfc7617#autoid-3 , specification of the `realm` parameter is REQUIRED, so making `realm` optional here

https://github.com/fastapi/fastapi/blob/643d2845de09a437b955a163ab25eb0887bfd0e1/fastapi/security/http.py#L195

and at related places, is misleading and makes it easy to create non-conforming APIs. It bit me when a Shelly device refused (rightfully) to authenticate against the API which was using the default (missing) `realm` behavior.

## Resolution

This issue was closed on 2026-01-12. See the linked GitHub issue and any
referenced pull requests at https://github.com/fastapi/fastapi/issues/13471 for the exact code change that resolved it.
