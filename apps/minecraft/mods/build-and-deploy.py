#!/usr/bin/env python3
"""
Unified build-and-deploy entrypoint for every mod under minecraft/mods/.

This script orchestrates: pick the right JDK for each target's Minecraft version,
run that mod's local ./gradlew for the requested target(s), locate the produced
jar by reading the mod's gradle.properties, and copy the new jar into configured
deploy paths.

Per-mod quirks (extra deploy paths, Prism client instance suffix(es), default-target
override, per-target JDK home overrides) live in an optional
minecraft/mods/<mod>/.mod-build.toml. Client deploy goes to one or more Prism Launcher
instances when the manifest sets prism_instance_suffix and/or
prism_instance_suffix_by_target (e.g. "MathQuest" -> "Fabric 26.1.2 MathQuest";
by_target lists deploy to every instance that exists). Historical jars stay in each target's Gradle
build/libs/ output; prior copies at deploy destinations are replaced, not archived.

Usage:
    ./minecraft/mods/build-and-deploy.py <mod>
    ./minecraft/mods/build-and-deploy.py <mod> --target fabric-1.21.11
    ./minecraft/mods/build-and-deploy.py <mod> --target fabric-1.21.11,forge-1.20.1
    ./minecraft/mods/build-and-deploy.py <mod> --no-deploy
    ./minecraft/mods/build-and-deploy.py <mod> -- --info       # forward to gradle
    ./minecraft/mods/build-and-deploy.py --list-mods
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# Resolve the mods directory from this script's own path so the script can be invoked
# from anywhere (repo root, mod subdir, etc.).
MODS_DIR_REPO = Path(__file__).resolve().parent

# Per-Java-version candidate JDK install locations, probed in order. The first one
# that exists on disk wins. Covers Homebrew Intel (/usr/local), Homebrew Apple Silicon
# (/opt/homebrew), and Eclipse Temurin (/Library/Java/JavaVirtualMachines). Override
# per-target in a mod's .mod-build.toml [java_home] table if a JDK lives elsewhere.
JAVA_HOME_PROBES = {
    17: [
        "/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home",
        "/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
        "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
    ],
    21: [
        "/usr/local/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home",
        "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home",
        "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home",
    ],
    25: [
        "/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home",
        "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home",
        "/Library/Java/JavaVirtualMachines/temurin-25.jdk/Contents/Home",
    ],
}

# Prism Launcher instance root on macOS. Client deploy uses
# instances/<Loader> <mc-version> <suffix>/minecraft/mods/ when the mod manifest
# sets prism_instance_suffix and/or prism_instance_suffix_by_target (see .mod-build.toml).
PRISM_INSTANCES_BASE = (
    Path.home() / "Library" / "Application Support" / "PrismLauncher" / "instances"
)


def required_java(target_name: str) -> int:
    """Map a target name to the Java major version its toolchain needs.

    forge-1.20.1 uses Java 17 (ForgeGradle 6 + Forge 47.x is Java 17).
    fabric-1.20.x also lands on Java 17 (Mojang's 1.20 line).
    fabric-1.21.x is Java 21 (Mojang bumped the line at 1.20.5).
    fabric-26.x is Java 25 (the current Mojang requirement).
    """
    if target_name.startswith("forge-1.20") or target_name.startswith("fabric-1.20"):
        return 17
    if target_name.startswith("fabric-1.21") or target_name.startswith("forge-1.21"):
        return 21
    if target_name.startswith("fabric-26") or target_name.startswith("forge-26"):
        return 25
    raise SystemExit(
        f"Unknown target '{target_name}'. Teach build-and-deploy.py about it by "
        f"editing required_java() in {Path(__file__).name}."
    )


def parse_properties(path: Path) -> dict[str, str]:
    """Minimal Java .properties reader. Ignores comments and blank lines."""
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def load_manifest(mod_dir: Path) -> dict:
    """Read the optional per-mod .mod-build.toml. Returns {} if absent."""
    manifest_path = mod_dir / ".mod-build.toml"
    if not manifest_path.exists():
        return {}
    with manifest_path.open("rb") as f:
        return tomllib.load(f)


def list_mods() -> list[str]:
    """Every directory under minecraft/mods/ that is a mod root.

    A directory counts as a mod root if it either contains its own ./gradlew (flat
    layout, e.g. mathquest) or has at least one loader-named subfolder that itself
    contains a ./gradlew (nested layout, e.g. remove-singleplayer with fabric/ and
    forge/ subroots).
    """
    out = []
    for p in MODS_DIR_REPO.iterdir():
        if not p.is_dir():
            continue
        if (p / "gradlew").exists():
            out.append(p.name)
            continue
        # Nested layout: a mod root with one or more loader-subroots inside it.
        for sub in p.iterdir():
            if sub.is_dir() and (sub / "gradlew").exists():
                out.append(p.name)
                break
    return sorted(out)


def gradle_root_for_target(mod_dir: Path, target: str) -> Path:
    """Pick the gradle root that owns a given target.

    Two layouts are supported:

    - Flat (e.g. mathquest): the mod directory itself is the gradle root. The
      target's subproject lives at <mod>/targets/<target>/.
    - Nested loader-subroots (e.g. remove-singleplayer): <mod>/<loader>/ is its own
      gradle root, with its own gradle wrapper version. The target's subproject lives
      at <mod>/<loader>/targets/<target>/. The loader is the first hyphen-segment of
      the target name (`fabric-1.21.11` -> `fabric`, `forge-1.20.1` -> `forge`).

    A nested loader subroot is preferred when present; falls back to flat otherwise.
    """
    loader = target.split("-", 1)[0]
    nested = mod_dir / loader
    if nested.is_dir() and (nested / "gradlew").exists():
        return nested
    if (mod_dir / "gradlew").exists():
        return mod_dir
    raise SystemExit(
        f"Cannot find a gradle root for target '{target}' under {mod_dir}. "
        f"Expected either {nested}/gradlew (nested layout) or "
        f"{mod_dir}/gradlew (flat layout)."
    )


def resolve_targets(mod_dir: Path, manifest: dict, cli_target: str | None) -> list[str]:
    """Decide which targets to build for this invocation.

    Priority: --target on the CLI > [default_target] in the manifest > the mod's
    gradle settings.gradle DEFAULT_TARGETS (left implicit; we pass no -Ptargets).
    """
    if cli_target:
        return [t.strip() for t in cli_target.split(",") if t.strip()]
    if manifest.get("default_target"):
        return [str(manifest["default_target"])]
    return []  # caller will run buildAll with no filter; gradle picks defaults


def expand_companion_targets(targets: list[str], manifest: dict) -> list[str]:
    """Append manifest companion targets after each requested target (deduped, order preserved)."""
    companions = manifest.get("companion_targets_by_target", {}) or {}
    out: list[str] = []
    seen: set[str] = set()
    for target in targets:
        if target not in seen:
            seen.add(target)
            out.append(target)
        for companion in companions.get(target, []) or []:
            name = str(companion).strip()
            if name and name not in seen:
                seen.add(name)
                out.append(name)
    return out


def jdk_home_for(target: str, manifest: dict) -> str:
    """Per-target Java home: manifest override wins, else probe known JDK locations.

    Raises SystemExit with a helpful message if no JDK of the required Java major
    version can be found on disk, listing every path that was tried.
    """
    overrides = manifest.get("java_home", {}) or {}
    if target in overrides:
        path = os.path.expanduser(overrides[target])
        if not Path(path).exists():
            raise SystemExit(
                f"JAVA_HOME override for '{target}' in .mod-build.toml points at "
                f"{path}, which does not exist on this machine."
            )
        return path

    major = required_java(target)
    for path in JAVA_HOME_PROBES.get(major, []):
        if Path(path).exists():
            return path

    raise SystemExit(
        f"No Java {major} install found for target '{target}'. Tried:\n"
        + "\n".join(f"  - {p}" for p in JAVA_HOME_PROBES.get(major, []))
        + f"\n\nInstall Java {major}, or add an override to the mod's .mod-build.toml:\n"
        + f"  [java_home]\n  \"{target}\" = \"/path/to/jdk-{major}\""
    )


def prism_instance_name_for(target: str, suffix: str) -> str:
    """Build a Prism instance folder name from a target and manifest suffix."""
    loader, mc_version = target.split("-", 1)
    return f"{loader.capitalize()} {mc_version} {suffix}"


def prism_mods_install_for(target: str, suffix: str) -> Path:
    """Return the mods/ folder for a target's Prism Launcher instance."""
    instance_name = prism_instance_name_for(target, suffix)
    return PRISM_INSTANCES_BASE / instance_name / "minecraft" / "mods"


def remove_prior_jars(mods_install: Path, archives_base_name: str) -> None:
    """Delete any existing <archives_base_name>-*.jar at a deploy destination."""
    for old in mods_install.glob(f"{archives_base_name}*.jar"):
        if old.is_file():
            old.unlink()
            print(f"[build-and-deploy] removed prior {old.name} from {mods_install}")


def deploy_to_prism(
    target: str,
    suffix: str,
    jar: Path,
    archives_base_name: str,
) -> bool:
    """Deploy to a Prism instance mods folder. Returns True when deployed."""
    instance_name = prism_instance_name_for(target, suffix)
    instance_dir = PRISM_INSTANCES_BASE / instance_name
    mods_install = instance_dir / "minecraft" / "mods"
    if not instance_dir.is_dir():
        print(f"[build-and-deploy] Prism instance not found: \"{instance_name}\"")
        print(
            "[build-and-deploy] Create that instance in Prism Launcher first, "
            "then re-run deploy."
        )
        print(f"[build-and-deploy] Expected path: {instance_dir}")
        return False
    print(f"[build-and-deploy] === Deploying {target} to Prism \"{instance_name}\" ===")
    mods_install.mkdir(parents=True, exist_ok=True)
    remove_prior_jars(mods_install, archives_base_name)
    deploy_jar(jar, mods_install)
    return True


def run_gradle(mod_dir: Path, target: str | None, java_home: str, extra_args: list[str]) -> None:
    """Invoke ./gradlew inside the mod directory with the right JAVA_HOME."""
    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    env["PATH"] = f"{java_home}/bin:" + env.get("PATH", "")

    cmd = ["./gradlew", "buildAll"]
    if target:
        cmd.append(f"-Ptargets={target}")
    cmd.extend(extra_args)

    print(f"[build-and-deploy] {mod_dir.name}: {' '.join(cmd)} (JAVA_HOME={java_home})")
    subprocess.run(cmd, cwd=mod_dir, env=env, check=True)


def jar_path_for(gradle_root: Path, archives_base_name: str, mod_version: str, target: str) -> Path:
    """Compute the expected jar path under <gradle_root>/targets/<target>/build/libs/.

    Mirrors the naming convention applied by every target's build.gradle:
        archivesName = "<archives_base_name>-<loader>"
        archiveVersion = "<mod_version>-mc<minecraft_version>"
        jar = "<archives_base_name>-<loader>-<mod_version>-mc<minecraft_version>.jar"
    """
    target_props = gradle_root / "targets" / target / "gradle.properties"
    if not target_props.exists():
        raise SystemExit(f"Missing {target_props} — cannot locate built jar.")
    mc_version = parse_properties(target_props)["minecraft_version"]
    loader = target.split("-", 1)[0]  # "fabric" / "forge" / "neoforge"
    suffix = "-all" if loader == "forge" else ""
    jar_name = f"{archives_base_name}-{loader}-{mod_version}-mc{mc_version}{suffix}.jar"
    return gradle_root / "targets" / target / "build" / "libs" / jar_name


def deploy_jar(jar: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    deploy_name = jar.name.replace("-all.jar", ".jar")
    shutil.copy2(jar, dest_dir / deploy_name)
    print(f"[build-and-deploy] deployed {deploy_name} -> {dest_dir}")


def split_dispatcher_and_gradle_args(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split argv on the first standalone '--'. Everything before is for argparse;
    everything after is forwarded verbatim to gradle.
    """
    if "--" in argv:
        idx = argv.index("--")
        return argv[:idx], argv[idx + 1:]
    return argv, []


def prism_suffixes_for(target: str, manifest: dict) -> list[str]:
    """Prism instance name suffixes for one target (e.g. MathQuest -> Forge 1.20.1 MathQuest)."""
    by_target = manifest.get("prism_instance_suffix_by_target", {}) or {}
    raw = by_target.get(target)
    if raw is None:
        raw = manifest.get("prism_instance_suffix")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return [str(s) for s in raw]


def extra_deploy_paths_for(target: str, manifest: dict) -> list[Path]:
    """Extra deploy dirs for one target: legacy flat list + per-target table."""
    seen: set[str] = set()
    out: list[Path] = []
    for raw in manifest.get("extra_deploy_paths", []) or []:
        key = os.path.expanduser(str(raw))
        if key not in seen:
            seen.add(key)
            out.append(Path(key))
    by_target = manifest.get("extra_deploy_paths_by_target", {}) or {}
    for raw in by_target.get(target, []) or []:
        key = os.path.expanduser(str(raw))
        if key not in seen:
            seen.add(key)
            out.append(Path(key))
    return out


def main() -> int:
    dispatcher_argv, gradle_extra = split_dispatcher_and_gradle_args(sys.argv[1:])

    parser = argparse.ArgumentParser(
        description="Build and deploy a mod under minecraft/mods/. "
                    "Pass extra gradle args after a literal '--' separator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mod", nargs="?", help="Mod directory name under minecraft/mods/")
    parser.add_argument(
        "--target", "-t",
        help="Comma-separated target names (e.g. fabric-1.21.11,forge-1.20.1). "
             "Defaults to the mod's manifest default_target, else gradle DEFAULT_TARGETS.",
    )
    parser.add_argument("--no-deploy", action="store_true", help="Build only; skip the copy step.")
    parser.add_argument("--list-mods", action="store_true", help="List available mods and exit.")
    args = parser.parse_args(dispatcher_argv)

    if args.list_mods:
        for m in list_mods():
            print(m)
        return 0

    if not args.mod:
        parser.error("mod name is required (or pass --list-mods)")

    mod_dir = MODS_DIR_REPO / args.mod
    if not mod_dir.is_dir():
        raise SystemExit(f"No mod directory at {mod_dir}.")
    # Reuse list_mods' liveness check so the nested-loader-root layout works too.
    if args.mod not in list_mods():
        raise SystemExit(
            f"{mod_dir} is not a recognized mod root (no ./gradlew at the top, and no "
            f"loader-named subfolder with its own ./gradlew either)."
        )

    manifest = load_manifest(mod_dir)
    targets = expand_companion_targets(resolve_targets(mod_dir, manifest, args.target), manifest)

    # Build each target with its required JDK, inside whichever gradle root owns that
    # target (mod_dir for the flat layout, mod_dir/<loader>/ for the nested loader-root
    # layout). Different targets in the same invocation can use different gradle roots
    # — e.g. fabric-26.1.2 from <mod>/fabric/ + forge-1.20.1 from <mod>/forge/ — each
    # with its own gradle wrapper version. Mixed-Java targets must be invoked
    # separately anyway because ForgeGradle 6 cannot run under Java 21+.
    if not targets:
        # Let gradle choose: it'll pick its own DEFAULT_TARGETS. Pick the flat root if
        # it exists; otherwise the user needs to pass --target explicitly so we know
        # which loader subroot to enter.
        if (mod_dir / "gradlew").exists():
            run_gradle(mod_dir, None, jdk_home_for("fabric-26.0", manifest), gradle_extra)
            print("[build-and-deploy] no explicit target; skipping deploy step.")
            return 0
        raise SystemExit(
            f"{mod_dir} uses the nested loader-root layout, so --target is required "
            f"(the dispatcher can't pick a single gradle root without knowing which "
            f"loader to enter). Pass --target <name> (or set default_target in "
            f"{mod_dir.name}/.mod-build.toml)."
        )

    for target in targets:
        gradle_root = gradle_root_for_target(mod_dir, target)
        run_gradle(gradle_root, target, jdk_home_for(target, manifest), gradle_extra)

    if args.no_deploy:
        print("[build-and-deploy] --no-deploy set; build only.")
        return 0

    print()

    for target in targets:
        gradle_root = gradle_root_for_target(mod_dir, target)
        root_props = parse_properties(gradle_root / "gradle.properties")
        archives_base_name = root_props["archives_base_name"]
        mod_version = root_props["mod_version"]

        jar = jar_path_for(gradle_root, archives_base_name, mod_version, target)
        if not jar.exists():
            print(f"[build-and-deploy] WARNING: expected jar not found at {jar}")
            continue

        print(f"[build-and-deploy] built jar: {jar}")

        prism_suffixes = prism_suffixes_for(target, manifest)
        if prism_suffixes:
            for suffix in prism_suffixes:
                deploy_to_prism(target, suffix, jar, archives_base_name)
        else:
            print(
                "[build-and-deploy] no prism_instance_suffix in .mod-build.toml; "
                "skipping Prism client deploy"
            )

        for extra in extra_deploy_paths_for(target, manifest):
            if extra.exists():
                print(f"[build-and-deploy] === Deploying {target} to {extra} ===")
                remove_prior_jars(extra, archives_base_name)
                deploy_jar(jar, extra)
            else:
                print(f"[build-and-deploy] skip extra deploy (not present): {extra}")

    print()
    print("[build-and-deploy] === Done. Restart Minecraft/server for changes to take effect. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
