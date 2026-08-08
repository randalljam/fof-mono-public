from setuptools import setup

# Read install_requires from requirements file (skip blanks and comment-only lines).
with open('dependencies/requirements_2026-07-11.txt') as f:
    requirements = []
    for line in f.read().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)

# Metadata-only package: records dependency pins for pip check without installing
# apps/ or core/ into site-packages (which would bind imports to one checkout).
setup(
    name='fof-mono',
    version='1.0',
    packages=[],
    py_modules=[],
    install_requires=requirements,
)

# Terminal commands (primary checkout only — worktrees symlink the shared .venv)
'''
python3 -m venv .venv
source .venv/bin/activate
pip install -r dependencies/requirements_2026-07-11.txt
pip install -e . --no-deps
python3 scripts/python/install_worktree_import_guard.py

Do NOT run pip install -e . from a shared-venv worktree — it rewrites venv metadata
for every checkout. See docs/2026-07-31_worktree-shared-venv-editable-import-trap.md.

To delete the virtual environment:
deactivate
rm -rf .venv
'''
