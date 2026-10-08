"""Read-only stage-1 art contracts, freshness and JAR checks; standard library only."""

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = "art/schemas/model-spec-v1.schema.json"
MANIFEST_PATH = "art/manifests/assets.json"
OUTPUT_ROOTS = (
    "src/main/resources/assets/redstonefamily",
    "src/main/resources/data/redstonefamily",
    "src/generated/resources/assets/redstonefamily",
    "src/generated/resources/data/redstonefamily",
    "src/main/java/com/redstonefamily/client",
)
RESOURCE_ROOTS = ("src/main/resources", "src/generated/resources")
FIXED = {
    "minecraft": "1.21.1", "neoforge": "21.1.235", "neogradle": "7.1.38",
    "gradle": "9.2.1", "java_target": 21,
    "parchment_minecraft": "1.21.1", "parchment_mappings": "2024.11.17",
}


class ValidationError(ValueError):
    """Actionable contract or resource error."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def read_json(path):
    def reject_constant(value):
        raise ValidationError(f"{path}: non-finite JSON number {value}")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"{path}: duplicate JSON key {key}")
            result[key] = value
        return result

    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{path}: {exc}") from exc


def matches_type(value, kind):
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "integer": lambda: type(value) is int,
        "number": lambda: type(value) in (int, float) and math.isfinite(value),
        "boolean": lambda: type(value) is bool,
        "null": lambda: value is None,
    }[kind]()


def validate_schema(value, schema, document=None, where="$", depth=0):
    """Implement ONLY the documented project's JSON Schema subset, fail on unknown keywords."""
    require(depth < 100, f"{where}: schema/data nesting too deep")
    document = document if document is not None else schema
    supported = {"$schema", "$id", "title", "description", "$defs", "$ref", "type",
                 "const", "enum", "properties", "required", "additionalProperties",
                 "items", "minItems", "maxItems", "minimum", "minLength", "pattern"}
    require(not (set(schema) - supported), f"{where}: unsupported schema keywords {set(schema) - supported}")
    if "$ref" in schema:
        ref = schema["$ref"]
        require(ref.startswith("#/$defs/"), f"{where}: unsupported reference {ref}")
        name = ref.removeprefix("#/$defs/")
        require(name in document.get("$defs", {}), f"{where}: unresolved schema reference {ref}")
        validate_schema(value, document["$defs"][name], document, where, depth + 1)
    if "type" in schema:
        kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        require(any(matches_type(value, kind) for kind in kinds), f"{where}: expected type {kinds}")
    if "const" in schema:
        require(value == schema["const"], f"{where}: expected {schema['const']!r}")
    if "enum" in schema:
        require(value in schema["enum"], f"{where}: invalid choice {value!r}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        missing = set(schema.get("required", [])) - set(value)
        require(not missing, f"{where}: missing fields {sorted(missing)}")
        extra = set(value) - set(props)
        additional = schema.get("additionalProperties", True)
        require(additional is not False or not extra, f"{where}: unexpected fields {sorted(extra)}")
        for key, item in value.items():
            child = props.get(key, additional if isinstance(additional, dict) else None)
            if child is not None:
                validate_schema(item, child, document, f"{where}.{key}", depth + 1)
    elif isinstance(value, list):
        require(len(value) >= schema.get("minItems", 0), f"{where}: too few items")
        require(len(value) <= schema.get("maxItems", len(value)), f"{where}: too many items")
        for index, item in enumerate(value):
            if "items" in schema:
                validate_schema(item, schema["items"], document, f"{where}[{index}]", depth + 1)
    elif isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0), f"{where}: string too short")
        require("pattern" not in schema or re.search(schema["pattern"], value) is not None,
                f"{where}: invalid string {value!r}")
    elif type(value) in (int, float):
        require(math.isfinite(value), f"{where}: non-finite number")
        require("minimum" not in schema or value >= schema["minimum"], f"{where}: below minimum")


