# Incident Report: Mounting sub-applications under `APIRouter`

**Source issue:** #10180 (https://github.com/fastapi/fastapi/issues/10180)
**Status:** closed
**Labels:** bug
**Reported:** 2023-08-31
**Resolved:** 2026-05-18
**Discussion comments:** 18

## Reported Problem

### Discussed in https://github.com/tiangolo/fastapi/discussions/8682

<div type='discussions-op-text'>

### Example Code

```python
from fastapi import FastAPI, APIRouter
from starlette.testclient import TestClient

app = FastAPI()
api_router = APIRouter(prefix="/api")


@api_router.get("/app")
def read_main():
    return {"message": "Hello World from main app"}


app.include_router(api_router)

subapi = FastAPI()


@subapi.get("/sub")
def read_sub():
    return {"message": "Hello World from sub API"}


api_router.mount("/subapi", subapi)

client = TestClient(app)

assert client.get('/api/app').status_code == 200

# this next assert fails
assert client.get('/api/subapi/sub').status_code == 200
```


### Description

Is it possible to mount a sub-application under an APIRouter? APIRouter itself has a mount function and accepts similar arguments to mounting a sub-application on a FastAPI instance, but I can't get the routing to actually work (nor can i get the openapi docs or spec to come back from that I would assume are the correct URLs.

The docs for sub applications note that the sub-application will have it's root_path correctly set, and I've tried a few combinations of manually setting the root_path on the subapi instance, but to no avail.

## Related
- https://github.com/tiangolo/fastapi/discussions/9070
- https://github.com/tiangolo/fastapi/pull/5373

## Resolution

This issue was closed on 2026-05-18. See the linked GitHub issue and any
referenced pull requests at https://github.com/fastapi/fastapi/issues/10180 for the exact code change that resolved it.
