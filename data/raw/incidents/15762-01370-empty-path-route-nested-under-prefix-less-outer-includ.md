# Incident Report: 0.137.0: empty-path route nested under prefix-less outer include raises 'Prefix and path cannot be both empty'

**Source issue:** #15762 (https://github.com/fastapi/fastapi/issues/15762)
**Status:** closed
**Labels:** bug, question
**Reported:** 2026-06-15
**Resolved:** 2026-06-15
**Discussion comments:** 1

## Reported Problem

### Discussed in https://github.com/fastapi/fastapi/discussions/15750

<div type='discussions-op-text'>

<sup>Originally posted by **yeonghun-toggle** June 15, 2026</sup>
### First Check

- [X] I added a very descriptive title here.
- [X] I used the GitHub search to find a similar question and didn't find it.
- [X] I searched the FastAPI documentation, with the integrated search.
- [X] I already searched in Google "How to X in FastAPI" and didn't find any information.
- [X] I already read and followed all the tutorial in the docs and didn't find an answer.
- [X] I already checked if it is not related to FastAPI but to [Pydantic](https://github.com/pydantic/pydantic).
- [X] I already checked if it is not related to FastAPI but to [Swagger UI](https://github.com/swagger-api/swagger-ui).
- [X] I already checked if it is not related to FastAPI but to [ReDoc](https://github.com/Redocly/redoc).

### Commit to Help

- [X] I commit to help with one of those options 👆

### Example Code

```python
from fastapi import FastAPI, APIRouter

leaf = APIRouter()

@leaf.get("")                                # empty path
def list_items():
    return []

inner = APIRouter()
inner.include_router(leaf, prefix="/items")  # inner include HAS a prefix

app = FastAPI()
app.include_router(inner)                     # outer include has NO prefix
```

### Description

On **0.137.0**, the last line raises at app-construction time:
`fastapi.exceptions.FastAPIError: Prefix and path cannot be both empty (path operation: list_items)`

On **0.136.3** and earlier the same code works and registers the route at `/items`.

This is a regression introduced by the route-tree refactor in #15745 (preserving `APIRouter`/`APIRoute` instances instead of flattening on include).

It only happens when an empty-path route (`path=""`) is nested **and** at least one include hop in its ancestry has no prefix. If every hop carries a prefix it still works on 0.137.0. Verified on both versions:

| setup | 0.136.3 | 0.137.0 |
|---|---|---|
| `app.include_router(leaf, prefix="/items")` (single include) | `/items` | works |
| `inner` and `app` both include with a prefix | `/v1/items` | works |
| `inner` has prefix, `app.include_router(inner)` has no prefix | `/items` | **raises** |

### Operating System

macOS

### Operating System Details

_No response_

### FastAPI Version

0.137.0

### Pydantic Version

2.13.4

### Python Version

3.12.13

### Additional Context

Root-cause pointer (from a quick read of 0.137.0 `fastapi/routing.py`): in `include_router`, when `prefix` is empty, it recursively iterates the included route candidates and raises if any route's **raw** `path` is empty — without composing the prefixes contributed by the intermediate included routers.
So a leaf that was included with a prefix at an inner hop still trips the check at a prefix-less outer include.
Whether the right fix is to validate the **effective** (prefix-composed) path, or to defer this validation to route-resolution time, is a design call for the refactor author.</div>

## Resolution

This issue was closed on 2026-06-15. See the linked GitHub issue and any
referenced pull requests at https://github.com/fastapi/fastapi/issues/15762 for the exact code change that resolved it.
