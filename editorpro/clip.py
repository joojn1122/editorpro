import cv2
from typing import overload, Union, Literal, Type
import tempfile
import subprocess
from .utils import *
from mutagen.mp3 import MP3
import os
import numpy as np

class Clip:
    def __init__(self, duration: int | float, start: int | float = 0):
        self.duration = duration
        self.start    = start

    def cleanup(self) -> None:
        pass

class AudioClip(Clip):
    @overload
    def __init__(self, clip: 'VideoClip'): ...

    @overload
    def __init__(self, path: str): ...

    @overload
    def __init__(self, data: bytes): ...

    @checktypes(None, (str, Clip, bytes), allow_none=True)
    def __init__(self, data: Union[str, 'VideoClip', bytes]):
        if data is None:
            super().__init__(0)
            return

        if isinstance(data, str):
            self.file = data

            if not os.path.exists(self.file):
                raise FileNotFoundError(f"File {self.file} does not exist.")
            
        else:
            self.file = tempfile.mktemp() + ".mp3"
            self.tempfile = True

        if isinstance(data, VideoClip):
            # TODO: FIX: For each audio in subclip of VideoClip it creates a new file
            subprocess.run([
                'ffmpeg',
                '-i', data.file,
                '-vn',
                # '-c:a', 'copy', # Can't copy?
                self.file
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            super().__init__(
                duration=data.duration,
                start=data.start
            )

            return
        
        elif isinstance(data, bytes):
            with open(self.file, "wb") as f:
                f.write(data)
        
        self.info = MP3(self.file)
        
        super().__init__(
            duration=self.info.info.length
        )

    def cleanup(self):
        if getattr(self, 'tempfile', None) is not None:
            os.remove(self.file)

    def copy(self) -> 'AudioClip':
        audio = AudioClip()

        audio.file = self.file
        audio.duration = self.duration
        audio.start = self.start

        return audio

    def subclip(self, start: int | float, end: int | float) -> 'AudioClip':
        audio = self.copy()

        audio.start = start
        audio.duration = end - start

        return audio

class VideoClip(Clip):
    @overload
    def __init__(self, path: str): ...

    @overload
    def __init__(self, data: bytes): ...

    @checktypes(None, (str, bytes), allow_none=True)
    def __init__(self, data: str | bytes):
        self._audio: AudioClip = None
        
        if data is None:
            super().__init__(0)
            return
        
        if isinstance(data, str):
            self.file = data

            if not os.path.exists(self.file):
                raise FileNotFoundError(f"File {self.file} does not exist.")

        elif isinstance(data, bytes):
            self.file = tempfile.mktemp() + ".mp4"
            self.tempfile = True

            with open(self.file, "wb") as f:
                f.write(data)

        self.cap = cv2.VideoCapture(self.file)
        
        if not self.cap.isOpened():
            raise ValueError(f"Error opening {self.file}.")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.resolution = (
            int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )
        duration = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps

        super().__init__(duration)

    @property
    def audio(self) -> 'AudioClip':
        if self._audio is None:
            self._audio = AudioClip(self)
        
        return self._audio
    
    def copy(self) -> 'VideoClip':
        video = VideoClip(None)

        video.file = self.file
        video.fps = self.fps
        video.resolution = self.resolution
        video.duration = self.duration
        video.start = self.start
        video.cap = cv2.VideoCapture(self.file)
        
        return video

    def subclip(self, start: int | float, end: int | float) -> 'VideoClip':
        if start < 0:
            start = 0

        if end > self.duration:
            end = self.duration

        if start > self.duration:
            raise ValueError(f"Start time ({start}) is greater than video duration ({self.duration})")
        
        if end < start:
            raise ValueError(f"End time ({end}) is less than start time ({start})")

        video = self.copy()

        video.start = start
        video.duration = end - start

        video.cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * video.fps))

        return video

    def cleanup(self):
        if getattr(self, 'tempfile', None) is not None:
            os.remove(self.file)

    def render(self, frame: np.ndarray[np.uint8], t: int) -> np.ndarray[np.uint8]:
        ret, frame_ = self.cap.read()

        if not ret:
            return frame
        
        return frame_

Position = Union[
    Literal["top-left"],
    Literal["top-right"],
    Literal["bottom-left"],
    Literal["bottom-right"],
    Literal["center"],
    Tuple[int, int]
]

class TextClip(Clip):
    def __init__(
            self,
            sequence,
            text: str,
            position: Position,
            color: Union[tuple[int, int, int], str], 
            font: str = "", # TODO: Add custom font support
            line_thickness: int = 2,
            scale: float = 1,
            stroke_color: Union[tuple[int, int, int], str] = None,
            stroke_width: int = 2,
            duration: int | float = 1
        ):

        self.text = text
        self.font = font
        self.scale = scale
        self.color = rgb_to_bgr(color if isinstance(color, tuple) else hex_to_rgb(color))
        self.line_thickness = line_thickness

        self.stroke_color = rgb_to_bgr(stroke_color if isinstance(stroke_color, tuple) else hex_to_rgb(stroke_color)) if stroke_color is not None else None
        self.stroke_width = stroke_width
        self.has_stroke = stroke_color is not None and stroke_width > 0

        super().__init__(None)
        self.duration = duration

        w, h = sequence.resolution
        
        (self.text_w, self.text_h), baseline = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            line_thickness
        )

        self.is_multiline = self.text_w > w
        if self.text_w > w:
            words = text.split(" ")
            
            self.blocks = []
            current = ""
            current_size = 0

            for word in words:
                (text_w, text_h), baseline = cv2.getTextSize(
                    word,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    scale,
                    line_thickness
                )

                if text_w + current_size < w:
                    current_size += text_w
                    current += word + " "

                else:
                    self.blocks.append(current)
                    current = word + " "
                    current_size = text_w

            if current != "":
                self.blocks.append(current)

        match position:
            case "top-left":
                self.org = (4, 4)

            case "top-right":
                self.org = (w, 4)

            case "bottom-left":
                self.org = (4, 4)

            case "bottom-right":
                self.org = (w, 0)

            case "center":
                self.org = (
                    int(w / 2 - text_w / 2), 
                    int(h / 2 - text_h / 2)
                )

            case (x, y):
                self.org = (x, y)

    def draw_text(
        self,
        frame,
        text,       
        org
    ) -> None:
        if self.has_stroke:
            cv2.putText(
                frame,
                text,
                org,
                cv2.FONT_HERSHEY_SIMPLEX,
                self.scale,
                self.stroke_color,
                self.line_thickness + self.stroke_width,
                cv2.LINE_AA,
                False
            )
        
        cv2.putText(
            frame,
            text,
            org,
            cv2.FONT_HERSHEY_SIMPLEX,
            self.scale,
            self.color,
            self.line_thickness,
            cv2.LINE_AA,
            False
        )

    def render(self, frame: np.ndarray[np.uint8], t: int) -> np.ndarray[np.uint8]:
        if self.is_multiline:
            for block in self.blocks:
                self.draw_text(
                    frame,
                    block,
                    (
                        self.org[0],
                        self.org[1] + self.text_h * self.blocks.index(block)
                    )
                )

        else:
            self.draw_text(frame, self.text, self.org)

        return frame