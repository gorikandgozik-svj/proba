# CINEMA FORGE 0.1 — Windows Desktop Video Studio

A real Python desktop application to split **one prompt** into 12 shots, produce a 120-second timeline, synthesize narration, and export MP4. The cloud engine uses the **paid Runway Developer API** (including Kling 3.0 4K via Runway) for AI-generated footage. The no-key **Preview** engine produces animated title-card motion graphics and is **not AI camera footage**. There are no bundled video foundation model weights.

## Status — read before downloading

* ✅ Desktop GUI with progress, logs, cancel action, file selection and resume/cache of rendered segments.
* ✅ Storyboard templates for twelve 10-second shots; all shots are derived from one prompt.
* ✅ Windows `.exe` build configuration via GitHub Actions; actual completion is determined by CI.
* ✅ Output resolution **3840×2160**, **60 FPS** (export settings). If the cloud model supplies 24fps, output frames are repeated; this is not genuine newly generated 60fps footage.
* ✅ Optional online neural narration via `edge-tts`; individual selectable languages: Russian, English, Spanish, Italian and German. Online voice inventory depends on the upstream provider. **70 distinct native Russian neural speakers are NOT bundled or promised.**
* ⚠️ Cloud output incurs provider API charges for **each scene**. API key is supplied at runtime and isn't saved to project files.
* ⚠️ Continuity of people, clothes and objects between independently generated scenes is prompted but cannot be guaranteed. Lip-sync and automatic character-to-speaker casting are not implemented.
* ⚠️ The full 120s/4K/60 pipeline requires substantial time, storage, and cloud credits. The `.exe` itself does not provide unlimited GPU power.
* ⚠️ Do not claim a tested Windows binary until CI build and on-device smoke testing succeed.

## Run from source

Install Python 3.12, then:

```bat
py -m pip install -r requirements.txt
py launch.py
```

Select **Preview (motion graphics)** for no-key operation (network is still needed if narration is checked). For real AI-generated motion, select **Cloud AI video**, choose a compatible Runway model, paste your `RUNWAYML_API_SECRET` in the application (not stored on disk), acknowledge that this incurs charges, and click **Создать фильм**. For CPU-limited machines, start with 720p/24. The built EXE bundles FFmpeg via `imageio-ffmpeg`, so you do not need to install FFmpeg separately.

## Development and tests

```bat
py -m pip install -r requirements-build.txt
py -m pytest -q tests
pyinstaller --noconfirm --clean --onefile --windowed --name CINEMA_FORGE --collect-binaries imageio_ffmpeg --collect-data imageio_ffmpeg --collect-data edge_tts launch.py
```

The unit tests mock external API calls; **they do not assert successful live video generation, paid account entitlements, Windows SmartScreen acceptance, or studio-grade quality**. When CI finishes, download `CINEMA_FORGE.exe` from the workflow artifact or the GitHub pre-release.

## Privacy, licenses, safety

Prompts are sent to Runway only in Cloud mode, and narration text goes to the online voice provider when narration is on. API keys are not written to the manifest. FFmpeg and third-party libraries each have their own licenses; review them before commercial distribution. The project should not be used to impersonate real speakers without their permission.

## Known limitations

No generative video or downloadable 70+ Russian TTS speakers without paid services or powerful local GPUs. No scene-to-scene reference images, advanced continuity control, video-to-video editing, lip sync, music licensing, video interpolation, key storage or credit-usage estimator yet. Preview is primarily a render-path demonstration, not a photorealistic fallback. No assertion of zero bugs.
