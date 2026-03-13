# Application Contract

Applications in this repository are self-contained packages that import the generic Vibecleaning core.

An application may own:

- its own `server.py` entrypoint
- its own `static/` frontend assets
- app-specific backend routes
- named UI actions
- summary or preview routes for large artifacts

The core does not discover or mount applications dynamically. An application imports the core app factory and composes on top of it.

## Recommended Layout

```text
examples/<app>/
  server.py
  routes.py
  summary.py
  static/
    index.html
    app.js
    vendor/
```

## Route Boundaries

Applications may call the generic core APIs:

- `GET /api/projects`
- `GET /api/project/{project}/state`
- `GET /api/project/{project}/graph`
- `GET /api/project/{project}/dataset/{dataset_id}`
- `GET /api/project/{project}/artifact/{dataset_id}/{logical_name}`
- `GET /api/project/{project}/artifact/{dataset_id}/{logical_name}/meta`
- `GET /api/project/{project}/artifact/{dataset_id}/{logical_name}/preview`
- `POST /api/project/{project}/analyses`
- `POST /api/project/{project}/steps`
- `POST /api/project/{project}/head`
- `POST /api/project/{project}/undo`

Applications may also define their own namespaced routes such as:

- `GET /api/project/{project}/apps/<app>/...`
- `POST /api/project/{project}/apps/<app>/actions/...`

Those routes should:

- live outside the core backend
- stay namespaced under the application
- translate persistent actions into generic `analysis` or `step` executions

## Large-File Behavior

If an application needs a faster read model for very large artifacts, it may implement a server-side summary route or generate derived artifacts through the generic execution harness.

Do not move that domain logic into the core unless it is broadly generic.
