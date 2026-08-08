# ===== START OF FILE apps/content_studio/model3d/rodin.py =====
# Hyper3D Rodin Image-to-3D client with local sidecar caching.

import os
import json
import time
import hashlib

from apps.content_studio.model3d import config

requests = None

### Payloads / request helpers
def create_task(image_path, api_key=None, **options):
    """Create a Hyper3D Rodin Image-to-3D task.

    :param image_path: local PNG/JPEG path.
    :param api_key: optional Hyper3D API key; defaults to HYPER3D_API_KEY or the free-trial key.
    :param options: Rodin request options overriding config defaults.
    :return: dict with task_uuid, subscription_key, job_uuids, and response_body.
    """
    request_options = _build_options(options)
    return _create_task_request(image_path, request_options, api_key)
def poll_task(subscription_key, api_key=None, task_uuid=None, interval=None, timeout=None):
    """Poll a Rodin task subscription until all jobs are done or any job fails.

    :param subscription_key: Rodin subscription key from the create response.
    :param api_key: optional Hyper3D API key; defaults to HYPER3D_API_KEY or the free-trial key.
    :param task_uuid: optional task UUID for clearer status output.
    :param interval: seconds between polls.
    :param timeout: max seconds to wait.
    :return: final status JSON dict.
    :raises RuntimeError: on failed Rodin jobs.
    :raises TimeoutError: when timeout elapses.
    """
    interval = config.RODIN_POLL_INTERVAL_S if interval is None else interval
    timeout = config.RODIN_TIMEOUT_S if timeout is None else timeout
    started = time.time()
    deadline = started + timeout
    label = task_uuid or subscription_key
    while True:
        status_body = get_status(subscription_key, api_key=api_key)
        statuses, final_status = _status_summary(status_body)
        elapsed = int(time.time() - started)
        print(f"[model3d] Rodin task {label}: {','.join(statuses) or final_status} elapsed {elapsed}s", flush=True)
        if final_status == "Done":
            return status_body
        if final_status == "Failed":
            detail = _response_detail_from_body(status_body)
            raise RuntimeError(f"Rodin task {label} failed: {detail}")
        if time.time() >= deadline:
            raise TimeoutError(f"Rodin task {label} timed out after {timeout}s.")
        time.sleep(interval)
def get_status(subscription_key, api_key=None):
    """Fetch Rodin task status for a subscription key.

    :param subscription_key: Rodin subscription key from the create response.
    :param api_key: optional Hyper3D API key; defaults to HYPER3D_API_KEY or the free-trial key.
    :return: parsed status JSON dict.
    """
    key = _require_api_key(api_key)
    url = f"{config.RODIN_BASE_URL}/status"
    response = _request("post", url, headers=_headers(key), json={"subscription_key": subscription_key}, timeout=60)
    body = response.json()
    _raise_body_error(body)
    if "jobs" not in body and "status_list" not in body and body.get("message"):
        raise RuntimeError(_friendly_rodin_error(body.get("message")))
    return body
def download_task(task_uuid, out_path, api_key=None):
    """Download the first GLB asset for a completed Rodin task.

    :param task_uuid: Rodin task UUID.
    :param out_path: destination GLB path.
    :param api_key: optional Hyper3D API key; defaults to HYPER3D_API_KEY or the free-trial key.
    :return: destination path.
    """
    key = _require_api_key(api_key)
    url = f"{config.RODIN_BASE_URL}/download"
    response = _request("post", url, headers=_headers(key), json={"task_uuid": task_uuid}, timeout=90)
    body = response.json()
    _raise_body_error(body)
    asset = _first_glb_asset(body)
    if not asset:
        detail = _friendly_rodin_error(_response_detail_from_body(body))
        raise RuntimeError(f"Rodin task {task_uuid} did not return a GLB download URL: {detail}")
    return download_file(asset["url"], out_path)
def download_file(url, out_path):
    """Stream a URL to a local file.

    :param url: source URL.
    :param out_path: destination path.
    :return: destination path.
    """
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    response = _request("get", url, stream=True, timeout=180)
    try:
        with open(out_path, "wb") as f:
            if hasattr(response, "iter_content"):
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            else:
                f.write(response.content)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return out_path
