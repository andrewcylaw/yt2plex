import logging
import os
from pathlib import Path
from typing import Tuple

import ffmpeg
from flask import Flask, request
from pytube import YouTube, Stream

from src.settings import Settings

logger = logging.getLogger(__name__)
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

env_settings = Settings()

@app.route("/watch")
def youtube_dl_entry():
    _setup_ffmpeg_path(env_settings.ffmpeg_path)
    video: str = request.args.get('v', None)
    if not video:
        return ValueError("Invalid video provided.")

    force_progressive: bool = request.args.get('progressive', False)
    try:
        return youtube_dl(video, force_progressive)
    except Exception as e:
        error_msg = f"Failed to download video - {e}"
        logger.error(error_msg)
        return error_msg


def youtube_dl(video: str, force_progressive: bool) -> str:
    logger.info(f'Beginning video download with          [force_progressive={force_progressive}]')
    logger.info(f'Videos will be downloaded to           [{env_settings.plex_server}]')
    yt = YouTube(f'http://youtube.com/watch?v={video}')
    logger.info(f'Attempting to fetch metadata for video [{video}]')

    streams = yt.streams if not force_progressive else yt.streams.filter(progressive=True)
    vid_partial = streams \
        .order_by('resolution') \
        .desc() \
        .first()
    logger.info(f'Fetched metadata for video             [{vid_partial.default_filename}]')
    logger.info(f'Detected highest fps/resolution of     [{vid_partial.fps}@{vid_partial.resolution}, progressive={vid_partial.is_progressive}]')
    logger.info(f'Beginning download for video           [{vid_partial.default_filename}]')

    if not vid_partial.is_progressive:
        logger.info(f'Detected non-progressive video, downloading video and audio streams separately and merging')
        audio_partial = yt.streams \
            .filter(only_audio=True) \
            .order_by('abr') \
            .desc() \
            .first()
        path, tot_size = _get_non_progressive(vid_partial=vid_partial, audio_partial=audio_partial, plex_server=env_settings.plex_server)
    else:
        path, tot_size = _get_progressive(vid_partial)

    logger.info(f'Successfully downloaded a total of     [{tot_size}mb]')
    logger.info(f'Successfully downloaded video to       [{path}]')

    return f"Successfully downloaded {round(tot_size, 3)}mb, and created video {path}"


def _get_progressive(partial: Stream) -> Tuple[str, float]:
    """
    Attempts to download a progressive stream, where progressive streams are videos with video+audio premixed
    :param partial: pytube streaming object to download
    :return: tuple of new video path and total file size downloaded in mb
    """
    path = partial.download(env_settings.plex_server)
    return Path(path), os.stat(path).st_size / (1024 * 1024)


def _get_non_progressive(vid_partial: Stream, audio_partial: Stream, plex_server: str) -> Tuple[str, float]:
    """
    Attempts to generate a non-progressive stream, where non-progressive streams are audio-less videos and videos
    separately.

    Uses ffmpeg to merge the audio and video tracks and create an mp4.

    :param vid_partial: pytube streaming object to download of highest quality video
    :param audio_partial: pytubs streaming object to download of highest quality audio
    :return: tuple of new video path and total file size downloaded in mb
    """
    VIDEO_TEMP, AUDIO_TEMP = f'{plex_server}/video_temp/', f'{plex_server}/audio_temp/'

    # Not async
    logger.info(f'Beginning download for audio portion:  [{audio_partial.default_filename}]')
    audio_path = audio_partial.download(AUDIO_TEMP)
    audio_size_mb = round(os.stat(audio_path).st_size / (1024 * 1024), 3)
    logger.info(f'Finished download for audio portion:   [{audio_partial.default_filename}, {audio_size_mb}mb]')

    logger.info(f'Beginning download for video portion:  [{vid_partial.default_filename}]')
    vid_path = vid_partial.download(VIDEO_TEMP)
    vid_size_mb = round(os.stat(vid_path).st_size / (1024 * 1024), 3)
    logger.info(f'Finished download for video portion:   [{vid_partial.default_filename}, {vid_size_mb}mb]')

    fsize = (os.stat(vid_path).st_size + os.stat(audio_path).st_size) / (1024 * 1024)
    merged_path = _merge_audio_video(vid_path, audio_path, plex_server)

    # Delete temp files/folder
    os.remove(vid_path)
    os.remove(audio_path)
    os.rmdir(VIDEO_TEMP)
    os.rmdir(AUDIO_TEMP)

    return Path(merged_path), fsize

def _merge_audio_video(vid_path: str, audio_path: str, output_path: str) -> str:
    """
    Uses ffmpeg to merge the given video and audio and output an mp4

    :param vid_path: path to audio-less video
    :param audio_path: path to audio track
    :return: filename of newly merged video
    """
    logger.info(f'Beginning ffmpeg merge with            [video={vid_path}, audio={audio_path}]')
    full_output_path = f'{output_path}/{os.path.splitext(os.path.split(vid_path)[1])[0]}.mp4'
    input_video = ffmpeg.input(os.path.abspath(vid_path))
    input_audio = ffmpeg.input(os.path.abspath(audio_path))

    logger.info(f'Attempting to merge audio and video to [{full_output_path}]')
    ffmpeg \
        .concat(input_video, input_audio, v=1, a=1)\
        .output(full_output_path)\
        .run(overwrite_output=True)
    logger.info(f'Successfully merged audio and video to [{full_output_path}]')

    return output_path


def _setup_ffmpeg_path(ffmpeg_path: str) -> None:
    logger.info(f'Adding ffmpeg {ffmpeg_path} to path')
    os.environ['PATH'] += os.pathsep + ffmpeg_path
    logger.info(f'----------------------------------------------------------------------')

