# GoodEcho

Rollback audio buffer that never leaves RAM unless you save a clip. Runs its
capture in a Shizuku shell-uid service so it does not conflict with other
apps' audio detection.

- Jetpack Compose + Material 3, dynamic color (Material You), AMOLED black option
- Cache limit: linked sliders (minutes <-> RAM MB), min 30 min, max 30% of heap
- Quick Settings tile to save a clip with configurable rollback length
- Auto-start on boot with Shizuku

## Workflow
Edit `tools/generate.py` (the whole project is generated from it), run
`python3 tools/generate.py`, commit. CI builds the APK on every push and
uploads it as an artifact. Never hand-edit generated files.

Generated. Do not edit emitted sources by hand.
