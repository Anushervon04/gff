from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from passlib.hash import bcrypt

db = SQLAlchemy()


class Role:
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    VICE_DEAN = "vice_dean"
    DEAN = "dean"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student_profile = db.relationship("Student", uselist=False, back_populates="user")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.password_hash)


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    course_year = db.Column(db.Integer, nullable=False)  # 1..4


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True)
    title = db.Column(db.String(255), nullable=False)
    total_hours = db.Column(db.Integer, nullable=False, default=0)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    teacher = db.relationship("User", foreign_keys=[teacher_id])


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    student_uid = db.Column(db.String(64), unique=True, nullable=False)

    user = db.relationship("User", back_populates="student_profile")
    group = db.relationship("Group")


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # academic year e.g., 2025
    semester = db.Column(db.Integer, nullable=False)  # 1 or 2

    student = db.relationship("Student")
    course = db.relationship("Course")


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollments.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    present = db.Column(db.Boolean, default=False, nullable=False)
    activity_score = db.Column(db.Numeric(3, 1), nullable=True)  # up to 6.5
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    enrollment = db.relationship("Enrollment")


class Behavior(db.Model):
    __tablename__ = "behavior"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollments.id"), nullable=False)
    period = db.Column(db.String(16), nullable=False)  # "2m" or "4m"
    value = db.Column(db.Numeric(5, 2), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollments.id"), nullable=False)
    exam_type = db.Column(db.String(32), nullable=False)  # midterm/final/etc
    score = db.Column(db.Numeric(5, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def can_edit_within(created_at: datetime, days: int) -> bool:
    return datetime.utcnow() <= created_at + timedelta(days=days)