def safe_path(base, relative):
    require(isinstance(relative, str) and relative, "empty path")
    require("\\" not in relative and ":" not in relative, f"invalid portable path: {relative}")
    require(all(part not in ("", ".", "..") for part in relative.split("/")), f"invalid relative path: {relative}")
    logical = PurePosixPath(relative)
    require(not logical.is_absolute(), f"absolute path forbidden: {relative}")
    resolved = (base / relative).resolve()
    require(resolved.is_relative_to(base.resolve()), f"path escapes its root: {relative}")
    return resolved


def hash_file(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValidationError(f"cannot hash {path}: {exc}") from exc


def png_size(path):
    """Validate PNG chunk structure/CRC and return IHDR dimensions, without pixel decoding."""
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"{path}: invalid PNG signature")
    pos, size, saw_data, ended = 8, None, False, False
    while pos < len(data):
        require(pos + 12 <= len(data), f"{path}: truncated PNG chunk")
        length = struct.unpack_from(">I", data, pos)[0]
        end = pos + 12 + length
        require(end <= len(data), f"{path}: truncated PNG payload")
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        crc = struct.unpack_from(">I", data, pos + 8 + length)[0]
        require(zlib.crc32(kind + payload) & 0xffffffff == crc, f"{path}: PNG CRC mismatch")
        if pos == 8:
            require(kind == b"IHDR" and length == 13, f"{path}: missing IHDR")
            width, height, bits, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            require(width > 0 and height > 0, f"{path}: invalid PNG dimensions")
            allowed_bits = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            require(color in allowed_bits and bits in allowed_bits[color], f"{path}: invalid PNG color format")
            require(compression == 0 and filtering == 0 and interlace in (0, 1), f"{path}: unsupported PNG header")
            size = (width, height)
        elif kind == b"IHDR":
            raise ValidationError(f"{path}: duplicate IHDR")
        if kind == b"IDAT":
            saw_data = True
        if kind == b"IEND":
            require(length == 0 and end == len(data), f"{path}: invalid IEND or trailing data")
            ended = True
            break
        pos = end
    require(ended and saw_data and size is not None, f"{path}: incomplete PNG")
    return size


def validate_model(model, schema, source_root):
    validate_schema(model, schema)
    texture = model["texture"]
    texture_path = safe_path(source_root, texture["source"])
    require(texture_path.is_file(), f"missing texture source: {texture_path}")
    require(png_size(texture_path) == (texture["width"], texture["height"]), "texture dimensions differ from model")
    names = [part["name"] for part in model["parts"]]
    require(len(names) == len(set(names)), "duplicate part name")
    parents = {part["name"]: part["parent"] for part in model["parts"]}
    count = 0
    for part in model["parts"]:
        seen, node = set(), part["name"]
        while node is not None:
            require(node in parents, f"missing parent: {node}")
            require(node not in seen, f"parent cycle at {node}")
            seen.add(node)
            node = parents[node]
        cubes = part["cubes"]
        cube_names = [cube["name"] for cube in cubes]
        require(len(cube_names) == len(set(cube_names)), f"duplicate cube in {part['name']}")
        for cube in cubes:
            width, height, depth = cube["size"]
            u, v = cube["uv"]
            require(u + 2 * (width + depth) <= texture["width"] and v + height + depth <= texture["height"],
                    f"UV outside atlas: {part['name']}/{cube['name']}")
        count += len(cubes)
    require(count > 0, "model contains no cubes")


def output_key(relative):
    for prefix in RESOURCE_ROOTS:
        if relative.startswith(prefix + "/"):
            return "resource/" + relative[len(prefix) + 1:].casefold()
    return relative.casefold()


def inspect_file(path):
    if path.suffix == ".json":
        read_json(path)
    elif path.suffix == ".png":
        png_size(path)


