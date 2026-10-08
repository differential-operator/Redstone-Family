# Redstone Family

GitHub repository: [differential-operator/Redstone-Family](https://github.com/differential-operator/Redstone-Family).
The original GitHub README titled this repository "Redstone-Family"; this document retains the local development guide.

A Minecraft mod project focused on redstone-themed creatures, weapons, and equipment.
Naturally generated redstone huts may be added later. No mechanical or redstone functional blocks are planned.
The current foundation registers no game content and includes no third-party mod dependencies.

## Project identity

- Mod ID: redstonefamily
- Java base package / Maven group: com.redstonefamily
- Mod version: 1.0.0
- Mod license: All Rights Reserved
- Gradle project name: Redstone Family

## Development environment

- Windows 11
- Minecraft Java Edition: 1.21.1
- NeoForge: 21.1.235
- Java: Temurin JDK 21 (verified locally with 21.0.11)
- NeoGradle userdev plugin: 7.1.38
- Gradle Wrapper: 9.2.1
- Parchment mappings: Minecraft 1.21.1 / 2024.11.17

Use the checked-in Gradle Wrapper. Keep these versions unchanged unless an upgrade is explicitly planned.

## Commands (PowerShell)

Build from the project root:

```powershell
.\gradlew.bat clean build
```

The mod JAR is written to build/libs/redstonefamily-1.0.0.jar.

Start the development client when needed:

```powershell
.\gradlew.bat runClient
```

The GameTest server configuration is retained, but should only be run after game tests are implemented.

## Source layout

Java sources are under src/main/java/com/redstonefamily:

| Package / class | Purpose |
| --- | --- |
| RedstoneFamily | Common entry point, Mod ID, and logger |
| registry | Future content registration |
| entity | Future creature behavior |
| item | Future weapons and equipment |
| client | Client-only renderers, models, and presentation |
| event | Future common event handlers |
| worldgen | Future structures and world generation |

Do not import client-only Minecraft classes into the common entry point or common packages.
Future client registration must be restricted to the client distribution so dedicated servers can load the mod safely.

Resources are under src/main/resources:

| Path | Purpose |
| --- | --- |
| META-INF/neoforge.mods.toml | Required NeoForge metadata |
| assets/redstonefamily/lang | Translations; en_us.json is currently empty |
| assets/redstonefamily/textures/entity | Future creature textures |
| assets/redstonefamily/textures/item | Future item textures |
| assets/redstonefamily/models/item | Future vanilla item model JSON |
| assets/redstonefamily/geo | Reserved for future GeckoLib model exports |
| assets/redstonefamily/animations | Reserved for future animation exports |
| data/redstonefamily/structure | Future structure NBT templates (1.21.1 singular directory name) |
| data/redstonefamily/worldgen | Future world generation definitions |

Generated data resources will go under src/generated/resources, as configured in Gradle.
Empty resource directories use .gitkeep placeholders, excluded from packaged resources.
Blockbench .bbmodel source projects are also excluded from packaged resources.
Reserved geometry and animation directories do not install or enable GeckoLib.

## Licenses and mappings

The mod license remains All Rights Reserved. TEMPLATE_LICENSE.txt retains the original NeoForge MDK template license.
Minecraft mappings supplied by Mojang have their own license. Refer to the mapping files or the
[NeoForm reference copy](https://github.com/NeoForged/NeoForm/blob/main/Mojang.md).
Parchment mappings are configured separately in gradle.properties.
