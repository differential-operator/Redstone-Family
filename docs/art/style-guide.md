# Vanilla-style art conventions

These are Redstone Family project conventions, not official numerical Minecraft rules.

- Use cuboid geometry, strong silhouettes and restrained pixel detail; prefer a few large forms over tiny attached parts.
- Item icons default to 16x16 RGBA PNG. Entity/armor atlases use UV-appropriate dimensions such as 64x32 or 64x64. Preserve roughly vanilla pixel density.
- Enlarge previews with nearest-neighbor sampling. No antialiasing, smooth gradients, photographic materials, noisy detail, PBR or normal maps.
- Use approximately 3-5 brightness steps per material. Pair red with dark red, stone gray, wood or iron colors; avoid saturating every surface.
- Ordinary item alpha is either 0 or 255. Slime translucency is a deliberate exception; keep inner features opaque and validate overlapping shells in game.
- First redstone slime retains the vanilla silhouette and UV layout. Use a red shell and simple core, without spikes, dynamic lighting or elaborate particles.
- Match vanilla movement rhythm. The first slime uses vanilla renderer squish, not a new keyframe system.
- Preserve user originals and provenance. Pixel normalization creates a separate output; it never replaces an original.
- Naming is lowercase snake_case, namespace redstonefamily. Avoid copying unrelated resource-pack requirements or newer game resource layouts.

The supplied redstone sword original remains outside the repository until stage 2:
D:/Documents/Minecraft Mod TempPic/redstone_sword.png.
Its 174x174 image was read-only verified as a nearest-neighbor enlargement of a 16x16 grid, with 10 RGBA colors and alpha 0/255. Recover cells using round-half-up boundaries, then verify the reconstruction before integration.
