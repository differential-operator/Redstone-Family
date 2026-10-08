# Art workflow and stage gates

## Stage 1: foundation

The repository follows the existing origin/main history; baseline-initialized marks the complete initialized mod before art tooling. No force push, destructive reset/clean, or implicit publishing is allowed. Inspect staged paths and diffs before committing. A reverse commit is preferable to destructive rollback.

Stage 1 creates conventions, model specifications, an empty asset manifest and read-only checks. No game registrations, textures or models are added. Python standard library only; no package installation, editor launch or export implementation.

Commands from the project root:

```powershell
python -m unittest discover -s tools/art -p "test_*.py"
python tools/art/art_pipeline.py validate
python tools/art/art_pipeline.py check
.\gradlew.bat clean build
python tools/art/art_pipeline.py inspect-jar
```

Gradle check depends on validateArt. Override the executable with -PartPython=C:/path/to/python.exe. Missing Python is an actionable configuration error, never an instruction to install it automatically. Every invocation checks current files; it does not depend on an editor or an environment-specific generated stamp. It is compatible with Gradle's configuration cache.

## Ownership and directories

- art/sources: immutable user originals and authoritative generated-model specifications.
- art/references: design notes and reference provenance, not shipping game resources.
- art/schemas: internal specification contracts.
- art/manifests/assets.json: asset ID, kind, source, source SHA-256, inputs (dependent source paths and SHA-256), generator ID, output paths and output SHA-256. Initially empty. Native models must list their texture in inputs so a texture-only edit also marks exports stale.
- tools/art: reproducible generators and checks. No export generator exists in stage 1.
- docs/art: workflow, style rules, observed tools and test evidence.
- build/art: disposable future staging and previews, ignored by Git.

Sources are relative to art/sources. Outputs are project-relative and restricted to src/main/resources/assets/redstonefamily, src/main/resources/data/redstonefamily, src/generated/resources/assets/redstonefamily, src/generated/resources/data/redstonefamily, or src/main/java/com/redstonefamily/client. Resource logical paths must not collide between main and generated roots. Each output belongs to exactly one asset/generator. A matching output hash detects manual edits; a changed source hash detects stale exports. Adoption of a hand-written file must be explicit before recording its original hash, not silently claimed by a generator.

Paths use forward slashes; absolute paths, backslashes, traversal, symbolic links escaping the allowed root and case-folded collisions are rejected. Do not edit generated outputs directly. Switching a model to manual bbmodel editing requires an explicit ownership change and preservation of the previous source.

validate checks contracts, paths, hierarchy, UV bounds, input presence and JSON/PNG structure. PNG checks cover signature, IHDR dimensions, chunk CRCs and terminator, not decoded pixel colors/alpha or artistic quality; pixel checks arrive with Pillow in stage 2. check adds source/dependency/output hashes and fixed toolchain versions. Both validate/check scan resource namespaces, legacy data directories, logical collisions and local model/texture references. Vanilla references come from Minecraft and are not duplicated in this repository. Empty manifests pass while explicitly reporting zero exported assets. inspect-jar verifies the built JAR independently. CLI checks do not write files, create directories, install tools or launch a game/editor.

## Model specification v1

model-spec-v1.schema.json is JSON Schema draft 2020-12 for a project-internal specification, not a bbmodel, Bedrock or GeckoLib loader format. Its $defs.manifest also describes the asset manifest. The standard-library validator deliberately implements only the schema keywords used here and rejects unknown validation keywords. Schema version changes require code/tests/docs changes together.

Top-level fields: schema_version=1, id=redstonefamily:<snake_case>, target=native_entity, texture, parts, animation. Texture source is a PNG relative to art/sources; width and height are positive integers. Each part has a unique name, nullable parent, pivot, rotation and cubes. Each cube has name, origin, size, UV offset and mirror. Cube names are unique within a part; parent names must resolve and the graph must be acyclic. At least one cube is required across the model.

Coordinates use native Java conventions: X right, Y down, Z back; 16 units equal one block. Part pivot is parent-relative and cube origin is part-relative. Geometry and UV offsets are integers; sizes are positive. Rotations are degrees and future Java export converts them to radians. Only box UV is supported. Atlas extents are u + 2*(width+depth), v + height+depth. Free meshes, per-face arbitrary UV and Molang are outside v1.

Animation is {type: procedural, profile: vanilla_slime, parameters: {}}. This freezes vanilla renderer squish; no tunable numeric values are currently defined. A later profile must explicitly define its parameter keys. Stage 1 stores no actual model spec; test fixtures are in-memory or temporary data only.

## Later stages and temporary baselines

2. Redstone sword: preserve the user's original, normalize to 16x16, generate handheld JSON and translations, integrate SwordItem. The temporary diamond baseline uses Tiers.DIAMOND and SwordItem.createAttributes(Tiers.DIAMOND, 3, -2.4F): total damage 7, attack speed 1.6, durability 1561, enchantability 10, diamond repair. It is not final balance or a recipe decision. Install a pinned Pillow only in a project-local environment at this stage.
3. Redstone slime: inherit vanilla Slime jumping, hostility, size and splitting; retain original inner/outer models and 64x32 atlas, native renderer squish and translucent outer layer. Test drops match the vanilla baseline (smallest size only slime balls). No natural spawning, egg, custom sounds or new particles. These behaviors and drops are not final gameplay. Test sizes 1/2/4, saving, splitting, daylight/night, overlaps, client and dedicated server.
4. Automatic modeling: implement only the defined cuboid subset. Export bbmodel and Java geometry from the same source; select and record a stable Blockbench version, test open/save/reopen and UV coordinates before replacing native baseline geometry. bbmodel does not load directly in Minecraft. Vanilla slime animation remains code-driven.
5. Optional experiments: only when separately authorized, test pinned Blockbench MCP and GeckoLib 4 compatible with Minecraft 1.21.1/NeoForge in independent samples. Documentation-confirmed support is not local runtime verification. Retain the native fallback; do not upgrade the core toolchain to accommodate plugins. Blender is unnecessary for the baseline workflow.
6. Armor: use ArmorItem/ArmorMaterial and conventional layer_1/layer_2 textures, separate 16x16 icons; temporary diamond properties. No later-version equipment JSON. Test worn movement, armor stands and enchanted rendering before advanced models.
7. Structures: begin with a 9x7x9 oak/cobblestone/red-terracotta hut from layout JSON to compressed Java NBT. Verify template rotations/mirrors before enabling native jigsaw generation in a separate confirmed step. The planned initial generation baseline is Overworld plains, spacing 32, separation 8 and a fixed unique salt. Test new chunks/worlds and do not overwrite existing structures.

Every stage ends with an independent local commit, evidence report and user confirmation. Only the current stage is authorized. First push additionally requires an explicit user confirmation of the commit summary.

## Evidence and limitations

Automated checks reject broken data but cannot establish artistic quality. Later stages must pass source/UV checks, deterministic export checks, previews, Gradle/JAR validation, client rendering and dedicated-server loading as applicable. Use an independent test world, resource reload for resource-only edits, and a client restart for Java edits. User visual review is the final gate. No stage-1 game launch is required because no rendering code is changed.

Documentation references: NeoForge 1.21.1 model docs (https://docs.neoforged.net/docs/1.21.1/resources/client/models/), Blockbench bbmodel docs (https://blockbench.net/wiki/docs/bbmodel/), GeckoLib 4 installation (https://github.com/bernie-g/geckolib/wiki/Installation-%28Geckolib4%29). Prefer local mapped 1.21.1 source for concrete signatures. No third-party plugin compatibility has been established locally.
