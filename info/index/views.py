from flask import render_template, current_app, session, jsonify
from flask import request

from info import constants
from info.models import User, Category
from info.models import News
from info.utils.response_code import RET
from . import index_blue


@index_blue.route("/news_list")
def news_list():
    cid = request.args.get("cid", 1)
    page = request.args.get("page", 1)
    per_page = request.args.get("pre_page", 10)
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # filters = [News.status == 0]
    filters = []
    if cid != 1:
        filters.append(News.category_id == cid)
    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    items = paginate.items
    total_page = paginate.pages
    current_page = paginate.page
    new_li = []
    for new in items:
        new_li.append(new.to_dict())
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_dict_li": new_li,
        "cid": cid
    }
    return jsonify(errno=RET.OK, errmsg="成功", data=data)


@index_blue.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("news/favicon.ico")


@index_blue.route("/")
def index():
    # 获取用户登陆
    user_id = session.get("user_id")
    user = None
    if user_id:
        user = User.query.get(user_id)

    # 获取点击排行
    news_model = News.query.order_by(News.clicks.desc()).limit(10)

    news_list = []

    for news in news_model:
        news_list.append(news.to_dict())

    # 获取新闻菜单
    categories = Category.query.all()
    categories_list = []
    for category in categories:
        categories_list.append(category)

    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": news_list,
        "categories": categories_list
    }

    return render_template("news/index.html", data = data)