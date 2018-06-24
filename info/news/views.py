from flask import current_app
from flask import render_template, g, jsonify
from flask import request

from info import db
from info.models import News, Comment, CommentLike, User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blue

@news_blue.route("/followed_user", methods=["POST"])
@user_login_data
def followed_user():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登录")

    # 被关注用户的id
    user_id = request.json.get("user_id")
    action = request.json.get("action")
    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    other = User.query.get(user_id)
    if action == "follow":
        if other not in user.followed:
            user.followed.append(other)
        else:
            return jsonify(errno=RET.DATAERR, errmsg="已经被关注了")
    else:
        if other in user.followed:
            user.followed.remove(other)
        else:
            return jsonify(errno=RET.NODATA, errmsg="没有关注该用户")
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="ok")


@news_blue.route("/comment_like", methods=["POST"])
@user_login_data
def comment_like():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登录")
    comment_id = request.json.get("comment_id")
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    comment = Comment.query.get(comment_id)

    if action == "add":
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                CommentLike.user_id == user.id).first()

        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            comment.like_count += 1

    else:
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                CommentLike.user_id == user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            comment.like_count -= 1
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="点赞成功")




@news_blue.route("/news_comment", methods=["POST"])
@user_login_data
def news_comment():
    user = g.user
    if not user:
        return jsonify(errno=RET.OK, errmsg="请登录")
    news_id = request.json.get("news_id")
    comment_str= request.json.get("comment")
    parent_id = request.json.get("parent_id")
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    news = News.query.get(news_id)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="没有新闻数据")
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据错误")
    return jsonify(errno=RET.OK, errmsg="评论成功", data=comment.to_dict())



@news_blue.route("/news_collect", methods=["POST"])
@user_login_data
def news_collect():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登录")
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    news = News.query.get(news_id)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="没有新闻数据")
    if action == "collect":
        user.collection_news.append(news)
    else:
        user.collection_news.remove(news)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
    return jsonify(errno=RET.OK, errmsg="收藏成功")



@news_blue.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    user = g.user
    news_model = News.query.order_by(News.clicks.desc()).limit(10)
    news_list = []
    for news in news_model:
        news_list.append(news.to_dict())

    news = News.query.get(news_id)
    news.clicks += 1

    comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    comment_list = []
    comment_like_ids = []
    if user:
        comment_likes = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]

    for comment in comments:
        comment_dict = comment.to_dict()
        comment_dict["is_like"] = False
        if comment.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_list.append(comment_dict)

    is_collected = False
    if user:
        if news in user.collection_news:
            is_collected = True

    is_followed = False
    if news.user and user:
        if news.user in user.followed:
            is_followed = True


    data ={
        "user_info": user.to_dict() if user else None,
        "click_news_list": news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "comments": comment_list,
        "is_followed": is_followed

    }
    return render_template("news/detail.html", data=data)