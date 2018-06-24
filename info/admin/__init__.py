from flask import Blueprint
from flask import redirect
from flask import request
from flask import session

admin_blue = Blueprint("admin", __name__, url_prefix="/admin")

from . import views

@admin_blue.before_request
def before_request():
    is_admin = session.get("is_admin", False)
    if not is_admin and not request.url.endswith("/admin/login"):
        return redirect("/")