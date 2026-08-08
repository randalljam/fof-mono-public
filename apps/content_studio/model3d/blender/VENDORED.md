file: apps/content_studio/model3d/blender/VENDORED.md
title: Vendored Blender MCP add-on
last-updated: 2026-07-27_2147
ai: Codex - GPT-5
session: `PR review #59`


## Provenance
`blender_mcp_addon.py` was imported on 2026-07-09 from the upstream [`ahujasid/blender-mcp` repository](https://github.com/ahujasid/blender-mcp) (`addon.py`). The import did not record an upstream commit SHA. Its reviewed vendored SHA-256 is:

```
bba60831f5f89a74deda0294b131668a086cf46eb35a6a01abbd0d21d9e92630
```

Treat the checksum as the local version pin. A future refresh must record the exact upstream commit, review the diff and security boundary, update this checksum, and preserve the upstream license notice below.


## Security boundary
The add-on binds its command socket to `localhost:9876`, but connected MCP clients can ask it to execute arbitrary Python inside Blender. That code runs with the Blender process's filesystem, network, and subprocess permissions. Use `mcp-launch` only for trusted local development, keep the socket on loopback, save work before connecting, and do not expose it to untrusted prompts or remote clients.

The external `blender-mcp` server is not vendored here. Upstream versions may collect telemetry; review the upstream terms and disable telemetry before connecting that server when the working material is sensitive.


## Upstream MIT license
MIT License

Copyright (c) 2025 Siddharth Ahuja

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
