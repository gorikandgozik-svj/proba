"""CINEMA FORGE entry point (windowed GUI + executable smoke check)."""
from __future__ import annotations


def main() -> int:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        # Run a real short local MP4 render from the packaged executable.
        # No cloud request, no key, no speech provider, no GPU requirement.
        import tempfile
        import traceback
        from pathlib import Path
        from cinema_forge.pipeline import execute, Job
        try:
            with tempfile.TemporaryDirectory(prefix='cinema_forge_smoke_') as directory:
                target = Path(directory) / 'selftest.mp4'
                result = execute(Job(
                    prompt='Cinematic silver coupe at dawn', destination=target,
                    profile='Preview 720p / 24 FPS', narration=False,
                    seconds=2, shot_seconds=1,
                ), log=lambda _: None)
                if not result.is_file() or result.stat().st_size < 2048:
                    raise RuntimeError('Packaged render produced no playable-sized MP4')
                with result.open('rb') as fh:
                    if b'ftyp' not in fh.read(64):
                        raise RuntimeError('Invalid MP4 file header')
            return 0
        except BaseException:
            # --windowed EXEs have no console; leave a diagnostic for CI.
            Path(tempfile.gettempdir(), 'CINEMA_FORGE_self_test_error.txt').write_text(
                traceback.format_exc(), encoding='utf-8')
            return 1
    from cinema_forge.app import main as desktop_main
    desktop_main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
