const fs = require("fs");
const path = require("path");
const vscode = require("vscode");

class LocalFilesDecorationProvider {
  constructor(context) {
    this.context = context;
    this.mountsByWorkspace = new Map();
    this.watchers = [];
    this.onDidChangeFileDecorationsEmitter = new vscode.EventEmitter();
    this.onDidChangeFileDecorations = this.onDidChangeFileDecorationsEmitter.event;
    this.reloadWatchers();
  }
  dispose() {
    this.onDidChangeFileDecorationsEmitter.dispose();
    for (const watcher of this.watchers) {
      watcher.dispose();
    }
  }
  provideFileDecoration(uri) {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
    if (!workspaceFolder || !this.isEnabled(workspaceFolder)) {
      return undefined;
    }
    const relativePath = this.toWorkspaceRelativePath(workspaceFolder, uri);
    if (!relativePath) {
      return undefined;
    }
    const mounts = this.getMounts(workspaceFolder);
    if (!mounts.some((mount) => this.isUnderMount(relativePath, mount))) {
      return undefined;
    }
    const tooltip = this.getConfig(workspaceFolder).get("tooltip", "Local-only canonical file mount");
    const decoration = new vscode.FileDecoration(
      undefined,
      tooltip,
      new vscode.ThemeColor("gitDecoration.ignoredResourceForeground")
    );
    decoration.propagate = false;
    return decoration;
  }
  refresh() {
    this.mountsByWorkspace.clear();
    this.onDidChangeFileDecorationsEmitter.fire(undefined);
  }
  reloadWatchers() {
    for (const watcher of this.watchers) {
      watcher.dispose();
    }
    this.watchers = [];
    for (const workspaceFolder of vscode.workspace.workspaceFolders || []) {
      const mountsFile = this.getMountsFile(workspaceFolder);
      const watcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(workspaceFolder, mountsFile)
      );
      watcher.onDidChange(() => this.refresh(), this, this.context.subscriptions);
      watcher.onDidCreate(() => this.refresh(), this, this.context.subscriptions);
      watcher.onDidDelete(() => this.refresh(), this, this.context.subscriptions);
      this.watchers.push(watcher);
      this.context.subscriptions.push(watcher);
    }
  }
  getConfig(workspaceFolder) {
    return vscode.workspace.getConfiguration("fofLocalFilesDecorator", workspaceFolder.uri);
  }
  isEnabled(workspaceFolder) {
    return this.getConfig(workspaceFolder).get("enabled", true);
  }
  getMountsFile(workspaceFolder) {
    const configuredPath = this.getConfig(workspaceFolder).get("mountsFile", "scripts/local_files_mounts.txt");
    return this.normalizeMount(configuredPath) || "scripts/local_files_mounts.txt";
  }
  getMounts(workspaceFolder) {
    const cacheKey = workspaceFolder.uri.toString();
    if (this.mountsByWorkspace.has(cacheKey)) {
      return this.mountsByWorkspace.get(cacheKey);
    }
    const config = this.getConfig(workspaceFolder);
    const mountsFile = this.getMountsFile(workspaceFolder);
    const mountPath = path.join(workspaceFolder.uri.fsPath, mountsFile);
    const fileMounts = this.readMountsFile(mountPath);
    const extraMounts = config.get("extraMounts", []).map((mount) => this.normalizeMount(mount)).filter(Boolean);
    const mounts = [...new Set([...fileMounts, ...extraMounts])];
    this.mountsByWorkspace.set(cacheKey, mounts);
    return mounts;
  }
  readMountsFile(mountPath) {
    try {
      const rawText = fs.readFileSync(mountPath, "utf8");
      return rawText
        .split(/\r?\n/)
        .map((line) => line.replace(/#.*/, ""))
        .map((line) => this.normalizeMount(line))
        .filter(Boolean);
    } catch (error) {
      return [];
    }
  }
  normalizeMount(rawPath) {
    if (typeof rawPath !== "string") {
      return null;
    }
    const normalized = rawPath
      .trim()
      .replace(/\\/g, "/")
      .replace(/^\/+/, "")
      .replace(/\/+$/, "");
    return normalized || null;
  }
  toWorkspaceRelativePath(workspaceFolder, uri) {
    const relativePath = path.relative(workspaceFolder.uri.fsPath, uri.fsPath);
    if (!relativePath || relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
      return null;
    }
    return relativePath.split(path.sep).join("/");
  }
  isUnderMount(relativePath, mount) {
    return relativePath === mount || relativePath.startsWith(`${mount}/`);
  }
}

function activate(context) {
  const provider = new LocalFilesDecorationProvider(context);
  context.subscriptions.push(
    provider,
    vscode.window.registerFileDecorationProvider(provider),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("fofLocalFilesDecorator")) {
        provider.refresh();
        provider.reloadWatchers();
      }
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
      provider.refresh();
      provider.reloadWatchers();
    })
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
