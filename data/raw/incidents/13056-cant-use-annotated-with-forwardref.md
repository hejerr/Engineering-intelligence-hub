# Incident Report: Can't use `Annotated` with `ForwardRef`

**Source issue:** #13056 (https://github.com/fastapi/fastapi/issues/13056)
**Status:** closed
**Labels:** bug
**Reported:** 2024-12-10
**Resolved:** 2026-05-18
**Discussion comments:** 16

## Reported Problem

### Issue Content

The following code doesn't generate the correct OpenAPI json:

```py
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_potato() -> Potato:
    return Potato(color='red', size=10)


@app.get('/')
async def read_root(potato: Annotated[Potato, Depends(get_potato)]):
    return {'Hello': 'World'}


@dataclass
class Potato:
    color: str
    size: int
```

If we move the `Potato` up, or remove the `Annotated`, then it works as expected.

## Resolution

This issue was closed on 2026-05-18. See the linked GitHub issue and any
referenced pull requests at https://github.com/fastapi/fastapi/issues/13056 for the exact code change that resolved it.
