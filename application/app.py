from flask import render_template, request, session, flash, redirect, url_for
from application.models import Users , Staffs, Treks, Bookings, Admins
from flask_session import Session
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from application.extensions import db, login_manager
def init(app):
    print("init")
    db.init_app(app)
    Session(app)
    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        prefix, real_id = user_id.split("-")
        if prefix == "user":
            return Users.query.get(int(real_id))
        elif prefix == "staff":
            from application.models import Staffs
            return Staffs.query.get(int(real_id))
        elif prefix == "admin":
            from application.models import Admins
            return Admins.query.get(int(real_id))
        return None

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            fullname = request.form.get("fullname")
            email = request.form.get("email")
            phone = request.form.get("phone")
            password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            emergency = request.form.get("emergency")

            existing_user = Users.query.filter(
                or_(Users.phone_no == phone, Users.email == email)
            ).first()

            if existing_user:
                flash("user already exists", "warning")
                return redirect(url_for("register"))
            elif not email:
                flash("Please fill email", "warning")
                return redirect(url_for("register"))
            elif not fullname:
                flash("please fill fullname", "warning")
                return redirect(url_for("register"))
            elif not phone:
                flash("please provide phone number", "warning")
                return redirect(url_for("register"))
            elif not password:
                flash("please fill password", "warning")
                return redirect(url_for("register"))
            elif not confirmation:
                flash("confirm your password", "warning")
                return redirect(url_for("register"))
            elif password != confirmation:
                flash("password mismatched", "warning")
                return redirect(url_for("register"))
            elif not emergency:
                flash("fill emergency number", "warning")
                return redirect(url_for("register"))

            user = Users(
                full_name=fullname,
                email=email,
                password_hash=generate_password_hash(password),
                phone_no=phone,
                emergency_contact=emergency
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful, you can login now", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            if not email:
                flash("please fill email", "warning")
                return redirect(url_for("login"))
            elif not password:
                flash("please fill your password", "warning")
                return redirect(url_for("login"))

            user = Users.query.filter_by(email=email).first()

            if not user:
                flash("user not registered", "warning")
                return redirect(url_for("register"))
            elif not check_password_hash(user.password_hash, password):
                flash("wrong password", "danger")
                return redirect(url_for("login"))
            elif user.status == "blacklisted":
                flash("your account has been blacklisted", "danger")
                return redirect(url_for("login"))
            else:
                login_user(user)
                flash("login successful", "success")
                return redirect(url_for("home"))

        return render_template("login.html")

    @app.route("/dashboard/<int:user_id>")
    @login_required
    def dashboard(user_id):
        return render_template("dashboard.html", user=current_user)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("logged out", "success")
        return redirect(url_for("home"))
    
    @app.route("/treks")
    def browse_treks():
        ...
    @app.route("/register/staff",methods=["GET","POST"])
    def staff_register():
        if request.method == "POST":
            fullname = request.form.get("fullname")
            email = request.form.get("email")
            phone = request.form.get("phone")
            password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            emergency = request.form.get("emergency")
            experience = request.form.get("experience")

            existing_staff=Staffs.query.filter(
                or_(Staffs.email==email,Staffs.phone_no==phone)
            ).first()

            if existing_staff:
                flash("staff already exists","warning")
                return redirect(url_for("staff_register"))
            elif not email :
                flash("please fill email","warning")
                return redirect(url_for("staff_register"))
            elif not fullname:
                flash("please fill fullname","warning")
                return redirect(url_for("staff_register"))
            elif not phone:
                flash("please provide phone","warning")
                return redirect(url_for("staff_register"))
            elif not password:
                flash("please fill password","warning")
                return redirect(url_for("staff_register"))
            elif not confirmation:
                flash("please confirm your password","warning")
                return redirect(url_for("staff_register"))
            elif not emergency:
                flash("please fill emergency number","warning")
                return redirect(url_for("staff_register"))
            elif not experience:
                flash("please fill experience","warning")
                return redirect(url_for("staff_register"))
            elif password != confirmation:
                flash("confirm password did not matched","warning")
                return redirect(url_for("staff_register"))
            else:
                staff=Staffs(
                    full_name=fullname,
                    email=email,
                    password_hash=generate_password_hash(password),
                    phone_no=phone,
                    exp=experience
                )
                db.session.add(staff)
                db.session.commit()
                flash("registration succesfull awaiting admin approval","success")
                return redirect(url_for("login"))

        else:
            return render_template("staff_register.html")
        
    @app.route("/admin/dashboard")
    @login_required
    def admin_dashboard():
        total_treks = Treks.querry.count()
        total_users= Users.query.count()
        total_staff=Staffs.querry.count()
        total_bookings= Bookings.query.count()

        pending_staff = Staffs.query.filter_by(approval_status="pending").all()

        return render_template(
        "admin_dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        pending_staff=pending_staff
    )

        