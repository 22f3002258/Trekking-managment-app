import os
from functools import wraps
from flask import abort
from flask_login import current_user
from application.models import Admins, Staffs
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join("static","uploads","treks")
ALLOWED_EXTENSIONS={"png","jpg","jpeg","webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def save_trek_image(image):
    if image and image.filename != "" and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, filename))
        return filename
    return None

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Admins):
            abort(403)
        return f(*args, **kwargs)
    return wrapper

def staff_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Staffs):
            abort(403)
        return f(*args, **kwargs)
    return wrapper