def validate_manifest(root, schema, fresh=False):
    manifest = read_json(root / MANIFEST_PATH)
    validate_schema(manifest, schema["$defs"]["manifest"], schema)
    asset_ids, owners = set(), set()
    for asset in manifest["assets"]:
        require(asset["id"] not in asset_ids, f"duplicate asset ID: {asset['id']}")
        asset_ids.add(asset["id"])
        source = safe_path(root / "art/sources", asset["source"])
        require(source.is_file(), f"missing source: {source}")
        if asset["kind"] == "native_entity":
            model = read_json(source)
            require(model.get("id") == asset["id"], "model and manifest IDs differ")
            validate_model(model, schema, root / "art/sources")
        else:
            inspect_file(source)
        dependencies = {}
        for dependency in asset["inputs"]:
            path = safe_path(root / "art/sources", dependency["path"])
            require(path.is_file(), f"missing input dependency: {path}")
            key = dependency["path"].casefold()
            require(key not in dependencies, f"duplicate input dependency: {key}")
            dependencies[key] = dependency
            if fresh:
                require(hash_file(path) == dependency["sha256"], f"stale export: input dependency changed for {asset['id']}")
        if asset["kind"] == "native_entity":
            require(model["texture"]["source"].casefold() in dependencies, "model texture must be tracked as an input dependency")
        if fresh:
            require(hash_file(source) == asset["source_sha256"], f"stale export: source changed for {asset['id']}")
        for output in asset["outputs"]:
            relative = output["path"]
            target = safe_path(root, relative)
            allowed = [prefix for prefix in OUTPUT_ROOTS if relative.startswith(prefix + "/")]
            require(allowed, f"output outside allowed namespace/client roots: {relative}")
            require(target.is_relative_to((root / allowed[0]).resolve()), f"output symlink escapes allowed root: {relative}")
            require(re.fullmatch(r"[a-z0-9_./]+", relative) is not None or
                    relative.startswith("src/main/java/com/redstonefamily/client/") and target.suffix == ".java",
                    f"invalid output filename: {relative}")
            require(target.name != ".gitkeep" and target.suffix not in (".bbmodel", ".bbmodelbackup"), "source/placeholder cannot be an output")
            key = output_key(relative)
            require(key not in owners, f"duplicate output owner: {relative}")
            owners.add(key)
            require(target.is_file(), f"missing exported output: {target}")
            inspect_file(target)
            if fresh:
                require(hash_file(target) == output["sha256"], f"output changed/stale: {relative}")
    return len(asset_ids)


