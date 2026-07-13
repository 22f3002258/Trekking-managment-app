import os
from datetime import datetime
from flask import render_template, request, session, flash, redirect, url_for
from application.models import Users , Staffs, Treks, Bookings, Admins
from flask_session import Session
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from application.extensions import db, login_manager
from application.helpers import admin_required , staff_required, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, allowed_file, save_trek_image

def init(app):
    print("init")
    db.init_app(app)
    Session(app)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    with app.app_context():
        db.create_all()

        existing_admin = Admins.query.filter_by(email="admin").first()
        if not existing_admin:
            admin = Admins(
                email="admin",
                password_hash=generate_password_hash("admin123")
            )
            db.session.add(admin)
            db.session.commit()

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

            # pehle admin table mein dhoondo
            admin = Admins.query.filter_by(email=email).first()
            if admin and check_password_hash(admin.password_hash, password):
                login_user(admin)
                return redirect(url_for("admin_dashboard"))

            # nahi mila to staff table mein dhoondo
            staff = Staffs.query.filter_by(email=email).first()
            if staff and check_password_hash(staff.password_hash, password):
                if staff.approval_status == "pending":
                    flash("your account is awaiting admin approval", "warning")
                    return redirect(url_for("login"))
                elif staff.approval_status == "blacklisted":
                    flash("your account has been blacklisted", "danger")
                    return redirect(url_for("login"))
                login_user(staff)
                return redirect(url_for("staff_dashboard"))

            # nahi mila to users table mein dhoondo
            user = Users.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                if user.status == "blacklisted":
                    flash("your account has been blacklisted", "danger")
                    return redirect(url_for("login"))
                login_user(user)
                return redirect(url_for("home"))

            flash("invalid email or password", "danger")
            return redirect(url_for("login"))

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
    @admin_required
    def admin_dashboard():
        total_treks = Treks.query.count()
        total_users= Users.query.count()
        total_staff=Staffs.query.count()
        total_bookings= Bookings.query.count()

        pending_staff = Staffs.query.filter_by(approval_status="pending").all()

        return render_template(
        "/admin/admin_dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        pending_staff=pending_staff
    )

    #approve staff in admin dashboard

    @app.route("/admin/staff/<int:staff_id>/approve", methods=["POST"])
    @login_required
    @admin_required
    def approve_staff(staff_id):
        staff=Staffs.query.get_or_404(staff_id)
        staff.approval_status = "approved"
        db.session.commit()
        flash(f"{staff.full_name} approved","success")
        return redirect(url_for("manage_staff"))
    
    #blaclist_staff
    @app.route("/admin/staff/<int:staff_id>/blacklist",methods=["POST"])
    @login_required
    @admin_required
    def blacklist_staff(staff_id):
        staff=Staffs.query.get_or_404(staff_id)
        staff.approval_status = "blacklisted"
        db.session.commit()
        flash(f"{staff.full_name} blacklisted","warning")
        return redirect(url_for("manage_staff"))
    
    #restore blacklisted staff
    @app.route("/admin/staff/<int:staff_id>/restore", methods=["POST"])
    @login_required
    @admin_required
    def restore_staff(staff_id):
        staff=Staffs.query.get_or_404(staff_id)
        staff.approval_status="approved"
        db.session.commit()
        flash("f{staff.full_name} restored","success")
        return redirect(url_for("manage_Staff"))
    
    #staff list search pagination
    @app.route("/admin/staff")
    @login_required
    @admin_required
    def manage_staff():
        search_query = request.args.get("q","")
        page=request.args.get("page",1,type=int)

        query=Staffs.query
        if search_query:
            query = query.filter(
                or_(
                    Staffs.full_name.ilike(f"%{search_query}%"),
                    Staffs.email.ilike(f"%{search_query}%")
                )
            )
        pagination = query.paginate(page=page,per_page=5,error_out=False)
        return render_template("admin/staffs.html",staff_list=pagination.items, pagination=pagination, search_query=search_query)
    
    #user list and search 
    @app.route("/admin/users")
    @login_required
    @admin_required
    def manage_users():
        search_query = request.args.get("q","")
        page=request.args.get("page",1,type=int)

        query=Users.query
        if search_query:
            query = query.filter(
                or_(
                    Users.full_name.ilike(f"%{search_query}%"),
                    Users.email.ilike(f"%{search_query}%")
                )
            )
        pagination = query.paginate(page=page,per_page=5,error_out=False)
        return render_template("admin/users.html",user_list=pagination.items, pagination=pagination, search_query=search_query)

    #blacklist users
    @app.route("/admin/users/<int:user_id>/blacklist", methods=["POST"])
    @login_required
    @admin_required
    def blacklist_user(user_id):
        user=Users.query.get_or_404(user_id)
        user.status = "blacklisted"
        db.session.commit()
        flash(f"{user.full_name} blacklisted", "warning")
        return redirect(url_for("manage_users"))
    
    #restore users
    @app.route("/admin/users/<int:user_id>/restore", methods=["POST"])
    @login_required
    @admin_required
    def restore_user(user_id):
        user=Users.query.get_or_404(user_id)
        user.status = "active"
        db.session.commit()
        flash(f"{user.full_name} restored", "warning")
        return redirect(url_for("manage_users"))
    
    # manage trek for admin
    @app.route("/admin/treks")
    @login_required
    @admin_required
    def manage_treks():
        search_query= request.args.get("q","")
        page = request.args.get("page",1,type=int)

        query =Treks.query
        if search_query:
            query = query.filter(
                or_(
                    Treks.trek_name.ilike(f"%{search_query}%"),
                    Treks.location.ilike(f"%{search_query}%")
                )
            )
        pagination=query.paginate(page=page,per_page=5,error_out=False)
        return render_template("admin/treks.html", treks=pagination.items,pagination=pagination, search_query=search_query)
    
    #create trek
    @app.route("/admin/treks/create", methods=["GET","POST"])
    @login_required
    @admin_required
    def create_trek():
        if request.method == "POST":
            trek_name = request.form.get("trek_name")
            location = request.form.get("location")
            cost = request.form.get("cost")
            difficulty = request.form.get("difficulty")
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            max_capacity = request.form.get("max_capacity")
            meeting_point = request.form.get("meeting_point")
            description = request.form.get("description")

            if not trek_name:
                flash("please fill trek name","warning")
                return redirect(url_for("create_trek"))
            elif not location:
                flash("please fill location", "warning")
                return redirect(url_for("create_trek"))
            elif not difficulty:
                flash("please select difficulty", "warning")
                return redirect(url_for("create_trek"))
            elif not start_date or not end_date:
                flash("please fill start and end date", "warning")
                return redirect(url_for("create_trek"))
            elif not max_capacity:
                flash("please fill available slots", "warning")
                return redirect(url_for("create_trek"))
            elif not cost:
                flash("please fill cost", "warning")
                return redirect(url_for("create_trek"))
            
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            except:
                flash("invalid date format", "warning")
                return redirect(url_for("create_trek"))
            
            if end_date_obj < start_date_obj:
                flash("end date cannot be before start date", "warning")
                return redirect(url_for("create_trek"))

            image = request.files.get("image")
            image_filename = save_trek_image(image)

            trek= Treks(
                trek_name=trek_name,
                location=location,
                cost=int(cost),
                difficulty=difficulty,
                start_date=start_date_obj,
                end_date=end_date_obj,
                max_capacity=int(max_capacity),
                available_slots=int(max_capacity),
                meeting_point=meeting_point,
                description=description,
                image_filename=image_filename,
                status="Open"
            )
            db.session.add(trek)
            db.session.commit()
            flash("trek created","success")
            return redirect(url_for("manage_treks"))
    
        return render_template("admin/create_trek.html")

    @app.route("/admin/treks/<int:trek_id>/edit", methods=["GET", "POST"])
    @login_required
    @admin_required
    def edit_trek(trek_id):
        trek = Treks.query.get_or_404(trek_id)
        if request.method == "POST":
            trek_name = request.form.get("trek_name")
            location = request.form.get("location")
            cost = request.form.get("cost")
            difficulty = request.form.get("difficulty")
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            max_capacity = request.form.get("max_capacity")
            status = request.form.get("status")

            if not trek_name or not location or not difficulty or not start_date or not end_date or not max_capacity or not status:
                flash("please fill all fields","warning")
                return redirect(url_for("edit_trek", trek_id=trek_id))
            
            try:
                trek.start_date= datetime.strptime(start_date,"%Y-%m-%d")
                trek.end_date = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                flash("invalid date format","warning")
                return redirect(url_for("edit_trek", trek_id=trek_id))
            
            trek.trek_name = trek_name
            trek.location = location
            trek.cost = int(cost)
            trek.difficulty = difficulty
            trek.max_capacity = int(max_capacity)
            trek.meeting_point = request.form.get("meeting_point")
            trek.description = request.form.get("description")
            trek.status = status

            assigned_staff_id = request.form.get("assigned_staff_id")
            trek.assigned_staff_id = int(assigned_staff_id) if assigned_staff_id else None

            image=request.files.get("image")
            new_filename = save_trek_image(image)
            if new_filename:
                trek.image_filename = new_filename

            db.session.commit()
            flash("trek updated", "success")
            return redirect(url_for("manage_treks"))
        approved_staff = Staffs.query.filter_by(approval_status="approved").all()
        return render_template("admin/edit_trek.html", trek=trek, approval_staff=approved_staff)
    
    @app.route("/admin/treks/<int:trek_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def delete_trek(trek_id):
        trek = Treks.query.get_or_404(trek_id)

        if trek.bookings:
            flash("cannot delete trek — bookings exist. Consider marking it Completed instead.", "warning")
            return redirect(url_for("manage_treks"))

        db.session.delete(trek)
        db.session.commit()
        flash("trek deleted", "warning")
        return redirect(url_for("manage_treks"))
    

    @app.route("/admin/bookings")
    def admin_bookings():
        ...
    @app.route("/admin/analytics")
    def admin_analytics():
        ...

        