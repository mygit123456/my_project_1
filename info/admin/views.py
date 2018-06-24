from flask import current_app
from flask import redirect
from flask import render_template, jsonify
from flask import request, session
from flask import url_for, g

from info import constants
from info.utils.image_storage import storage
from info import db
from info.utils.common import user_login_data
from info.models import User, News, Category
from info.utils.response_code import RET
from . import admin_blue
import time
from datetime import datetime, timedelta


# 新闻分类管理
@admin_blue.route("/add_category", methods=["POST"])
def add_category():
    category_id = request.json.get("id")
    name = request.json.get("name")
    if category_id:
        category = Category.query.get(category_id)
        category.name = name
    else:
        category = Category()
        category.name = name
        db.session.add(category)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="ok")


@admin_blue.route("/news_type")
def news_type():
    category_li = Category.query.all()
    categories = []
    for category in category_li:
        categories.append(category.to_dict())
    categories.pop(0)
    data = {
        "categories": categories
    }
    return render_template("admin/news_type.html", data=data)


# 新闻编辑
@admin_blue.route("/news_edit_detail", methods=["GET", "POST"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        news = News.query.get(news_id)
        category_list = Category.query.all()
        categories = []
        for category in category_list:
            categories.append(category.to_dict())
        categories.pop(0)
        data = {
            "news": news.to_review_dict(),
            "categories": categories
        }
        return render_template("admin/news_edit_detail.html", data=data)
    news_id = request.form.get("news_id")
    news = News.query.get(news_id)
    if not news:
        return jsonify(errno=RET.DATAERR, errmsg="没有此新闻")
    title = request.form.get("title")
    digest = request.form.get("digest")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    content = request.form.get("content")
    if not all([title, digest, index_image, category_id, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    index_image = index_image.read()
    key = storage(index_image)
    news.title = title
    news.digest = digest
    news.category_id = category_id
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg = "编辑成功")



@admin_blue.route("/news_edit")
def news_edit():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    filters = []
    if keywords:
        filters.append(News.title.contains(keywords))
    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_li = []
    for news in items:
        news_li.append(news.to_review_dict())
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_li
    }
    return render_template("admin/news_edit.html", data=data)

# 新闻审核
@admin_blue.route("/news_review_detail", methods = ["GET", "POST"])
def news_review_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template("admin/news_review_detail.html", errmsg="没有该新闻")
        news = News.query.get(news_id)
        data = {
            "news": news.to_dict()
        }
        return render_template("admin/news_review_detail.html", data=data)
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    if not all([news_id, action]):
        return jsonify(eerno=RET.PARAMERR, errmsg="参数错误")
    news = News.query.get(news_id)
    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.NODATA, errmsg="请输入未通过原因")
        news.status = -1
        news.reason = reason
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="ok")


# 新闻审核
@admin_blue.route("/news_review")
def news_review():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    filters = [News.status != 0]
    if keywords:
        filters.append(News.title.contains(keywords))
    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for news in items:
        news_list.append(news.to_review_dict())
    data = {
        "news_list": news_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_review.html", data=data)

# 用户列表
@admin_blue.route("/user_list")
def user_list():
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    users = []
    for user in items:
        users.append(user.to_admin_dict())
    data = {
        "users": users,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/user_list.html", data=data)

# 用户计数
@admin_blue.route("/user_count")
def user_count():
    total_count = 0
    mon_count = 0
    day_count = 0
    total_count = User.query.filter(User.is_admin == False).count()
    t = time.localtime()
    mon_begin = "%d-%02d-01" %(t.tm_year, t.tm_mon) # 2018-06-01
    mon_begin_date = datetime.strptime(mon_begin, "%Y-%m-%d") # 2018-06-01-0-0-0
    mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()
    day_begin = "%d-%02d-%02d" %(t.tm_year, t.tm_mon, t.tm_mday) # 2018-06-21
    day_begin_date = datetime.strptime(day_begin, "%Y-%m-%d") # 2018-06-21-0-0-0
    day_count = User.query.filter(User.is_admin == False, User.create_time >= day_begin_date).count()

    today_begin = "%d-%02d-%02d" %(t.tm_year, t.tm_mon, t.tm_mday) # 2018-06-21
    today_begin_date = datetime.strptime(day_begin, "%Y-%m-%d") # 2018-06-21-0-0-0
    activate_count = []
    activate_time = []
    for i in range(0, 31):
        begin_date = today_begin_date - timedelta(days=i)

        end_date = today_begin_date - timedelta(days=(i - 1))
        count = User.query.filter(User.is_admin == False, User.create_time >= begin_date, User.create_time < end_date).count()
        activate_count.append(count)
        activate_time.append(begin_date.strftime("%Y-%m-%d"))

    activate_count.reverse()
    activate_time.reverse()
    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "activate_count": activate_count,
        "activate_time": activate_time
    }
    return render_template("admin/user_count.html", data = data)



# 新闻后台主页面
@admin_blue.route("/index")
@user_login_data
def admin_index():
    user = g.user
    return render_template("admin/index.html", user = user.to_dict())


# 管理员登陆界面
@admin_blue.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        user_id = session.get("user_id")
        is_admin = session.get("is_admin")
        if user_id and is_admin:
            return redirect(url_for("admin.admin_index"))

        return render_template("admin/login.html")
    username = request.form.get("username")
    password = request.form.get("password")
    if not all([username, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    if not user:
        return jsonify(errno=RET.DATAERR, errmsg="用户不存在")
    if not user.check_password(password):
        return jsonify(errno=RET.DATAERR, errmsg="密码错误")
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = username
    session["is_admin"] = True
    return redirect(url_for("admin.admin_index"))

