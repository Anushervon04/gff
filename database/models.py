from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    role = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()
    
    def has_role(self, role):
        return self.role == role
    
    def can_edit_attendance(self):
        return self.role in ['teacher', 'vice_dean', 'dean']
    
    def can_edit_grades(self):
        return self.role in ['teacher', 'vice_dean', 'dean']

class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    course_number = db.Column(db.Integer, nullable=False)
    specialty = db.Column(db.String(100))
    year_started = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    students = db.relationship('Student', backref='group', lazy=True)
    courses = db.relationship('Course', backref='group', lazy=True)

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    credits = db.Column(db.Integer, default=3)
    hours_total = db.Column(db.Integer)
    hours_lecture = db.Column(db.Integer)
    hours_practice = db.Column(db.Integer)
    course_number = db.Column(db.Integer)
    semester = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    
    courses = db.relationship('Course', backref='subject', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    admission_year = db.Column(db.Integer)
    birth_date = db.Column(db.Date)
    passport_number = db.Column(db.String(20))
    parent_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='student_profile')
    parent = db.relationship('User', foreign_keys=[parent_id], backref='children')
    attendance_records = db.relationship('Attendance', backref='student', lazy=True)
    grades = db.relationship('Grade', backref='student', lazy=True)
    behavior_records = db.relationship('BehaviorRecord', backref='student', lazy=True)

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.String(20), unique=True)
    position = db.Column(db.String(100))
    degree = db.Column(db.String(50))
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='teacher_profile')
    courses = db.relationship('Course', backref='teacher', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    semester = db.Column(db.Integer)
    academic_year = db.Column(db.String(9))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    attendance_records = db.relationship('Attendance', backref='course', lazy=True)
    grades = db.relationship('Grade', backref='course', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='present')
    activity_score = db.Column(db.Numeric(3, 1))
    comments = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    creator = db.relationship('User', backref='created_attendance')
    
    def can_edit(self, user):
        days_passed = (datetime.utcnow().date() - self.date).days
        if user.role == 'teacher' and days_passed <= 1:
            return True
        elif user.role in ['vice_dean', 'dean'] and days_passed <= 30:
            return True
        return False

class Grade(db.Model):
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    grade_type = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Numeric(4, 2))
    max_score = db.Column(db.Numeric(4, 2), default=100)
    date_taken = db.Column(db.Date)
    comments = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    creator = db.relationship('User', backref='created_grades')
    
    def can_edit(self, user):
        days_passed = (datetime.utcnow().date() - self.created_at.date()).days
        if user.role == 'teacher' and days_passed <= 7:
            return True
        elif user.role in ['vice_dean', 'dean'] and days_passed <= 30:
            return True
        return False

class BehaviorRecord(db.Model):
    __tablename__ = 'behavior_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    behavior_type = db.Column(db.String(30), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='created_behavior_records')

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(50))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    semester = db.Column(db.Integer)
    academic_year = db.Column(db.String(9))
    data = db.Column(db.JSON)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='reports')
    course = db.relationship('Course', backref='reports')
    generator = db.relationship('User', backref='generated_reports')