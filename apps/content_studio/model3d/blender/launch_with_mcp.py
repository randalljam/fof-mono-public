# ===== START OF FILE apps/content_studio/model3d/blender/launch_with_mcp.py =====
# Blender UI startup script: enable the vendored MCP addon and start localhost:9876.

import os
import sys
import importlib

import bpy

ADDON_MODULE = "blender_mcp_addon"
ADDON_PORT = 9876

### MCP launch
def main():
    """Enable BlenderMCP and start its socket server for UI sessions."""
    addon = _ensure_addon_enabled()
    scene = bpy.context.scene
    scene.blendermcp_port = ADDON_PORT
    scene.blendermcp_auto_start_server = True
    if not getattr(scene, "blendermcp_server_running", False):
        try:
            bpy.ops.blendermcp.start_server()
        except Exception:
            _start_server_direct(addon, scene)
    if not getattr(scene, "blendermcp_server_running", False):
        _start_server_direct(addon, scene)
    print("BlenderMCP server listening on localhost:9876")
def _ensure_addon_enabled():
    """Enable the vendored addon, installing it first if Blender cannot find it."""
    addon_dir = os.path.dirname(__file__)
    addon_path = os.path.join(addon_dir, f"{ADDON_MODULE}.py")
    if addon_dir not in sys.path:
        sys.path.insert(0, addon_dir)
    if ADDON_MODULE not in bpy.context.preferences.addons:
        try:
            bpy.ops.preferences.addon_enable(module=ADDON_MODULE)
        except Exception:
            bpy.ops.preferences.addon_install(filepath=addon_path, overwrite=True)
            bpy.ops.preferences.addon_enable(module=ADDON_MODULE)
    addon = importlib.import_module(ADDON_MODULE)
    if not hasattr(bpy.types.Scene, "blendermcp_port"):
        addon.register()
    return addon
def _start_server_direct(addon, scene):
    """Start the addon server using the same BlenderMCPServer class as the operator."""
    if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
        bpy.types.blendermcp_server = addon.BlenderMCPServer(port=scene.blendermcp_port)
    if not bpy.types.blendermcp_server.running:
        bpy.types.blendermcp_server.start()
    scene.blendermcp_server_running = bpy.types.blendermcp_server.running
main()

# ===== END OF FILE apps/content_studio/model3d/blender/launch_with_mcp.py =====
