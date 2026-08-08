file: _archive-chalice-contents.md
title: Inventory stand-in for the un-migrated web-shared/aws_chalice/_archive chalice/ folder

This file is the carried-over stand-in for the `web-shared/aws_chalice/_archive chalice/` folder, which is NOT migrated into the new repo (it is ~373 MB, mostly old Chalice deployment artifacts). The folder remains in the frozen pre-cutover corpus-tools repo. An agent who needs any of the items below should retrieve them from that frozen repo's git history rather than expecting them in the new repo.

All items are 2024-vintage early/experimental Chalice apps superseded by the current Lambdas under `apps/qrag/api/` and `web-shared/aws_chalice/`.


## Contents
| Item | Date (mtime) | Size | What it is |
| --- | --- | --- | --- |
| `helloworld/` | 2024-04-15 | ~188 KB | Chalice starter app — single GET `/` returning a hello-world JSON message. First Chalice deploy experiment. |
| `bot-reply/` | 2024-05-20 | ~540 KB | Early Chalice app: POST `/reply` echoing a user message and returning sample markdown rendered via `markdown2`. Precursor to the QRAG reply flow. |
| `qrag-deutsch-v3/` | 2024-06-12 | ~373 MB | Older standalone QRAG Deutsch v3 Chalice app (`POST /qrag`) with its own bundled `chalicelib/` copies (`rag_bots.py`, `rag_prompts_routes.py`, `vectordb.py`, `aws_s3.py`, `fileops.py`, `llm.py`, `config.py`), routes dict `ROUTES_DICT_DEUTSCH_V3`, and empty `bots/` and `general/` subdirs. Superseded by `apps/qrag/api/qrag-llm/` + `qrag-routing/`. The size is almost entirely `.chalice/deployments/` build zips. |
| `chalicelib_mirror_deploy_2024-10-03.sh` | 2024-10-03 | ~2.5 KB | Early dated variant of the chalicelib mirror/deploy script, predating the current `find_repo_root()` version at `web-shared/aws_chalice/chalicelib_mirror_deploy.sh`. |


## Retrieval note
Nothing here is referenced by active code. The bundled `chalicelib/` modules in `qrag-deutsch-v3/` are stale copies of what now lives in `core/`; do not import from them. If the historical `ROUTES_DICT_DEUTSCH_V3` routing or an old `app.py` shape is ever needed, pull the specific file from the frozen repo's history.