def resource_check(root):
    logical_paths = set()
    models = {}
    for directory in RESOURCE_ROOTS:
        resource_root = root / directory
        if not resource_root.exists():
            continue
        for path in sorted(resource_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(resource_root)
            if path.name == ".gitkeep" or ".cache" in rel.parts or path.suffix == ".bbmodel":
                continue
            require(path.resolve().is_relative_to(resource_root.resolve()), f"resource escapes root: {path}")
            key = rel.as_posix().casefold()
            require(key not in logical_paths, f"duplicate resource between roots/cases: {rel}")
            logical_paths.add(key)
            if rel.parts[0] in ("assets", "data"):
                require(len(rel.parts) >= 3 and rel.parts[1] == "redstonefamily", f"unexpected namespace: {rel}")
                require(re.fullmatch(r"[a-z0-9_./]+", rel.as_posix()) is not None, f"invalid resource path: {rel}")
                if rel.parts[0] == "data":
                    require(rel.parts[2] not in {"structures", "recipes", "loot_tables", "advancements", "predicates", "functions", "item_modifiers"},
                            f"pre-1.21 data directory: {rel}")
                    if rel.parts[2] == "tags" and len(rel.parts) > 3:
                        require(rel.parts[3] not in {"items", "blocks", "entity_types", "fluids", "functions", "game_events"}, f"pre-1.21 tag directory: {rel}")
            inspect_file(path)
            if len(rel.parts) >= 4 and rel.parts[:3] == ("assets", "redstonefamily", "models") and path.suffix == ".json":
                models[rel.as_posix()] = read_json(path)
    def reference_path(reference, category, suffix):
        require(isinstance(reference, str), "model reference must be a string")
        match = re.fullmatch(r"(?:(minecraft|redstonefamily):)?([a-z0-9_/]+)", reference)
        require(match is not None and all(part not in ("", ".", "..") for part in match.group(2).split("/")), f"invalid model reference: {reference}")
        if (match.group(1) or "minecraft") == "minecraft":
            return None
        key = f"assets/redstonefamily/{category}/{match.group(2)}{suffix}"
        require(key.casefold() in logical_paths, f"missing model/texture reference: {reference}")
        return key
    parents = {}
    for key, model in models.items():
        require(isinstance(model, dict), f"model JSON must be an object: {key}")
        parents[key] = reference_path(model["parent"], "models", ".json") if "parent" in model else None
        textures = model.get("textures", {})
        require(isinstance(textures, dict), f"model textures must be an object: {key}")
        for value in textures.values():
            require(isinstance(value, str), f"model texture reference must be a string: {key}")
            if not value.startswith("#"):
                reference_path(value, "textures", ".png")
    for key in parents:
        seen, current = set(), key
        while current is not None:
            require(current not in seen, f"model parent cycle: {current}")
            seen.add(current)
            current = parents.get(current)
    return len(logical_paths)


def check_versions(root):
    recorded = read_json(root / "docs/art/toolchain.json")
    for key, value in FIXED.items():
        require(recorded.get(key) == value, f"toolchain record changed: {key}")
    props = {}
    for line in (root / "gradle.properties").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    expected = {"minecraft_version": "1.21.1", "neo_version": "21.1.235", "mod_id": "redstonefamily",
                "mod_group_id": "com.redstonefamily", "neogradle.subsystems.parchment.minecraftVersion": "1.21.1",
                "neogradle.subsystems.parchment.mappingsVersion": "2024.11.17"}
    for key, value in expected.items():
        require(props.get(key) == value, f"fixed property changed: {key}")
    build = (root / "build.gradle").read_text(encoding="utf-8")
    require(re.search(r"id\s+['\"]net\.neoforged\.gradle\.userdev['\"]\s+version\s+['\"]7\.1\.38['\"]", build), "NeoGradle version changed")
    require(re.search(r"java\.toolchain\.languageVersion\s*=\s*JavaLanguageVersion\.of\(21\)", build), "Java target changed")
    wrapper = (root / "gradle/wrapper/gradle-wrapper.properties").read_text(encoding="utf-8")
    require(re.search(r"^distributionUrl=.*?/gradle-9\.2\.1-bin\.zip\s*$", wrapper, re.M), "Gradle Wrapper version changed")


def inspect_jar(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(archive.testzip() is None, "JAR CRC check failed")
        require("com/redstonefamily/RedstoneFamily.class" in names, "missing mod entry point")
        for name in names:
            require(not re.search(r"examplemod|ExampleMod|com/example/|(^|/)(art|tools|docs|\.cache)/|\.gitkeep|\.bbmodel$|\.py$|AGENTS\.md$", name), f"unexpected JAR entry: {name}")
        metadata = archive.read("META-INF/neoforge.mods.toml").decode("utf-8")
        require("${" not in metadata, "unexpanded mod metadata")
        require('modId="redstonefamily"' in metadata and 'displayName="Redstone Family"' in metadata, "wrong mod identity")
        for entry in archive.infolist():
            if entry.filename.endswith(".class"):
                data = archive.read(entry)
                require(data[:4] == b"\xca\xfe\xba\xbe" and int.from_bytes(data[6:8], "big") == 65, f"class is not Java 21: {entry.filename}")
    return len(names)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "check", "export", "inspect-jar"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="alias for freshness checks with validate")
    parser.add_argument("--jar", type=Path, help="JAR path; default build/libs/redstonefamily-1.0.0.jar")
    args = parser.parse_args(argv)
    try:
        require(args.command != "export", "Export is not implemented in stage 1; no files were written.")
        root = args.root.resolve()
        if args.command == "inspect-jar":
            count = inspect_jar(args.jar or root / "build/libs/redstonefamily-1.0.0.jar")
            print(f"JAR validation passed ({count} entries; Java 21; correct metadata; no art sources/tools/placeholders).")
            return 0
        schema = read_json(root / SCHEMA_PATH)
        fresh = args.command == "check" or args.check
        count = validate_manifest(root, schema, fresh)
        resources = resource_check(root)
        if fresh:
            check_versions(root)
        print(f"Art {args.command} passed: {count} assets, {resources} resource files. Read-only; no export performed.")
        if count == 0:
            print("Manifest is empty: zero exported assets. This does not certify any model or texture.")
        return 0
    except (ValidationError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Art validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
