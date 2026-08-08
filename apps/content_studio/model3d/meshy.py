# ===== START OF FILE apps/content_studio/model3d/meshy.py =====
# Meshy Image-to-3D client with local sidecar caching to avoid duplicate credit spend.

import os
import json
import time
import base64
import hashlib

from apps.content_studio.model3d import config

requests = None

### Payloads / request helpers
def image_to_data_uri(path):
    """Read a PNG/JPEG image and return a base64 data URI.

    :param path: local .png, .jpg, or .jpeg path.
    :return: a data:image/...;base64 URI string.
    """
    ext = os.path.splitext(path)[1].lower()
    mime_by_ext = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    if ext not in mime_by_ext:
        raise ValueError(f"Meshy image input must be PNG or JPEG, got {path!r}.")
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime_by_ext[ext]};base64,{encoded}"
def create_task(image_path, api_key=None, **options):
    """Create a Meshy Image-to-3D task.

    :param image_path: local PNG/JPEG path.
    :param api_key: optional Meshy API key; defaults to MESHY_API_KEY.
    :param options: Meshy request options overriding config defaults.
    :return: Meshy task id string.
    """
    payload = _build_payload(image_path, options)
    return _create_task_payload(payload, api_key)
def get_task(task_id, api_key=None):
    """Fetch a Meshy Image-to-3D task object.

    :param task_id: Meshy task id.
    :param api_key: optional Meshy API key; defaults to MESHY_API_KEY.
    :return: parsed task JSON dict.
    """
    key = _require_api_key(api_key)
    url = f"{config.MESHY_BASE_URL}/image-to-3d/{task_id}"
    response = _request("get", url, headers=_headers(key), timeout=60)
    return response.json()
def poll_task(task_id, api_key=None, interval=None, timeout=None):
    """Poll a Meshy task until it succeeds or fails.

    :param task_id: Meshy task id.
    :param api_key: optional Meshy API key; defaults to MESHY_API_KEY.
    :param interval: seconds between polls.
    :param timeout: max seconds to wait.
    :return: final task JSON dict.
    :raises RuntimeError: on FAILED/CANCELED tasks.
    :raises TimeoutError: when timeout elapses.
    """
    interval = config.MESHY_POLL_INTERVAL_S if interval is None else interval
    timeout = config.MESHY_TIMEOUT_S if timeout is None else timeout
    started = time.time()
    deadline = started + timeout
    while True:
        task = get_task(task_id, api_key=api_key)
        status = task.get("status", "UNKNOWN")
        progress = task.get("progress", 0)
        elapsed = int(time.time() - started)
        print(f"[model3d] Meshy task {task_id}: {status} {progress}% elapsed {elapsed}s", flush=True)
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELED", "CANCELLED"):
            message = ((task.get("task_error") or {}).get("message")
                       or f"Meshy task {task_id} ended with status {status}.")
            raise RuntimeError(message)
        if time.time() >= deadline:
            raise TimeoutError(f"Meshy task {task_id} timed out after {timeout}s.")
        time.sleep(interval)
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
    """Generate or reuse a Meshy GLB and thumbnail for an input image.

    :param image_path: local PNG/JPEG path.
    :param out_dir: directory where outputs and sidecar JSON should land.
    :param name: output stem; writes <name>.glb and <name>-thumb.png.
    :param api_key: optional Meshy API key; defaults to MESHY_API_KEY.
    :param force: create a new task even when a matching cache exists.
    :param options: Meshy request options overriding config defaults.
    :return: dict with glb_path, thumbnail_path, task_id, consumed_credits, cached.
    """
    os.makedirs(out_dir, exist_ok=True)
    glb_path = os.path.join(out_dir, f"{name}.glb")
    thumbnail_path = os.path.join(out_dir, f"{name}-thumb.png")
    sidecar_path = os.path.join(out_dir, f"{name}.meshy-task.json")
    payload = _build_payload(image_path, options)
    payload_hash = _payload_hash(payload, image_path)
    sidecar = _read_json(sidecar_path)
    if not force and sidecar and sidecar.get("payload_hash") == payload_hash:
        cached = _try_cached_task(sidecar, api_key, glb_path, thumbnail_path, sidecar_path)
        if cached:
            return cached
    task_id = _create_task_payload(payload, api_key)
    _write_json(sidecar_path, {
        "payload_hash": payload_hash,
        "request_payload": _redacted_payload(payload),
        "task_id": task_id,
        "final_task": None,
    })
    final_task = poll_task(task_id, api_key=api_key,
                           interval=options.get("poll_interval"),
                           timeout=options.get("timeout"))
    result = _download_task_outputs(final_task, glb_path, thumbnail_path, cached=False, task_id=task_id)
    _write_json(sidecar_path, {
        "payload_hash": payload_hash,
        "request_payload": _redacted_payload(payload),
        "task_id": task_id,
        "final_task": final_task,
    })
    return result
