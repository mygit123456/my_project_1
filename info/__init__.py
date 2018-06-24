import logging
from logging.handlers import RotatingFileHandler
from flask import render_template, g
from flask_wtf.csrf import generate_csrf
from flask import Flask
import redis
from flask_wtf import CSRFProtect
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from config import config_map

redis_stroe = None  # type: redis.StrictRedis
db = SQLAlchemy()


def create_app(config_name):
    app = Flask(__name__)
    config_name = config_map.get(config_name)
    app.config.from_object(config_name)
    db.init_app(app)
    global redis_stroe
    redis_stroe = redis.StrictRedis(host=config_name.REDIS_HOST, port=config_name.REDIS_PORT, decode_responses=True)
    Session(app)
    CSRFProtect(app)

    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    setup_log(config_name)
    from info.utils.common import user_login_data
    @app.errorhandler(404)
    @user_login_data
    def not_found(error):
        user = g.user
        data = {
            "user_info": user.to_dict() if user else None
        }

        return render_template("news/404.html", data=data)

    from info.utils.common import index_class
    app.add_template_filter(index_class, "indexClass")
    from info.index import index_blue
    app.register_blueprint(index_blue)
    from info.passport import passport_blue
    app.register_blueprint(passport_blue)
    from info.news import news_blue
    app.register_blueprint(news_blue)
    from info.user import profile_blue
    app.register_blueprint(profile_blue)
    from info.admin import admin_blue
    app.register_blueprint(admin_blue)
    return app


def setup_log(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=logging.DEBUG)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)
