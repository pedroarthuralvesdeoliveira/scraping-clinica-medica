from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    softclyn_url: str
    softclyn_login_page: str
    softclyn_user: str
    softclyn_pass: str
    softclyn_empresa: str
    api_key: str
    redis_url: str
    database_url: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