def _try_cached_task(sidecar, api_key, glb_path, thumbnail_path, sidecar_path):
    """Reuse a matching sidecar without creating a new Meshy task."""
    final_task = sidecar.get("final_task") or {}
    task_id = sidecar.get("task_id")
    if final_task.get("status") == "SUCCEEDED" and os.path.exists(glb_path):
        return _result_from_task(final_task, glb_path, thumbnail_path, task_id, cached=True)
    if not task_id:
        return None
    task = get_task(task_id, api_key=api_key)
    if task.get("status") != "SUCCEEDED":
        task = poll_task(task_id, api_key=api_key)
    result = _download_task_outputs(task, glb_path, thumbnail_path, cached=True, task_id=task_id)
    sidecar["final_task"] = task
    _write_json(sidecar_path, sidecar)
    return result
def _download_task_outputs(task, glb_path, thumbnail_path, cached, task_id=None):
    """Download GLB and thumbnail URLs from a successful Meshy task."""
    if task.get("status") != "SUCCEEDED":
        raise RuntimeError(f"Cannot download outputs from Meshy status {task.get('status')!r}.")
    glb_url = ((task.get("model_urls") or {}).get("glb"))
    if not glb_url:
        raise RuntimeError(f"Meshy task succeeded but did not include model_urls.glb: {task}")
    download_file(glb_url, glb_path)
    thumb_url = task.get("thumbnail_url")
    if thumb_url:
        download_file(thumb_url, thumbnail_path)
    return _result_from_task(task, glb_path, thumbnail_path, task_id or task.get("id"), cached=cached)
def _result_from_task(task, glb_path, thumbnail_path, task_id, cached):
    """Shape the public generate_mesh return dict."""
    return {
        "glb_path": glb_path,
        "thumbnail_path": thumbnail_path if os.path.exists(thumbnail_path) else None,
        "task_id": task_id or task.get("id"),
        "consumed_credits": task.get("consumed_credits"),
        "cached": cached,
    }
def _build_payload(image_path, options):
    """Build the Meshy Image-to-3D request payload."""
    payload = {
        "image_url": image_to_data_uri(image_path),
        "ai_model": config.MESHY_AI_MODEL,
        "topology": config.MESHY_TOPOLOGY,
        "target_polycount": config.MESHY_TARGET_POLYCOUNT,
        "should_texture": config.MESHY_SHOULD_TEXTURE,
        "enable_pbr": config.MESHY_ENABLE_PBR,
        "pose_mode": config.MESHY_POSE_MODE,
        "symmetry_mode": config.MESHY_SYMMETRY_MODE,
        "target_formats": ["glb"],
    }
    for key, value in options.items():
        if key in ("poll_interval", "timeout") or value is None:
            continue
        payload[key] = value
    if not payload.get("texture_prompt"):
        payload.pop("texture_prompt", None)
    return payload
def _create_task_payload(payload, api_key):
    """POST a prepared Meshy payload and return its task id."""
    key = _require_api_key(api_key)
    url = f"{config.MESHY_BASE_URL}/image-to-3d"
    response = _request("post", url, headers=_headers(key), json=payload, timeout=90)
    body = response.json()
    task_id = body.get("result")
    if not task_id:
        raise RuntimeError(f"Unexpected Meshy create response: {body}")
    return task_id
def _headers(key):
    """Build Meshy auth headers."""
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
def _require_api_key(api_key):
    """Resolve and require a Meshy API key."""
    key = config.resolve_meshy_api_key(api_key)
    if not key:
        raise RuntimeError("MESHY_API_KEY invalid or missing")
    return key
def _request(method, url, **kwargs):
    """Call requests with friendly Meshy errors and short 429 backoff."""
    client = _requests()
    func = getattr(client, method.lower())
    last_response = None
    for attempt in range(4):
        response = func(url, **kwargs)
        last_response = response
        if getattr(response, "status_code", 200) == 429 and attempt < 3:
            wait_s = 2 ** attempt
            print(f"[model3d] Meshy rate limit hit; retrying in {wait_s}s.", flush=True)
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
    """Raise friendly Meshy errors for common HTTP failures."""
    status = getattr(response, "status_code", 200)
    if status < 400:
        return
    if status == 401:
        raise RuntimeError("MESHY_API_KEY invalid or missing")
    if status == 402:
        raise RuntimeError("Meshy account out of credits")
    detail = _response_detail(response)
    raise RuntimeError(f"Meshy request failed with HTTP {status}: {detail}")
def _response_detail(response):
    """Return useful error text from an HTTP response."""
    try:
        body = response.json()
        message = ((body.get("task_error") or {}).get("message")
                   or body.get("message") or body.get("error"))
        if message:
            return message
        return json.dumps(body, sort_keys=True)
    except Exception:
        return getattr(response, "text", "") or "<no response body>"
def _payload_hash(payload, image_path):
    """Hash canonical request options plus raw image bytes."""
    hashed = {
        "image_sha256": _file_sha256(image_path),
        "payload": _redacted_payload(payload),
    }
    encoded = json.dumps(hashed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
def _redacted_payload(payload):
    """Return a copy of the request payload without the base64 image."""
    redacted = dict(payload)
    redacted.pop("image_url", None)
    return redacted
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

# ===== END OF FILE apps/content_studio/model3d/meshy.py =====
