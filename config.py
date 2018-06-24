import redis, logging


class Config(object):

    SECRET_KEY = "gdgfwhdnojdyra"
    LOG_LEVEL = logging.DEBUG

    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information2"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    SESSION_TYPE = "redis"
    SESSION_USE_SIGNER = True
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    PERMANENT_SESSION_LIFETIME = 86400


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}