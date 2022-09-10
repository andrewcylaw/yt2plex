import pathlib
from typing import Optional

from pydantic import BaseSettings, Extra

# project root directory
repo_path = pathlib.Path(__file__).parent.parent

class Settings(BaseSettings):
    class Config:
        extra = Extra.allow
        env_file = repo_path.joinpath(".env")
        env_file_encoding = "utf-8"

    plex_server: str
    ffmpeg_path: Optional[str] = f'{repo_path}/ffmpeg/'