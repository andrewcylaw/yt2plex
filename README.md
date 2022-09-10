# Youtube to Plex

1. Point to your Plex server in the `.env`
2. Run with `cd src` and `flask run`
3. Replace `youtube.com/` with `localhost:5000/`

Optional parameter `progressive=true` forces option to download
the highest progressive version of the given video, skipping ffmpeg.
