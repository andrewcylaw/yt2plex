import logging

from flask import Flask, request
from pytube import YouTube

from settings import Settings

logger = logging.getLogger(__name__)
app = Flask(__name__)

env_settings = Settings()

@app.route("/watch")
def youtube_dl():
    video = request.args.get('v', None)
    if not video:
        return ValueError("Invalid video provided.")

    logger.info(f'Attempting to download video {video}')
    yt = YouTube(f'http://youtube.com/watch?v={video}')
    to_dl = yt \
        .streams \
        .filter(progressive=True, file_extension='mp4') \
        .order_by('resolution') \
        .desc() \
        .first()

    print(to_dl)
    # to_dl.download(env_settings.plex_server)

