# FOF Local Files Decorator

Small local Cursor/VS Code extension that grays out canonical local-file mount paths in the Explorer.

The repo's local-only roots are symlinks into `_LOCAL_FILES`, so Cursor's normal Git ignored-file decorations gray the symlink root but may not gray the files and folders underneath it. This extension reads `scripts/local_files_mounts.txt` and applies the same ignored-resource foreground color to every Explorer item under those configured mount paths.

## What It Decorates

By default, the extension reads:

```text
scripts/local_files_mounts.txt
```

In this repo, that currently includes paths such as:

```text
data
exchanges
_archive
logs
apps/math-quiz/_data
apps/math-quiz/_assets
```

Comments and blank lines in the mounts file are ignored. Changes to the mounts file are picked up after a window reload, and usually after the file watcher fires.

## Install In Cursor

From the repo root:

```bash
bash tools/cursor-local-files-decorator/install.sh
```

Then reload Cursor:

```text
Command Palette -> Developer: Reload Window
```

The installer creates this symlink:

```text
~/.cursor/extensions/fof-local-files-decorator -> <repo>/tools/cursor-local-files-decorator
```

## Install In VS Code

If you want the same behavior in VS Code:

```bash
bash tools/cursor-local-files-decorator/install.sh --vscode
```

Then reload VS Code.

## Settings

The extension should work without settings changes. Optional workspace settings:

```json
{
  "fofLocalFilesDecorator.enabled": true,
  "fofLocalFilesDecorator.mountsFile": "scripts/local_files_mounts.txt",
  "fofLocalFilesDecorator.extraMounts": [],
  "fofLocalFilesDecorator.tooltip": "Local-only canonical file mount"
}
```

It uses the theme color `gitDecoration.ignoredResourceForeground`. To make the gray stronger or weaker, set:

```json
{
  "workbench.colorCustomizations": {
    "gitDecoration.ignoredResourceForeground": "#6f6f6f"
  }
}
```

## Uninstall

Cursor:

```bash
rm ~/.cursor/extensions/fof-local-files-decorator
```

VS Code:

```bash
rm ~/.vscode/extensions/fof-local-files-decorator
```
