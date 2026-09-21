# Incident Report: 0.137.0: `APIRoute.tags` invisible to type checkers in generate_unique_id_function (regression from #15745)

**Source issue:** #15764 (https://github.com/fastapi/fastapi/issues/15764)
**Status:** closed
**Labels:** bug
**Reported:** 2026-06-15
**Resolved:** 2026-06-15
**Discussion comments:** 2

## Reported Problem

### Discussed in https://github.com/fastapi/fastapi/discussions/15749

<div type='discussions-op-text'>

<sup>Originally posted by **tedserbinski** June 15, 2026</sup>
### First check

- I searched existing discussions and issues — no existing report for this.
- This is about a **type-checker regression in 0.137.0**, not a runtime bug (runtime is unaffected).

### Summary

In **0.137.0**, the documented `generate_unique_id_function` pattern from [Advanced → Generate Clients](https://fastapi.tiangolo.com/advanced/generate-clients/) — which reads `route.tags` — now fails static type checking. Type checkers report that `APIRoute` has no attribute `tags`, even though the docs still show exactly this code and it works fine at runtime.

This appears to be an unintended side-effect of #15745 ("Refactor internals to preserve APIRouter and APIRoute instances"): `APIRoute.__init__` was changed to delegate state-setting to a helper that receives `self` cast to the `_APIRouteLike` Protocol, and `APIRoute` itself no longer carries a class-level `tags` annotation. So the attribute is still assigned at runtime, but it's invisible to type checkers looking at the `APIRoute` type.

### Reproducible example

This is the docs' own example (`docs_src/generate_clients/tutorial003_py310.py`):

```python
from fastapi import FastAPI
from fastapi.routing import APIRoute

def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"

app = FastAPI(generate_unique_id_function=custom_generate_unique_id)
```

Running a type checker (`ty`) over it on 0.137.0:

```
error[unresolved-attribute]: Object of type `APIRoute` has no attribute `tags`
 --> repro.py:6:15
  |
6 |     return f"{route.tags[0]}-{route.name}"
  |               ^^^^^^^^^^
```

At runtime the same code builds the app and generates operation IDs correctly — only the static type surface is affected. `route.name` resolves fine; only `route.tags` is missing.

### Expected behavior

`route.tags` should remain visible to type checkers as a public attribute of `APIRoute` (it's part of the documented public callback contract), as it was in 0.136.x where `APIRoute.__init__` assigned `self.tags = tags or []` directly.

### Environment

- FastAPI: **0.137.0**
- Python: 3.14
- Type checker: `ty` 0.0.49 (also reproduces with strict Pyright per the same root cause); mypy may differ
- OS: macOS

### Possible fix

Add the lost class-level annotation back to `APIRoute` (e.g. `tags: list[str | Enum]`) so it matches what the `_APIRouteLike` Protocol already declares. Happy to open a PR if that direction is welcome.

Thanks for FastAPI! 🙏
</div>

## Resolution

This issue was closed on 2026-06-15. See the linked GitHub issue and any
referenced pull requests at https://github.com/fastapi/fastapi/issues/15764 for the exact code change that resolved it.
