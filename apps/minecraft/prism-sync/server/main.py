"""FastAPI entrypoint for the Prism Sync local web app."""
import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import config as app_config
from server import mods as mods_ops
from server import prism as prism_ops
from server import remote as remote_ops
from server import sync as sync_ops

WEB_DIR = os.path.join(APP_DIR, "web")
app = FastAPI(title="Prism Sync")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ReachabilityRequest(BaseModel):
    computer_ids: list[str] | None = None


class StatusRequest(BaseModel):
    instance_names: list[str] | None = None
    computer_ids: list[str] | None = None


class InstanceStatusRequest(BaseModel):
    instance_name: str
    computer_ids: list[str] | None = None


class PullRequest(BaseModel):
    instance_names: list[str]
    computer_ids: list[str]


class SyncRequest(BaseModel):
    instance_names: list[str]
    computer_ids: list[str]
    update_existing: bool = False
    sync_icons: bool = True
    write_log: bool = True
    mods_only: bool = False


@app.get("/")
def index_page():
    """Serve the single-page UI."""
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.get("/api/config")
def get_config():
    """Return computers, filters, and exclude labels."""
    return app_config.public_config()


@app.get("/api/instances")
def get_instances(includes: str | None = None, excludes: str | None = None):
    """List local Prism instances."""
    cfg = app_config.load_config()
    if includes is None:
        include_list = cfg["instance_filters"].get("includes", [])
    else:
        include_list = [part.strip() for part in includes.split(",") if part.strip()]
    if excludes is None:
        exclude_list = cfg["instance_filters"].get("excludes", [])
    else:
        exclude_list = [part.strip() for part in excludes.split(",") if part.strip()]
    instances = prism_ops.discover_local_instances(include_list, exclude_list)
    instance_names = [row["name"] for row in instances]
    return {
        "instances": instances,
        "local_mods": mods_ops.local_mods_map(instance_names),
    }


@app.get("/api/icon/{instance_name:path}")
def get_icon(instance_name):
    """Return the resolved icon bytes for an instance."""
    data = prism_ops.read_icon_bytes(instance_name)
    return Response(content=data, media_type="image/png")


@app.post("/api/reachability")
def post_reachability(body: ReachabilityRequest):
    """Check SSH reachability for computers."""
    results = remote_ops.check_all_reachability(body.computer_ids)
    return {"reachability": results}


@app.get("/api/status")
def get_status_health():
    """Lightweight liveness probe. Matrix status check requires POST."""
    return {
        "ok": True,
        "service": "prism-sync",
        "hint": "POST /api/status for matrix status; GET is health-only",
    }


@app.post("/api/status")
def post_status(body: StatusRequest):
    """Fill matrix status for instances and computers."""
    reachability = remote_ops.check_all_reachability(body.computer_ids)
    local_instances = prism_ops.discover_local_instances([], [])
    if body.instance_names:
        allowed = {row["name"] for row in local_instances}
        instance_names = [name for name in body.instance_names if name in allowed]
    else:
        instance_names = [row["name"] for row in local_instances]
    status_payload = sync_ops.status_for_instances(instance_names, body.computer_ids, reachability)
    payload = sync_ops.build_matrix(local_instances, status_payload)
    payload["reachability"] = reachability
    return payload


@app.post("/api/status/instance")
def post_instance_status(body: InstanceStatusRequest):
    """Status for one instance across computers (row click)."""
    reachability = remote_ops.check_all_reachability(body.computer_ids)
    status_payload = sync_ops.status_for_instances([body.instance_name], body.computer_ids, reachability)
    return {
        "instance_name": body.instance_name,
        "status": status_payload["status"].get(body.instance_name, {}),
        "mods_detail": status_payload["mods_detail"].get(body.instance_name, {}),
        "reachability": reachability,
    }


@app.post("/api/sync/preview")
def post_sync_preview(body: SyncRequest):
    """Dry-run sync preview."""
    if not body.instance_names:
        raise HTTPException(status_code=400, detail="No instances selected")
    if not body.computer_ids:
        raise HTTPException(status_code=400, detail="No target computers selected")
    preview = sync_ops.preview_sync(
        body.instance_names,
        body.computer_ids,
        sync_icons=body.sync_icons,
        update_existing=body.update_existing,
        mods_only=body.mods_only,
    )
    return {"preview": preview}


@app.post("/api/sync/apply")
def post_sync_apply(body: SyncRequest):
    """Run the real sync after preview."""
    if not body.instance_names:
        raise HTTPException(status_code=400, detail="No instances selected")
    if not body.computer_ids:
        raise HTTPException(status_code=400, detail="No target computers selected")
    preview = sync_ops.preview_sync(
        body.instance_names,
        body.computer_ids,
        sync_icons=body.sync_icons,
        update_existing=body.update_existing,
        mods_only=body.mods_only,
    )
    before_snapshot = sync_ops.capture_mods_snapshot(body.instance_names, body.computer_ids)
    apply_text = sync_ops.apply_sync(
        body.instance_names,
        body.computer_ids,
        sync_icons=body.sync_icons,
        update_existing=body.update_existing,
        mods_only=body.mods_only,
    )
    after_snapshot = sync_ops.capture_mods_snapshot(body.instance_names, body.computer_ids)
    if body.write_log:
        sync_ops.append_sync_log(
            before_snapshot,
            after_snapshot,
            body.instance_names,
            body.computer_ids,
            {
                "sync_icons": body.sync_icons,
                "mods_only": body.mods_only,
            },
        )
    return {"preview": preview, "apply": apply_text}


@app.post("/api/pull/apply")
def post_pull_apply(body: PullRequest):
    """Pull remote-only mod jars from targets into local instances."""
    if not body.instance_names:
        raise HTTPException(status_code=400, detail="No instances selected")
    if not body.computer_ids:
        raise HTTPException(status_code=400, detail="No target computers selected")
    result = sync_ops.apply_pull(body.instance_names, body.computer_ids)
    return {"result": result}


def main():
    """Run uvicorn for local development."""
    import uvicorn
    cfg = app_config.load_config()
    port = cfg.get("server", {}).get("port", 8770)
    uvicorn.run("server.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
