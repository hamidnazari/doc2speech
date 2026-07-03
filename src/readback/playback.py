from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING, cast

from readback.settings import DEFAULT_SPEED, MAX_SPEED, MIN_SPEED

if TYPE_CHECKING:
    import numpy as np


class Player:
    """Buffers synthesised audio and serves it frame-by-frame to a sounddevice callback."""

    seek_samples: int
    chunks: list[np.ndarray]
    lock: threading.Lock
    synthesis_done: threading.Event
    paused: threading.Event
    stopped: threading.Event
    playhead: float
    playback_speed: float

    def __init__(self, seek_samples: int, playback_speed: float = DEFAULT_SPEED) -> None:
        self.seek_samples = seek_samples
        self.chunks = []
        self.lock = threading.Lock()
        self.synthesis_done = threading.Event()
        self.paused = threading.Event()
        self.stopped = threading.Event()
        self.playhead = 0.0
        self.playback_speed = _clamp_speed(playback_speed)

    def push(self, chunk: np.ndarray) -> None:
        with self.lock:
            self.chunks.append(chunk.astype("float32"))

    def total(self) -> int:
        with self.lock:
            return sum(len(c) for c in self.chunks)

    def read(self, start: int, n: int) -> np.ndarray:
        import numpy as np

        out = np.zeros(n, dtype="float32")
        written = pos = 0
        with self.lock:
            for chunk in self.chunks:
                end = pos + len(chunk)
                if end <= start:
                    pos = end
                    continue
                src = max(0, start - pos)
                take = min(len(chunk) - src, n - written)
                out[written : written + take] = chunk[src : src + take]
                written += take
                pos = end
                if written >= n:
                    break
        return out

    def read_at_speed(self, start: float, n: int, speed: float) -> np.ndarray:
        import numpy as np

        if speed == 1.0 and start.is_integer():
            return self.read(int(start), n)

        out = np.zeros(n, dtype="float32")
        with self.lock:
            for frame in range(n):
                sample = int(start + frame * speed)
                out[frame] = self._sample_at_locked(sample)
        return out

    def _sample_at_locked(self, sample: int) -> float:
        pos = 0
        for chunk in self.chunks:
            end = pos + len(chunk)
            if sample < end:
                return float(cast("float", chunk[sample - pos]))
            pos = end
        return 0.0

    def callback(
        self,
        outdata: np.ndarray,
        frames: int,
        _time: object,
        _status: object,
    ) -> None:
        import sounddevice as sd

        if self.stopped.is_set():
            outdata[:] = 0
            raise sd.CallbackStop()
        if self.paused.is_set():
            outdata[:] = 0
            return
        total = self.total()
        if self.playhead >= total:
            if self.synthesis_done.is_set():
                outdata[:] = 0
                raise sd.CallbackStop()
            outdata[:] = 0
            return
        outdata[:, 0] = self.read_at_speed(self.playhead, frames, self.playback_speed)
        self.playhead += frames * self.playback_speed

    def seek(self, delta: int) -> None:
        self.playhead = max(0, min(self.playhead + delta, self.total()))

    def change_speed(self, delta: float) -> float:
        self.playback_speed = _clamp_speed(round(self.playback_speed + delta, 2))
        return self.playback_speed


def _clamp_speed(speed: float) -> float:
    return max(MIN_SPEED, min(speed, MAX_SPEED))


def fmt_time(samples: int, sample_rate: int) -> str:
    secs = samples // sample_rate
    return f"{secs // 60}:{secs % 60:02d}"


def render_bar(
    playhead: float,
    total: int,
    synth_done: bool,
    sample_rate: int,
    width: int = 40,
    action: str = "",
    speed: float | None = None,
) -> str:
    filled = 0 if total == 0 else int(min(playhead / total, 1.0) * width)
    bar = "█" * filled + ("░" * (width - filled))
    total_str = fmt_time(total, sample_rate) if synth_done else f"~{fmt_time(total, sample_rate)}"
    action_col = f"  {action:<6}" if action else " " * 8
    speed_col = f" {speed:.2f}x" if speed is not None else ""
    playhead_str = fmt_time(int(playhead), sample_rate)
    return f"\033[0m\r{playhead_str} [{bar}] {total_str}{action_col}{speed_col}"


def play_stream(text: str, voice: str, speed: float) -> None:
    import asyncio

    import sounddevice as sd

    from readback.synth import SAMPLE_RATE, synthesise_stream

    player = Player(seek_samples=5 * SAMPLE_RATE, playback_speed=speed)
    done = threading.Event()
    action: list[str] = [""]
    interactive = sys.stdin.isatty()

    def keyreader() -> None:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            _ = tty.setraw(fd)
            while not player.stopped.is_set() and not done.is_set():
                ch = sys.stdin.read(1)
                if ch == " ":
                    if player.paused.is_set():
                        player.paused.clear()
                        action[0] = "▶"
                    else:
                        player.paused.set()
                        action[0] = "⏸"
                elif ch == "\x1b":
                    nxt = sys.stdin.read(1)
                    if nxt == "[":
                        arrow = sys.stdin.read(1)
                        if arrow == "C":
                            player.seek(+player.seek_samples)
                            action[0] = "+5s"
                        elif arrow == "D":
                            player.seek(-player.seek_samples)
                            action[0] = "-5s"
                elif ch in ("+", "="):
                    action[0] = f"{player.change_speed(+0.1):.1f}x"
                elif ch == "-":
                    action[0] = f"{player.change_speed(-0.1):.1f}x"
                elif ch in ("\x03", "\x04", "q"):
                    player.stopped.set()
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    controls = "space  ←/→=seek 5s  +/-=speed  q=quit" if interactive else "controls disabled"
    _ = sys.stderr.write(f"\033[0mPlaying… ({controls})\n\033[?25l")
    _ = sys.stderr.flush()

    def progress_loop() -> None:
        while not done.is_set():
            line = render_bar(
                player.playhead,
                player.total(),
                player.synthesis_done.is_set(),
                SAMPLE_RATE,
                action=action[0],
                speed=player.playback_speed,
            )
            _ = sys.stderr.write(line)
            _ = sys.stderr.flush()
            _ = threading.Event().wait(0.1)
        _ = sys.stderr.write("\r" + " " * 70 + "\r\033[?25h")
        _ = sys.stderr.flush()

    with sd.OutputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=player.callback
    ) as stream:
        if interactive:
            key_thread = threading.Thread(target=keyreader, daemon=True)
            key_thread.start()
        progress_thread = threading.Thread(target=progress_loop, daemon=True)
        progress_thread.start()

        try:

            async def run() -> None:
                async for chunk, _ in synthesise_stream(text, voice=voice, speed=speed):
                    if player.stopped.is_set():
                        return
                    player.push(chunk)
                player.synthesis_done.set()

            asyncio.run(run())
            while stream.active:
                _ = threading.Event().wait(0.05)
        finally:
            done.set()
