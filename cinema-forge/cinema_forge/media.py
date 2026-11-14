"""FFmpeg rendering. Export dimensions and fps are technical output settings, not native AI quality."""
from pathlib import Path
import hashlib
import math
import subprocess
import time
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

PROFILES = {
    'Preview 720p / 24 FPS': (1280, 720, 24),
    'Full HD / 30 FPS': (1920, 1080, 30),
    '4K UHD / 60 FPS': (3840, 2160, 60),
}


def ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str], *, cancel=None, logger=None, timeout=14400) -> None:
    if logger:
        logger('FFmpeg: ' + ' '.join(args[1:5]) + ' ...')
    command = [ffmpeg(), '-hide_banner', '-nostdin', '-loglevel', 'error', '-y'] + args
    # Redirect stderr to file: a pipe can deadlock if it fills while we poll.
    import tempfile
    with tempfile.TemporaryFile(mode='w+b') as errors:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=errors)
        start = time.monotonic()
        try:
            while proc.poll() is None:
                if cancel is not None and cancel.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise InterruptedError('Операция отменена.')
                if time.monotonic() - start > timeout:
                    proc.kill()
                    raise TimeoutError('FFmpeg не завершил рендер в установленный защитный лимит.')
                time.sleep(0.2)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        if proc.returncode != 0:
            errors.seek(0)
            tail = errors.read()[-6000:].decode('utf-8', errors='replace')
            raise RuntimeError(f'FFmpeg (код {proc.returncode}): {tail}')


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        'C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/segoeui.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int = 4) -> list[str]:
    words = text.split()
    if not words:
        return ['']
    lines = []
    current = ''
    for word in words:
        trial = (current + ' ' + word).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] > width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while draw.textbbox((0, 0), lines[-1] + '…', font=font)[2] > width and lines[-1]:
            lines[-1] = lines[-1][:-1]
        lines[-1] += '…'
    return lines


def poster(prompt: str, scene_index: int, count: int, dst: Path) -> None:
    """Local fallback: original animated title cards, not synthesized camera footage."""
    w, h = 1280, 720
    digest = hashlib.sha256((prompt + str(scene_index)).encode('utf-8')).digest()
    palette = [(9, 14, 29), (20, 33, 59), (8, 59, 74), (29, 24, 65)]
    base = palette[digest[0] % len(palette)]
    accent = (70 + digest[1] // 3, 130 + digest[2] // 3, 170 + digest[3] // 4)
    im = Image.new('RGB', (w, h), base)
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        col = tuple(int(base[k] * (1-t) + accent[k] * t * 0.28) for k in range(3))
        d.line((0, y, w, y), fill=col)
    for i in range(5):
        x = int((digest[4+i] / 255) * w)
        r = 160 + i * 75
        c = tuple(min(255, int(v * 0.33)) for v in accent)
        d.ellipse((x-r, h//2-r+i*45, x+r, h//2+r+i*45), outline=c, width=3)
    d.rounded_rectangle((70, 58, 325, 101), radius=18, fill=(27, 44, 60))
    d.text((92, 66), 'CINEMA FORGE  •  PREVIEW', font=_font(17), fill=(207, 222, 237))
    d.text((71, 194), f'SCENE  {scene_index:02d} / {count:02d}', font=_font(22), fill=accent)
    f = _font(44)
    for n, line in enumerate(_wrap(d, prompt, f, w-148, 4)):
        d.text((70, 257 + n*64), line, font=f, fill=(247, 249, 254))
    d.line((70, 642, 1208, 642), fill=(80, 111, 128), width=3)
    d.line((70, 642, 70 + int(1138 * scene_index/count), 642), fill=accent, width=5)
    d.text((70, 660), 'Local motion graphics • not generative cinematography',
           font=_font(17), fill=(182, 203, 213))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def render_slide(image: Path, destination: Path, seconds: int, profile: str, *, cancel=None, logger=None):
    w, h, fps = PROFILES[profile]
    # Subtle push-in motion. Source is a static card and is clearly labeled as such.
    # 720p motion animation first, upscale at export to avoid excessive zoompan cost.
    zoom = f"zoompan=z='min(zoom+0.00025,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x720:fps={fps}"
    vf = f'{zoom},scale={w}:{h}:flags=bicubic,format=yuv420p'
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(['-loop', '1', '-framerate', str(fps), '-i', str(image), '-t', str(seconds),
         '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '24',
         '-pix_fmt', 'yuv420p', str(destination)], cancel=cancel, logger=logger)


def normalize_video(source: Path, destination: Path, seconds: int, profile: str, *, cancel=None, logger=None):
    w, h, fps = PROFILES[profile]
    # Loop for slight shortfall; output is always exactly target duration (within frame tick).
    vf = (f'scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,'
          f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},format=yuv420p')
    run(['-stream_loop', '-1', '-i', str(source), '-t', str(seconds), '-vf', vf,
         '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
         '-pix_fmt', 'yuv420p', str(destination)], cancel=cancel, logger=logger)


def concat_video(clips: list[Path], output: Path, *, cancel=None, logger=None):
    if not clips or not all(x.is_file() for x in clips):
        raise ValueError('Список роликов пуст или имеются отсутствующие файлы.')
    listing = output.parent / 'concat.txt'
    # Safe local paths: FFmpeg concat file apostrophe escaping.
    listing.write_text(''.join("file '" + str(p.resolve()).replace('\\', '/').replace("'", "'\\''") + "'\n"
                               for p in clips), encoding='utf-8')
    run(['-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', str(output)],
        cancel=cancel, logger=logger)


def add_audio(video: Path, audio_by_scene: list[tuple[Path, int]], output: Path,
              total_seconds: int, *, cancel=None, logger=None):
    output.parent.mkdir(parents=True, exist_ok=True)
    if not audio_by_scene:
        run(['-i', str(video), '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
             '-map', '0:v:0', '-map', '1:a:0', '-t', str(total_seconds),
             '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
             str(output)], cancel=cancel, logger=logger)
        return
    inputs = ['-i', str(video)]
    filters, branches = [], []
    for n, (audio_file, offset) in enumerate(audio_by_scene, 1):
        inputs += ['-i', str(audio_file)]
        filters.append(f'[{n}:a]aresample=48000,adelay={int(offset * 1000)}:all=1,apad,atrim=0:{total_seconds}[v{n}]')
        branches.append(f'[v{n}]')
    filters.append(''.join(branches) +
                   f'amix=inputs={len(branches)}:duration=longest:normalize=0,volume=0.85[a]')
    run(inputs + ['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[a]',
                  '-t', str(total_seconds), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                  '-movflags', '+faststart', str(output)], cancel=cancel, logger=logger)
