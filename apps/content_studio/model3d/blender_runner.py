# ===== START OF FILE apps/content_studio/model3d/blender_runner.py =====
# Subprocess helpers for running Blender scripts from the model3d CLI.

import os
import subprocess

from apps.content_studio.model3d.config import find_blender

### Blender process helpers
def run_blender_script(script_path, script_args=None, background=True, blend_file=None):
    """Run a Blender Python script and stream combined stdout/stderr live.

    :param script_path: path to the Blender Python script.
    :param script_args: argv values passed after Blender's `--` separator.
    :param background: whether to pass --background.
    :param blend_file: optional .blend file to open before running the script.
    :return: captured combined process output.
    :raises RuntimeError: when Blender exits nonzero.
    """
    argv = [find_blender()]
    if background:
        argv.append("--background")
    argv.extend(["--factory-startup", "--python-exit-code", "1"])
    if blend_file:
        argv.append(blend_file)
    argv.extend(["--python", script_path, "--"])
    argv.extend(script_args or [])
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    rc = proc.wait()
    output = "".join(lines)
    if rc != 0:
        tail = "".join(lines[-30:])
        raise RuntimeError(f"Blender exited with code {rc}.\nLast output lines:\n{tail}")
    return output
def launch_blender_ui(startup_script):
    """Launch non-background Blender with a startup Python script and return its PID.

    :param startup_script: path to the script passed via --python.
    :return: subprocess pid.
    """
    argv = [find_blender(), "--factory-startup", "--python", startup_script]
    proc = subprocess.Popen(
        argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, start_new_session=True,
    )
    return proc.pid

# ===== END OF FILE apps/content_studio/model3d/blender_runner.py =====
