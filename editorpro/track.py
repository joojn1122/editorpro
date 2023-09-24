from .clip import *
import numpy as np
from rich.progress import track
from rich import print
import tempfile

class Track:
    def __init__(self, index: int, seq: 'Sequence'):
        self.index = index
        self.sequence = seq
        self.clips: list[tuple[int | float, Clip]] = []

    @checktypes(None, Clip, (int, float))
    def _insert_clip(self, clip: Clip, time: int | float):
        self.clips.append((
            time,
            clip
        ))

class VideoTrack(Track):
    @overload
    def insert_clip(self, clip: VideoClip, time: int | float, with_audio: bool = True) -> None: ...

    @overload
    def insert_clip(self, clip: TextClip, time: int | float) -> None: ...

    def insert_clip(self, clip: VideoClip, time: int | float, with_audio = True):
        if isinstance(clip, VideoClip) and with_audio:
            audio_track_index = self.index if self.index < len(self.sequence.audio_tracks) else -1
            self.sequence.audio_tracks[audio_track_index].insert_clip(clip.audio, time)

        self._insert_clip(clip, time)

class AudioTrack(Track):
    def insert_clip(self, clip: AudioClip, time: int | float):
        self._insert_clip(clip, time)

class Sequence:

    @checktypes(None, Tuple, int)
    def __init__(self, resolution: tuple[int, int], fps: int):
        self.resolution = resolution
        self.fps = fps
        
        self.video_tracks = [
            VideoTrack(0, self),
            VideoTrack(1, self),
            VideoTrack(2, self)
        ]

        self.audio_tracks = [
            AudioTrack(0, self),
            AudioTrack(1, self),
            AudioTrack(2, self)
        ]

    def add_video_track(self):
        self.video_tracks.append(
            VideoTrack(len(self.video_tracks), self)
        )

    def add_audio_track(self):
        self.audio_tracks.append(
            AudioTrack(len(self.audio_tracks), self)
        )

    def cleanup(self):
        for track in concat(self.video_tracks, self.audio_tracks):
            for _, clip in track.clips:
                try:
                    clip.cleanup()
                except:
                    pass

        self.video_tracks.clear()
        self.audio_tracks.clear()

    def calculate_duration(self) -> int | float:
        duration = 0

        for track in concat(self.audio_tracks, self.video_tracks):
            for time, clip in track.clips:
                if time + clip.duration > duration:
                    duration = time + clip.duration

        return duration

    @checktypes(None, str, str)
    def export(self, file: str, fourcc: str = "mp4v") -> None:
        temp_video_file = tempfile.mktemp(suffix=".mp4")

        filename = os.path.basename(file)
        
        # Video tracks
        writer = cv2.VideoWriter(
            temp_video_file,
            fourcc=cv2.VideoWriter_fourcc(*fourcc),
            fps=self.fps,
            frameSize=self.resolution
        )

        total_seconds = self.calculate_duration()

        if total_seconds == 0:
            raise Exception("No clips to render")

        sorted_clips: list[list[tuple[int | float, VideoClip]]] = [None] * len(self.video_tracks)

        for i, video_track in enumerate(self.video_tracks):
            sorted_clips[i] = sorted(video_track.clips, key=lambda x: x[0])

        seconds_frame = 1 / self.fps
        current_second = 0

        for current_second in track(
            np.arange(0, total_seconds, seconds_frame),
            description=f"[green1]Rendering video '{filename}'..[/green1]"
        ):
            frame = np.zeros((*self.resolution, 3), dtype=np.uint8)

            for clips in sorted_clips:
                for time, clip in clips:
                    if current_second >= time:
                        if current_second <= time + clip.duration:
                            frame = clip.render(frame, round((current_second - time) * self.fps))
                    
                    # Sorted by time, so if the current time is greater than the time of the clip
                    # All other clips are also greater than the current time
                    else:
                        break
                        
            writer.write(frame)

        writer.release()

        # Audio tracks
        sorted_clips: list[list[tuple[int | float, AudioClip]]] = [None] * len(self.audio_tracks)

        for i, audio_track in enumerate(self.audio_tracks):
            sorted_clips[i] = sorted(audio_track.clips, key=lambda x: x[0])

        from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip

        final_audios = []
        for clips in sorted_clips:
            if len(clips) == 0:
                continue
            
            audios = []

            first_time, clip = clips.pop(0)
            audios.append(
                AudioFileClip(clip.file).subclip(clip.start, clip.start + clip.duration)
            )

            for i, (time, clip) in enumerate(clips):
                if i == 0:
                    silence_length = time - (first_time + clip.duration)

                else:
                    silence_length = time - (clips[i - 1][0] + clips[i - 1][1].duration)

                if silence_length > 0:
                    audios.append(create_silence(silence_length))

                audios.append(AudioFileClip(clip.file).subclip(clip.start, clip.start + clip.duration))

            final_audios.append(concatenate_audioclips(audios))

        if len(final_audios) == 0:
            subprocess.run([
                'ffmpeg',
                '-i', temp_video_file,
                '-c:v', 'copy',
                '-an',
                '-y',
                file
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        else:
            temp_audio_file = tempfile.mktemp(suffix=".mp3")
            
            final_audio = CompositeAudioClip(final_audios)
            final_audio.write_audiofile(temp_audio_file, fps=44100)

            subprocess.run([
                'ffmpeg',
                '-i', temp_video_file,
                '-i', temp_audio_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-y',
                '-strict', 'experimental',
                file
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            os.remove(temp_audio_file)
        
        os.remove(temp_video_file)

        print(f"[green1]Successfully rendered video in '{file}'[/green1]")