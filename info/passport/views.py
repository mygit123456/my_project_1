from flask import current_app
from flask import make_response
from flask import request, jsonify, session
import re, random
from info import db
from datetime import datetime
from info import constants
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from info import redis_stroe
from info.utils.yuntongxun.sms import CCP
from info.models import User
from . import passport_blue


@passport_blue.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("mobile", None)
    session.pop("nick_name", None)
    session.pop("user_id", None)
    session.pop("is_admin", None)
    return jsonify(errno=RET.OK, errmsg="退出成功")

# 登陆
@passport_blue.route("/login", methods=["POST"])
def login():
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取数据失败")
    if not user:
        return jsonify(errno=RET.DATAERR, errmsg="用户不存在")
    if not user.check_password(password):
        return jsonify(errno=RET.DATAERR, errmsg="密码错误")
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    user.last_login = datetime.now()
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="登陆成功")

# 注册
@passport_blue.route("/register", methods=["POST"])
def register():
    mobile = request.json.get("mobile")
    smscode = request.json.get("smscode")
    password = request.json.get("password")
    if not all([mobile, smscode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        real_smscode = redis_stroe.get("Sms_" + smscode)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取短信验证码失败")
    if not real_smscode:
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码已过期")
    if smscode != real_smscode:
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码输入错误")
    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    user.password = password
    user.last_login = datetime.now()
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据存储失败")
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    return jsonify(errno=RET.OK, errmsg="注册成功")
# 获取短信验证码
@passport_blue.route("/sms_code", methods=["POST"])
def get_sms_code():
    mobile = request.json.get("mobile")
    image_code = request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not re.match(r"^1[3578]\d{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号码不正确")
    try:
        real_image_code = redis_stroe.get("ImageCode_" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取图片验证码失败")
    if not real_image_code:
        return jsonify(errno=RET.DBERR, errmsg="图片验证码已过期")
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="图片验证码输入错误")
    result = random.randint(0, 999999)
    sms_code = "%06d" % result
    print(sms_code)
    # result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES], 1)
    # if result != 0:
    #     return jsonify(errno=RET.THIRDERR, errmsg="发送短信失败")
    redis_stroe.set("Sms_" + sms_code, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    return jsonify(errno=RET.OK, errmsg="发送成功")



# 获取图片验证码
@passport_blue.route("/image_code")
def get_image_code():
    code_id = request.args.get("code_id")
    if not code_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    name, text, image = captcha.generate_captcha()
    print(text)
    try:
        redis_stroe.set("ImageCode_" + code_id, text, constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="存储错误")
    resp = make_response(image)
    resp.headers["Content-Type"] = "image/jpg"
    return resp
