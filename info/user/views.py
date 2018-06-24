from flask import current_app
from flask import redirect
from flask import render_template
from flask import request
from flask import session

from info import constants
from info import db
from info.models import Category, News, User

from info.utils.response_code import RET
from . import profile_blue
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from flask import g, jsonify


@profile_blue.route("/other_news_list")
def other_news_list():
    page = request.args.get("p", 1)
    user_id = request.args.get("user_id")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    paginate = News.query.filter(News.user_id == user_id).paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for i in items:
        news_list.append(i.to_review_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_list
    }
    return jsonify(errno = RET.OK, errmsg = "ok", data = data)


@profile_blue.route("/other_info")
@user_login_data
def other_info():
    user = g.user
    user_id = request.args.get("id")
    other = User.query.get(user_id)
    is_followed = False
    if other and user:
        if other in user.followed:
            is_followed = True
    data = {
        "user_info": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template("news/other.html", data=data)



# 我的关注
@profile_blue.route("/user_follow")
@user_login_data
def user_follow():
    user = g.user
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    paginate = user.followed.paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    users = []
    for i in items:
        users.append(i.to_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "users": users
    }
    return render_template("news/user_follow.html", data=data)


# 用户发布新闻列表
@profile_blue.route("/news_list")
@user_login_data
def news_list():
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    user = g.user
    paginate = News.query.filter(News.user_id == user.id).paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_li = []
    for item in items:
        news_li.append(item.to_review_dict())
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_li
    }

    return render_template("news/user_news_list.html", data=data)


# 用户新闻发布
@profile_blue.route("/news_release", methods=["GET", "POST"])
@user_login_data
def news_release():
    if request.method == "GET":
        categories = Category.query.all()
        category_list = []
        for category in categories:
            category_list.append(category.to_dict())
        category_list.pop(0)
        data = {
            "categories": category_list
        }
        return render_template("news/user_news_release.html", data=data)
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    index_image = request.files.get("index_image")
    content = request.form.get("content")
    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    user = g.user
    index_image = index_image.read()
    key = storage(index_image)
    news = News()
    news.title = title
    news.user_id = user.id
    news.digest = digest
    news.category_id = category_id
    news.source = "个人发布"
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.status = 1
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据错误")
    return jsonify(errno=RET.OK, errmsg="发布成功")




# 用户新闻收藏
@profile_blue.route("/collection")
@user_login_data
def collection():
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    user = g.user
    paginate = user.collection_news.paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    collections = []
    for item in items:
        collection_dict = item.to_dict()
        collections.append(collection_dict)

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "collections": collections
    }

    return render_template("news/user_collection.html", data=data)


# 修改密码
@profile_blue.route("/pass_info", methods=["GET", "POST"])
@user_login_data
def pass_info():
    user = g.user
    if request.method == "GET":
        return render_template("news/user_pass_info.html")
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not user.check_password(old_password):
        return jsonify(errno=RET.PARAMERR, errmsg="密码错误")
    user.password = new_password
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="修改成功")

# 更换头像
@profile_blue.route("/pic_info", methods=["GET", "POST"])
@user_login_data
def pic_info():
    user = g.user
    if request.method == "GET":
        data = {
            "user_info": user.to_dict() if user else None,
        }
        return render_template("news/user_pic_info.html", data=data)
    avatar_file = request.files.get("avatar").read()
    key = storage(avatar_file)
    user.avatar_url = key
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
    data = {
        "avatar_url": constants.QINIU_DOMIN_PREFIX + key
    }
    return jsonify(errno=RET.OK, errmsg="上传成功", data=data)



# 基本资料修改
@profile_blue.route("/base_info", methods=["GET", "POST"])
@user_login_data
def base_info():
    user = g.user
    if request.method == "GET":
        data = {
            "user_info": user.to_dict() if user else None,
        }
        return render_template("news/user_base_info.html", data=data)
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")
    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
    session["nick_name"] = nick_name
    return jsonify(errno=RET.OK, errmsg="修改成功")


@profile_blue.route("/info")
@user_login_data
def info():
    user = g.user
    if not user:
        return redirect("/")
    data = {
        "user_info": user.to_dict() if user else None,
    }
    return render_template("news/user.html", data=data)