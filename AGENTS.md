# Redstone Family development instructions

## Scope and stage gates

- Work only on the stage explicitly authorized by the user. After completing a stage, report evidence and wait for user confirmation before starting the next stage.
- Stage 1 is art specifications and validation only: no game content, model/texture exports, or third-party tool installation.
- Do not install GeckoLib, Blockbench MCP, or Blender ahead of a separately authorized stage.
- Redstone sword diamond properties, vanilla redstone slime behavior and test drops, and diamond-equivalent test armor are temporary technical baselines, not final gameplay decisions.

## Fixed environment

- Minecraft 1.21.1; NeoForge 21.1.235; NeoGradle 7.1.38; Gradle Wrapper 9.2.1; Java target 21; Parchment 1.21.1 / 2024.11.17.
- Mod ID redstonefamily, package com.redstonefamily. Do not upgrade versions or regenerate the wrapper without explicit authorization.
- No new mechanical or redstone functional blocks. No unapproved runtime dependencies.

## Git and source ownership

- Confirm baseline-initialized and inspect the working tree before implementing changes. Preserve user changes and remote history.
- Do not force-push or perform destructive reset/clean. Pushing requires the user's authorization; show the first push summary before requesting it.
- Keep art sources in art/sources, references in art/references, and build artifacts in build/art. Never overwrite user originals.
- Every asset has one authoritative source and one generator in art/manifests/assets.json. Never hand-edit generated output or let two generators own one path.
- A manual bbmodel edit requires an explicit ownership switch. Preserve sources and provenance; do not silently regenerate over it.
- Manifest hashes refer to file bytes. Generation must be deterministic, with stable ordering, identifiers and random seeds.
- Specs use model-spec-v1.schema.json and documented coordinates. Changes to the spec require matching validator, documentation and migration updates.

## Art style

- Follow docs/art/style-guide.md: vanilla-like cuboids, readable silhouettes, restrained palettes and pixel detail.
- Default item icons are 16x16. Entity/armor atlases follow UV needs, usually 64x32 or 64x64, rather than being forced to 16x16.
- Use nearest-neighbor previews. No antialiasing, photographic textures, smooth gradients, PBR or normal maps.
- Ordinary item alpha is 0/255. Translucent entity shells are explicit exceptions with separate opaque inner geometry.
- Use lowercase snake_case resource paths and the redstonefamily namespace. Keep art sources, tools and caches out of the JAR.

## Integration and verification

- Check local mapped 1.21.1 sources and version-specific official documentation before using APIs. Do not copy newer item/equipment rendering systems.
- Common code must not import client classes; register models/renderers only on the client through the appropriate mod events.
- Distinguish locally verified capabilities, source/documentation-confirmed capabilities and untested capabilities, especially for MCP, Blockbench exports and GeckoLib.
- Commands: python -m unittest discover -s tools/art -p "test_*.py"; python tools/art/art_pipeline.py validate; python tools/art/art_pipeline.py check; .\gradlew.bat clean build; python tools/art/art_pipeline.py inspect-jar.
- Art checks are read-only and must not install dependencies or launch editor/MCP tools. The exporter remains unavailable in stage 1.
- Use -PartPython=<absolute Python path> when Gradle cannot resolve Python. Do not silently install an interpreter.
- Build success proves compilation and packaging, not visual correctness. Later stages require independent-world client checks, server loading checks and user visual approval.
- Report sources, outputs, tests, commit summary, risks and unverified items. Stop at the stage boundary.
