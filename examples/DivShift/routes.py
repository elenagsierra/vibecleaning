import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.state import ProjectStateError, get_dataset_artifact, media_type_for_path
from app.web import get_project_dir, json_error, validate_path_part

from .summary import build_divshift_summary


PHOTO_ID_RE = re.compile(r"^[0-9]+$")


def resolve_divshift_image_path(project_dir: Path, state_name: str, photo_id: str) -> Path:
    state_part = validate_path_part(state_name, label="state").lower()
    if not PHOTO_ID_RE.fullmatch(photo_id):
        raise ValueError("Invalid photo id")

    prefix = photo_id[:3]
    project_root = project_dir.resolve()
    for extension in ("png", "jpg", "jpeg", "webp"):
        path = (project_root / state_part / prefix / f"{photo_id}.{extension}").resolve()
        if project_root not in path.parents:
            raise ProjectStateError("Invalid image path")
        if path.exists() and path.is_file():
            return path
    raise ProjectStateError("Unknown image")


def register_divshift_routes(app: FastAPI, *, data_root: Path):
    data_root = data_root.resolve()

    @app.get("/api/project/{project_name}/apps/divshift/dataset/{dataset_id}/summary")
    async def get_divshift_summary(project_name: str, dataset_id: str, logical_name: str = "divshift_nawc.csv"):
        try:
            project_dir = get_project_dir(data_root, project_name)
            _, artifact_path = get_dataset_artifact(project_dir, dataset_id, logical_name)
            return JSONResponse(build_divshift_summary(artifact_path))
        except (ValueError, ProjectStateError) as exc:
            return json_error(str(exc), 404)

    @app.get("/api/project/{project_name}/apps/divshift/image")
    async def get_divshift_image(project_name: str, state_name: str, photo_id: str):
        try:
            project_dir = get_project_dir(data_root, project_name)
            image_path = resolve_divshift_image_path(project_dir, state_name, photo_id)
        except (ValueError, ProjectStateError) as exc:
            return json_error(str(exc), 404)
        return FileResponse(image_path, media_type=media_type_for_path(image_path))

