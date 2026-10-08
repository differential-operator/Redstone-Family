# Stage 1 validation — 2026-10-08

## Git history and baseline

- origin: https://github.com/differential-operator/Redstone-Family.git
- Existing remote main commit: 2911612677a29c008b272ff7f38b30b8a95f31e6 (Initial commit).
- Local baseline: e2a04cb (chore: preserve initialized Redstone Family baseline), tagged baseline-initialized.
- The local main branch starts at the fetched remote commit; its index was populated without replacing the local working files. The complete project baseline is a descendant of the original remote history.
- Local detailed README preserved, including the original remote repository title and link.
- Commit identity is repository-local differential-operator / 254057043+differential-operator@users.noreply.github.com. No global identity change.
- gradlew has executable mode 100755 for Linux CI. The wrapper contents and versions were not upgraded.
- No push performed. First push requires user confirmation; authentication for fetching the public repository was not needed. Push authentication and remote CI remain untested.

## Checks performed

| Check | Result |
| --- | --- |
| Existing project build before baseline | BUILD SUCCESSFUL |
| Python unittest discovery | 27 tests passed |
| art_pipeline.py validate | Passed; zero assets, two current resource files |
| art_pipeline.py check | Passed; source/output contracts and fixed versions |
| gradlew.bat clean build | BUILD SUCCESSFUL; validateArt executed |
| gradlew.bat validateArt repeated for configuration-cache compatibility | Passed; configuration cache reused |
| art_pipeline.py inspect-jar | Passed; 21 entries, correct metadata and Java 21 entry point |
| Baseline diff of source/resources, settings, version properties and wrapper properties | No differences |
| Ignore-rule checks | Caches, output, development worlds, virtual environments, Python caches and common credential paths ignored |
| git diff --check | Passed |

The JAR contains no template content, art sources, tools, documentation, bbmodel files or gitkeep placeholders. All compiled classes target Java 21 (major version 65).

No model or texture was generated; the original sword image was not copied or modified. Test fixtures are temporary synthetic data, not production art. No Pillow, Blockbench, MCP, GeckoLib or Blender installation was performed.

## Limits and stage gate

The schema validator supports only the documented project schema subset. PNG checks are structural and do not decode pixel colors or alpha. No exporter or generic modeler is implemented. Empty-manifest validation must not be interpreted as proof of completed art.

Gradle reported deprecated features in its existing plugin/build environment; the approved toolchain was kept unchanged. Client and dedicated server were not launched because stage 1 changes no game content/rendering code. Remote CI has not run for these local commits.

Stage 1 stops here pending user confirmation. Stage 2, including the first sword texture integration and project-local Pillow setup, is not authorized yet.
