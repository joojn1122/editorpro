# Editor pro

**Simple video editor for python.**
Uses [opencv](https://opencv.org/) to edit video and [ffmpeg](https://ffmpeg.org/) with [moviepy](https://github.com/Zulko/moviepy) to edit audio.

## Example with explanation

```python
from editorpro import *

# Get first 15 seconds
background = VideoClip('background.mp4').subclip(0, 15)
music = AudioClip('music.mp3').subclip(0, 15)

seq = Sequence(
    resolution=background.resolution,  # (1920, 1080)
    fps=background.fps                 # 30
)

# Get first video track
# Imagine it like normal video editor tracks
# 3rd track has bigger priority than first
first_video_track = seq.video_tracks[0] 
second_video_track = seq.video_tracks[1]

first_audio_track = seq.audio_tracks[0]

# Default seq has 3 video and audio tracks
# You can also add more
seq.add_video_track()
seq.add_audio_track()

# Add background clip to the track
# time in seconds
# with_audio=True will get the audio from video clip and insert it to the same indexed audio track
first_video_track.insert_clip(background, 0, with_audio=True)
first_audio_track.insert_clip(music, 0)

# Unfortunatelly you can't use custom font, nor the size
# Use scaling to change the size
txt = TextClip(
    seq,
    'Hello world!',
    color='#ff0000',
    scale=1.2,
    position='center',
    duration=background.duration
)

second_video_track.insert_clip(txt, 0)

# Export the video
# You can also specify fourcc, defaults to mp4v
seq.export('final.mp4')
```
