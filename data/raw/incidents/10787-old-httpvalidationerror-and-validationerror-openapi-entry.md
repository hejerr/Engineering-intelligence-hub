# Incident Report: Old `HTTPValidationError` and `ValidationError` OpenAPI entry

**Source issue:** #10787 (https://github.com/fastapi/fastapi/issues/10787)
**Status:** closed
**Labels:** bug
**Reported:** 2023-12-16
**Resolved:** 2026-02-04
**Discussion comments:** 7

## Reported Problem

### Privileged issue

- [X] I'm @tiangolo or he asked me directly to create an issue here.

### Issue Content

Those lines need to be updated:

https://github.com/tiangolo/fastapi/blob/36c26677682c4245183912e00fc057c05cc6cf7a/fastapi/openapi/utils.py#L36-L61

They reflect how it was before 0.100.0, but with Pydantic V2, that's no longer true.

## Resolution

This issue was closed on 2026-02-04. See the linked GitHub issue and any
referenced pull requests at https://github.com/fastapi/fastapi/issues/10787 for the exact code change that resolved it.
