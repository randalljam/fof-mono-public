file: dependencies/venv_setup_log.md
title: Log of virtual environment and dependency setup for fof-mono


## 2026-06-02 — Initial fof-mono venv (snapshot from corpus-tools)

### Context

- New monorepo setup; dependencies copied from `requirements_2024-09-26_add_CURRENT.txt` into a dated snapshot file (see below).
- `.env` copied from the old repo (API keys).
- Virtual environment created at repo root: `.venv`.
- Shell shows `(.venv)` in the prompt after `source .venv/bin/activate`.

### Requirements file

- **New (active for fixes):** `dependencies/requirements_2026-06-02.txt`
- **Unchanged archive:** `dependencies/requirements_2024-09-26_add_CURRENT.txt` (left as the historical copy)

Diff between the two files is only these install-blockers (everything else identical):

| Line | 2024 file | 2026-06-02 file |
| --- | --- | --- |
| docs | `docs==0.1.0` | Commented out — not a PyPI package; pipreqs false positive from local `docs/` imports (`docs.vis`) |
| megaparse | `megaparse>=0.0.48,<1.0.0` | Commented out — conflicts with `langchain==0.3.1` (megaparse wants `langchain<0.3`); optional for `core/conversion.py` PDF helpers |

### Venv commands used

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
```

`pip install -e .` succeeded after the two requirement lines above were commented out in the 2026-06-02 file (~5 minutes; includes torch, speechbrain, langchain stack).

### Python version: 3.12 vs 3.11

- **Installed venv:** Python **3.12.8** (`python3.12 -m venv .venv`).
- **Reason chosen:** Default `python3` on this machine is **3.13.1**, which is a poor match for many pinned packages; 3.12 is closer to README_external’s “python 3.12.6” path and worked for a full `pip install -e .`.
- **README_internal** still says to select **Python 3.11.3** in VS Code/Cursor. That was the prior corpus-tools convention; this venv was not recreated on 3.11 yet.
- **Open decision:** Stay on 3.12 for fof-mono, or delete `.venv` and recreate with 3.11 to match the old interpreter choice:

```bash
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

(Use whichever requirements file `setup.py` points at when reinstalling.)

### setup.py note (follow-up)

`setup.py` still reads `dependencies/requirements_2024-09-26_add_CURRENT.txt`. To use the 2026-06-02 snapshot for future installs, change that path (and keep or add comment-line filtering in `setup.py` so provenance `#` blocks at the bottom of the file are not passed to pip).

### Other setup notes

- **setup.py filtering:** Skipping blank lines and comment-only lines avoids pip errors on the provenance section at the bottom of the requirements file.
- **Tests:** `python -m unittest discover -s tests` may still hit gaps unrelated to venv creation (e.g. `cv2` / opencv not listed in requirements; some tests import modules that need extra env).
- **megaparse:** Install separately only if needed; resolve langchain version conflict first.
