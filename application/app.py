import os
from datetime import datetime
from flask import render_template, request, session, flash, redirect, url_for,abort
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
                email="admin@trekmanager.com",
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
        featured_treks = Treks.query.filter_by(status="Open").limit(3).all()
        return render_template("index.html", featured_treks=featured_treks)

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
    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("logged out", "success")
        return redirect(url_for("home"))
    
    @app.route("/treks")
    def browse_treks():
        difficulty=request.args.get("difficulty","All")
        search_query=request.args.get("q","")
        page = request.args.get("page", 1, type=int)

        query = Treks.query.filter_by(status="Open")

        if difficulty != "All":
            query = query.filter_by(difficulty=difficulty)
        
        if search_query:
            query = query.filter(
                or_(
                    Treks.trek_name.ilike(f"%{search_query}%"),
                    Treks.location.ilike(f"%{search_query}%")
                )
            )
        pagination = query.paginate(page=page, per_page=6, error_out=False)
        return render_template(
            "treks.html",
            treks=pagination.items,
            pagination=pagination,
            difficulty=difficulty,
            search_query=search_query
            )

    @app.route("/treks/<int:trek_id>")
    def trek_detail(trek_id):
        trek = Treks.query.get_or_404(trek_id)
        return render_template("trek_detail.html", trek=trek)
    
    @app.route("/treks/<int:trek_id>/book", methods=["POST"])
    @login_required
    def book_trek(trek_id):
        if isinstance(current_user, Staffs) or isinstance(current_user, Admins):
            flash("only trekkers can book treks", "warning")
            return redirect(url_for("trek_detail", trek_id=trek_id))

        trek = Treks.query.get_or_404(trek_id)

        if trek.status != "Open":
            flash("this trek is not open for booking", "warning")
            return redirect(url_for("trek_detail", trek_id=trek_id))

        if trek.available_slots <= 0:
            flash("no slots available", "warning")
            return redirect(url_for("trek_detail", trek_id=trek_id))

        existing = Bookings.query.filter_by(
            user_id=current_user.id, trek_id=trek.id, status="Booked"
        ).first()
        if existing:
            flash("you have already booked this trek", "warning")
            return redirect(url_for("trek_detail", trek_id=trek_id))

        booking = Bookings(
            user_id=current_user.id,
            trek_id=trek.id,
            amount=trek.cost,
            status="Booked"
        )
        trek.available_slots -= 1
        db.session.add(booking)
        db.session.commit()

        flash("booking confirmed", "success")
        return redirect(url_for("booking_confirmation", booking_id=booking.id))

    @app.route("/bookings/<int:booking_id>/confirmation")
    @login_required
    def booking_confirmation(booking_id):
        booking = Bookings.query.get_or_404(booking_id)
        if booking.user_id != current_user.id:
            abort(403)
        return render_template("booking_confirmation.html", booking=booking)
    
    @app.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
    @login_required
    def cancel_booking(booking_id):
        booking = Bookings.query.get_or_404(booking_id)
        if booking.user_id != current_user.id:
            abort(403)

        if booking.status == "Cancelled":
            flash("booking already cancelled", "warning")
            return redirect(url_for("dashboard"))

        booking.status = "Cancelled"
        booking.trek.available_slots += 1
        db.session.commit()
        flash("booking cancelled", "success")
        return redirect(url_for("dashboard"))
    
    @app.route("/profile")
    @login_required
    def dashboard():
        if isinstance(current_user, Staffs) or isinstance(current_user, Admins):
            abort(403)

        all_bookings = Bookings.query.filter_by(user_id=current_user.id).all()
        active_bookings = Bookings.query.filter_by(user_id=current_user.id, status="Booked").all()
        completed_count = Bookings.query.filter_by(user_id=current_user.id, status="Completed").count()

        recent_history = Bookings.query.filter_by(user_id=current_user.id)\
            .order_by(Bookings.booking_date.desc()).limit(5).all()

        return render_template(
            "dashboard.html",
            total_booked=len(all_bookings),
            active_bookings=active_bookings,
            active_count=len(active_bookings),
            completed_count=completed_count,
            recent_history=recent_history
        )
    
    @app.route("/profile/edit", methods=["GET", "POST"])
    @login_required
    def edit_profile():
        if isinstance(current_user, Staffs) or isinstance(current_user, Admins):
            abort(403)

        if request.method == "POST":
            fullname = request.form.get("fullname")
            phone = request.form.get("phone")
            emergency = request.form.get("emergency")

            if not fullname or not phone or not emergency:
                flash("please fill all fields", "warning")
                return redirect(url_for("edit_profile"))

            current_user.full_name = fullname
            current_user.phone_no = phone
            current_user.emergency_contact = emergency
            db.session.commit()
            flash("profile updated", "success")
            return redirect(url_for("dashboard"))

        return render_template("edit_profile.html", user=current_user)
    

    @app.route("/profile/history")
    @login_required
    def full_history():
        if isinstance(current_user, Staffs) or isinstance(current_user, Admins):
            abort(403)

        bookings = Bookings.query.filter_by(user_id=current_user.id)\
            .order_by(Bookings.booking_date.desc()).all()
        return render_template("history.html", bookings=bookings)
    



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
        return redirect(url_for("manage_staff"))
    
    #staff list search pagination
    @app.route("/admin/staff",methods=["GET","POST"])
    @login_required
    @admin_required
    def manage_staff():
        if request.method=="POST":
            staff_id=request.form.get("selected_staff_id")
            trek_id=request.form.get("selected_trek_id")
            if not staff_id or not trek_id:
                flash("please select staff and trek","warning")
                return redirect(url_for("manage_staff"))
            
            staff=Staffs.query.filter_by(id=int(staff_id)).first()
            trek=Treks.query.filter_by(id=int(trek_id)).first()
            trek.assigned_staff_id=int(staff_id)
            db.session.commit()
            flash(f"assigned {staff.full_name} to {trek.trek_name}","success")
            return redirect(url_for("manage_staff"))

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
        
        approved_staff = Staffs.query.filter_by(approval_status="approved").all()
        opened_trek = Treks.query.filter_by(status="Open").all()
        pagination = query.paginate(page=page,per_page=5,error_out=False)
        return render_template("admin/staffs.html",staff_list=pagination.items, pagination=pagination, search_query=search_query,approved_staffs=approved_staff,opened_trek=opened_trek)
    
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
        return render_template("admin/edit_trek.html", trek=trek, approved_staff=approved_staff)
    
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
    @login_required
    @admin_required
    def admin_bookings():
        page = request.args.get("page", 1, type=int)
        pagination = Bookings.query.order_by(Bookings.booking_date.desc()).paginate(page=page, per_page=10, error_out=False)
        return render_template("admin/bookings.html", bookings=pagination.items, pagination=pagination)
    


    #staff starts from here

    @app.route("/staff/dashboard")
    @login_required
    @staff_required
    def staff_dashboard():
        assigned_treks = Treks.query.filter_by(assigned_staff_id=current_user.id).all()
        total_participants = sum(len(trek.bookings) for trek in assigned_treks)
        active_count = sum(1 for trek in assigned_treks if trek.status == "Open")

        return render_template(
            "staff/staff_dashboard.html",
            assigned_treks=assigned_treks,
            total_participants=total_participants,
            active_count=active_count
        )


    @app.route("/staff/treks/<int:trek_id>/manage", methods=["GET", "POST"])
    @login_required
    @staff_required
    def staff_manage_trek(trek_id):
        trek = Treks.query.get_or_404(trek_id)

        if trek.assigned_staff_id != current_user.id:
            abort(403)

        if request.method == "POST":
            available_slots = request.form.get("available_slots")
            status = request.form.get("status")
            progress = request.form.get("progress")
            staff_notes = request.form.get("staff_notes")

            if available_slots:
                slots = int(available_slots)
                if slots > trek.max_capacity:
                    flash("available slots cannot exceed max capacity", "warning")
                    return redirect(url_for("staff_manage_trek", trek_id=trek_id))
                trek.available_slots = slots

            if status:
                trek.status = status
            if progress:
                trek.progress = progress
            trek.staff_notes = staff_notes

            db.session.commit()
            flash("trek updated", "success")
            return redirect(url_for("staff_dashboard"))

        return render_template("staff/manage_trek.html", trek=trek)


    @app.route("/staff/treks/<int:trek_id>/participants")
    @login_required
    @staff_required
    def staff_participants(trek_id):
        trek = Treks.query.get_or_404(trek_id)

        if trek.assigned_staff_id != current_user.id:
            abort(403)

        bookings = Bookings.query.filter_by(trek_id=trek.id).all()
        return render_template("staff/participants.html", trek=trek, bookings=bookings)


    @app.route("/staff/treks/<int:trek_id>/complete", methods=["POST"])
    @login_required
    @staff_required
    def mark_trek_completed(trek_id):
        trek = Treks.query.get_or_404(trek_id)

        if trek.assigned_staff_id != current_user.id:
            abort(403)

        trek.status = "Completed"
        trek.progress = "Completed"
        db.session.commit()
        flash("trek marked as completed", "success")
        return redirect(url_for("staff_dashboard"))        