def generate_mesh(image_path, out_dir, name, api_key=None, force=False, **options):
    """Generate or reuse a Rodin GLB for an input image.

    :param image_path: local PNG/JPEG path.
    :param out_dir: directory where outputs and sidecar JSON should land.
    :param name: output stem; writes <name>.glb.
    :param api_key: optional Hyper3D API key; defaults to HYPER3D_API_KEY or the free-trial key.
    :param force: create a new task even when a matching cache exists.
    :param options: Rodin request options overriding config defaults.
    :return: dict with glb_path, thumbnail_path, task_id, consumed_credits, cached.
    """
    os.makedirs(out_dir, exist_ok=True)
    glb_path = os.path.join(out_dir, f"{name}.glb")
    sidecar_path = os.path.join(out_dir, f"{name}.rodin-task.json")
    request_options = _build_options(options)
    payload_hash = _payload_hash(request_options, image_path)
    sidecar = _read_json(sidecar_path)
    if not force and sidecar and sidecar.get("payload_hash") == payload_hash:
        cached = _try_cached_task(sidecar, api_key, glb_path, sidecar_path,
                                  interval=options.get("poll_interval"),
                                  timeout=options.get("timeout"))
        if cached:
            return cached
    created = _create_task_request(image_path, request_options, api_key)
    sidecar = {
        "payload_hash": payload_hash,
        "request_payload": request_options,
        "task_uuid": created["task_uuid"],
        "subscription_key": created["subscription_key"],
        "job_uuids": created["job_uuids"],
        "create_response": created["response_body"],
        "final_status": None,
        "final_status_body": None,
    }
    _write_json(sidecar_path, sidecar)
    status_body = poll_task(created["subscription_key"], api_key=api_key,
                            task_uuid=created["task_uuid"],
                            interval=options.get("poll_interval"),
                            timeout=options.get("timeout"))
    download_task(created["task_uuid"], glb_path, api_key=api_key)
    sidecar["final_status"] = _status_summary(status_body)[1]
    sidecar["final_status_body"] = status_body
    _write_json(sidecar_path, sidecar)
    return _result_from_task(created["task_uuid"], glb_path, cached=False)
def _try_cached_task(sidecar, api_key, glb_path, sidecar_path, interval=None, timeout=None):
    """Reuse a matching sidecar without creating a new Rodin task."""
    task_uuid = sidecar.get("task_uuid") or sidecar.get("task_id")
    subscription_key = sidecar.get("subscription_key")
    if os.path.exists(glb_path) and sidecar.get("final_status") == "Done":
        return _result_from_task(task_uuid, glb_path, cached=True)
    if not task_uuid:
        return None
    if subscription_key and sidecar.get("final_status") != "Done":
        status_body = poll_task(subscription_key, api_key=api_key, task_uuid=task_uuid,
                                interval=interval, timeout=timeout)
        sidecar["final_status"] = _status_summary(status_body)[1]
        sidecar["final_status_body"] = status_body
    download_task(task_uuid, glb_path, api_key=api_key)
    _write_json(sidecar_path, sidecar)
    return _result_from_task(task_uuid, glb_path, cached=True)
def _result_from_task(task_uuid, glb_path, cached):
    """Shape the public generate_mesh return dict."""
    return {
        "glb_path": glb_path,
        "thumbnail_path": None,
        "task_id": task_uuid,
        "consumed_credits": None,
        "cached": cached,
    }
def _build_options(options):
    """Build canonical Rodin request options."""
    request_options = {
        "tier": options.get("tier") or config.RODIN_TIER,
        "mesh_mode": options.get("mesh_mode") or "Raw",
        "texture_mode": options.get("texture_mode") or "high",
    }
    if options.get("prompt"):
        request_options["prompt"] = options["prompt"]
    return request_options
def _build_files(image_path, request_options):
    """Build Rodin multipart form-data fields."""
    files = [
        ("images", ("0000.png", _read_image_bytes(image_path))),
        ("tier", (None, request_options["tier"])),
        ("mesh_mode", (None, request_options["mesh_mode"])),
        ("texture_mode", (None, request_options["texture_mode"])),
    ]
    if request_options.get("prompt"):
        files.append(("prompt", (None, request_options["prompt"])))
    return files
def _create_task_request(image_path, request_options, api_key):
    """POST a prepared Rodin payload and return parsed task identifiers."""
    key = _require_api_key(api_key)
    url = f"{config.RODIN_BASE_URL}/rodin"
    response = _request("post", url, headers=_headers(key), files=_build_files(image_path, request_options), timeout=90)
    body = response.json()
    _raise_body_error(body)
    parsed = _parse_create_response(body)
    if not parsed["task_uuid"] or not parsed["subscription_key"]:
        detail = _response_detail_from_body(body)
        raise RuntimeError(_friendly_rodin_error(f"Unexpected Rodin create response: {detail}"))
    return parsed
def _parse_create_response(body):
    """Extract Rodin task identifiers from known create response shapes."""
    jobs = body.get("jobs") or {}
    task_uuid = body.get("uuid") or body.get("task_uuid")
    subscription_key = body.get("subscription_key")
    job_uuids = []
    if isinstance(jobs, dict):
        subscription_key = subscription_key or jobs.get("subscription_key") or jobs.get("subscriptionKey")
        job_uuids = jobs.get("uuids") or jobs.get("job_uuids") or []
    elif isinstance(jobs, list):
        for job in jobs:
            if isinstance(job, dict):
                subscription_key = subscription_key or job.get("subscription_key") or job.get("subscriptionKey")
                if job.get("uuid"):
                    job_uuids.append(job.get("uuid"))
    if not task_uuid and job_uuids:
        task_uuid = job_uuids[0]
    return {
        "task_uuid": task_uuid,
        "subscription_key": subscription_key,
        "job_uuids": job_uuids,
        "response_body": body,
    }
