# ===== START OF FILE apps/content_studio/model3d/blender/install_mcp_addon.py =====
# Blender-side script: install and enable the sibling vendored Blender MCP addon.

import os

import bpy

### Addon install
def main():
    """Install, enable, and save preferences for the vendored Blender MCP addon."""
    addon_path = os.path.join(os.path.dirname(__file__), "blender_mcp_addon.py")
    if not os.path.exists(addon_path):
        raise RuntimeError(f"Vendored Blender MCP addon not found: {addon_path}")
    print(f"Installing BlenderMCP addon from {addon_path}")
    bpy.ops.preferences.addon_install(filepath=addon_path, overwrite=True)
    bpy.ops.preferences.addon_enable(module="blender_mcp_addon")
    bpy.ops.wm.save_userpref()
    print("BlenderMCP addon enabled as module blender_mcp_addon")
    print("Blender preferences saved")
main()

# ===== END OF FILE apps/content_studio/model3d/blender/install_mcp_addon.py =====
