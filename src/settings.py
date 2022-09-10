from pydantic import BaseSettings


class Settings(BaseSettings):
    plex_server: str