def _status_summary(body):
    """Return status list and aggregate final status from a Rodin status response."""
    statuses = []
    jobs = body.get("jobs") or []
    if isinstance(jobs, list):
        statuses = [str(job.get("status", "Unknown")) for job in jobs if isinstance(job, dict)]
    if not statuses and body.get("status_list"):
        statuses = [str(status) for status in body.get("status_list") or []]
    normalized = [status.lower() for status in statuses]
    if normalized and all(status == "done" for status in normalized):
        return statuses, "Done"
    if any(status == "failed" for status in normalized):
        return statuses, "Failed"
    return statuses, "Generating"
def _first_glb_asset(body):
    """Find the first GLB asset in a Rodin download response."""
    for item in body.get("list") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or ""
        url = item.get("url")
        if name.lower().endswith(".glb") and url:
            return item
    return None
def _headers(key):
    """Build Rodin auth headers."""
    return {"Authorization": f"Bearer {key}"}
def _require_api_key(api_key):
    """Resolve a Hyper3D API key, falling back to the Rodin free-trial key."""
    return config.resolve_hyper3d_api_key(api_key)
def _request(method, url, **kwargs):
    """Call requests with friendly Rodin errors and short 429 backoff."""
    client = _requests()
    func = getattr(client, method.lower())
    last_response = None
    for attempt in range(4):
        response = func(url, **kwargs)
        last_response = response
        if getattr(response, "status_code", 200) == 429 and attempt < 3:
            wait_s = 2 ** attempt
            print(f"[model3d] Rodin rate limit hit; retrying in {wait_s}s.", flush=True)
            time.sleep(wait_s)
            continue
        _raise_for_status(response)
        return response
    _raise_for_status(last_response)
    return last_response
def _requests():
    """Import requests lazily so CLI help stays lightweight."""
    global requests
    if requests is None:
        import requests as imported_requests
        requests = imported_requests
    return requests
def _raise_for_status(response):
    """Raise friendly Rodin errors for common HTTP failures."""
    status = getattr(response, "status_code", 200)
    if status < 400:
        return
    detail = _response_detail(response)
    if status in (402, 429):
        raise RuntimeError(_friendly_rodin_error(detail))
    if status in (401, 403):
        raise RuntimeError("HYPER3D_API_KEY invalid or rejected")
    raise RuntimeError(f"Rodin request failed with HTTP {status}: {detail}")
def _raise_body_error(body):
    """Raise friendly Rodin errors embedded in JSON bodies."""
    if not isinstance(body, dict):
        return
    status = str(body.get("status", "")).lower()
    detail = body.get("error")
    if not detail and status in ("error", "failed", "failure"):
        detail = body.get("message") or body.get("status")
    if detail:
        raise RuntimeError(_friendly_rodin_error(detail))
def _friendly_rodin_error(detail):
    """Return a user-facing Rodin error with quota guidance when relevant."""
    text = str(detail)
    lowered = text.lower()
    if any(word in lowered for word in ("quota", "credit", "limit", "exceed", "daily", "rate")):
        return (
            "Hyper3D Rodin free trial has a daily limit; try again later or set "
            f"HYPER3D_API_KEY to your own key. Detail: {text}"
        )
    return text
def _response_detail(response):
    """Return useful error text from an HTTP response."""
    try:
        return _response_detail_from_body(response.json())
    except Exception:
        return getattr(response, "text", "") or "<no response body>"
def _response_detail_from_body(body):
    """Return useful error text from a parsed JSON body."""
    if isinstance(body, dict):
        message = body.get("message") or body.get("error")
        if message:
            return message
        return json.dumps(body, sort_keys=True)
    return str(body)
def _payload_hash(request_options, image_path):
    """Hash canonical request options plus raw image bytes."""
    hashed = {
        "image_sha256": _file_sha256(image_path),
        "payload": request_options,
    }
    encoded = json.dumps(hashed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
def _read_image_bytes(path):
    """Read a PNG/JPEG image as bytes."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        raise ValueError(f"Rodin image input must be PNG or JPEG, got {path!r}.")
    with open(path, "rb") as f:
        return f.read()
def _file_sha256(path):
    """Hash a local file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def _read_json(path):
    """Read JSON if present; return None if missing."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
def _write_json(path, body):
    """Write stable, readable JSON."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2, sort_keys=True)
        f.write("\n")

# ===== END OF FILE apps/content_studio/model3d/rodin.py =====
