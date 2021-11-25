from dataclasses import dataclass
from typing import Optional

from environs import Env


@dataclass
class DbConfig:
    url: str


@dataclass
class RedisConfig:
    redis_host: str
    redis_port: int
    redis_db_jobstore: int


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]
    bot_name: str
    use_redis: bool


@dataclass
class Miscellaneous:
    provider_token_ukassa: str = None
    provider_token_sber: str = None
    other_params: str = None


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    redis: RedisConfig
    misc: Miscellaneous


def load_config(database_url: Optional[str], path: str = None):
    env = Env()
    env.read_env(path)

    if not database_url:
        db_user = env.str("DB_USER")
        db_pass = env.str("DB_PASS")
        db_host = env.str("DB_HOST")
        db_port = env.str("DB_PORT")
        db_name = env.str("DB_NAME")
        database_url = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMINS"))),
            bot_name=env.str("BOT_NAME"),
            use_redis=env.bool("USE_REDIS"),
        ),
        db=DbConfig(url=database_url),
        redis=RedisConfig(
            redis_host=env.str("REDIS_HOST", default="localhost"),
            redis_port=env.int("REDIS_PORT", default=6379),
            redis_db_jobstore=env.int("REDIS_DB_JOBESTORE", default=1)
        ),
        misc=Miscellaneous(
            provider_token_sber=env.str('PROVIDER_TOKEN_SBER')
        )
    )
