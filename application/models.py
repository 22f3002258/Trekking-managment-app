from application.extensions import db
from flask_login import UserMixin
from datetime import datetime


class Users(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_no = db.Column(db.String(15), nullable=False, unique=True)
    emergency_contact = db.Column(db.String(15), nullable=False)
    status = db.Column(db.String(20), default="active")

    def get_id(self):
        return f"user-{self.id}"


class Staffs(db.Model, UserMixin):
    __tablename__ = "staffs"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_no = db.Column(db.String(15), nullable=False, unique=True)
    exp = db.Column(db.String(10), nullable=False)
    approval_status = db.Column(db.String(20), default="pending")

    def get_id(self):
        return f"staff-{self.id}"


class Admins(db.Model, UserMixin):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"admin-{self.id}"


class Treks(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    trek_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Integer)
    difficulty = db.Column(db.String(20))
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    meeting_point = db.Column(db.String(150))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")
    progress = db.Column(db.String(20), default="Not Started")
    staff_notes = db.Column(db.Text)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"))


class Bookings(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Booked") 