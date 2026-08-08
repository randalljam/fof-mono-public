file: apps/minecraft/litematica/README.md
title: Litematica schematic format — reference area
last-updated: 2026-06-22_0800
ai: Cursor - Composer 2.5 Fast
session: Litematic format spec

# Litematica reference

This folder holds documentation and example files for the **Litematica** (`.litematic`) schematic format used with the [Litematica](https://github.com/maruohon/litematica) Minecraft mod.

| File | Purpose |
|------|---------|
| [`LITEMATIC_FORMAT.md`](LITEMATIC_FORMAT.md) | Full format specification for humans and coding agents |
| [`examples/village-house.litematic`](examples/village-house.litematic) | Small 7×7×7 example schematic (MC 26.1.2, format v7) |

**For coding agents:** read `LITEMATIC_FORMAT.md` before generating or parsing `.litematic` files. Prefer a library (litemapy, mc_schem) over hand-rolled NBT unless you have a strong reason not to.
