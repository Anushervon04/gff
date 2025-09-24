from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy import func
from database.models import (
    User,
    Role,
    Student,
    Group,
    Course,
    Enrollment,
    Attendance,
    Behavior,
    Rating,
    Exam,
    can_edit_within,
)
from database import db

api_bp = Blueprint("api", __name__)


@api_bp.post("/auth/login")
def login():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")  # optional role hint

    if not email or not password:
        return {"message": "Invalid credentials"}, 401

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if not user or not user.check_password(password):
        return {"message": "Invalid credentials"}, 401

    identity = {"id": user.id, "email": user.email, "role": user.role, "name": user.full_name}
    token = create_access_token(identity=identity)
    return {"access_token": token, "user": identity}


@api_bp.get("/me")
@jwt_required()
def me():
    return {"me": get_jwt_identity()}


@api_bp.get("/hello")
def hello():
    return {"message": "Education CRM API"}


def require_roles(*allowed_roles):
    def decorator(fn):
        from functools import wraps

        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            if identity.get("role") not in allowed_roles:
                return {"message": "Forbidden"}, 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# Core entity CRUD stubs with role restrictions

@api_bp.get("/students")
@jwt_required()
def list_students():
    ident = get_jwt_identity()
    role = ident.get("role")
    q = db.select(Student)
    if role == Role.TEACHER:
        q = (
            db.select(Student)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(Course, Course.id == Enrollment.course_id)
            .filter(Course.teacher_id == ident.get("id"))
        )
    elif role == Role.STUDENT:
        q = (
            db.select(Student)
            .join(User, User.id == Student.user_id)
            .filter(User.id == ident.get("id"))
        )
    # vice_dean and dean see all
    rows = db.session.execute(q).scalars().all()
    return [
        {
            "id": s.id,
            "uid": s.student_uid,
            "name": s.user.full_name if s.user else None,
            "group": s.group.name if s.group else None,
            "course_year": s.group.course_year if s.group else None,
        }
        for s in rows
    ]


@api_bp.post("/groups")
@require_roles(Role.DEAN, Role.VICE_DEAN)
def create_group():
    payload = request.get_json(force=True)
    g = Group(name=payload["name"], course_year=int(payload["course_year"]))
    db.session.add(g)
    db.session.commit()
    return {"id": g.id, "name": g.name, "course_year": g.course_year}


@api_bp.post("/courses")
@require_roles(Role.DEAN, Role.VICE_DEAN)
def create_course():
    payload = request.get_json(force=True)
    c = Course(
        code=payload["code"],
        title=payload["title"],
        total_hours=int(payload.get("total_hours", 0)),
        teacher_id=payload.get("teacher_id"),
    )
    db.session.add(c)
    db.session.commit()
    return {"id": c.id, "code": c.code}


@api_bp.post("/students")
@require_roles(Role.DEAN, Role.VICE_DEAN)
def create_student():
    payload = request.get_json(force=True)
    # assumes user already created by dean
    user_id = payload["user_id"]
    group_id = payload["group_id"]
    student_uid = payload["student_uid"]
    s = Student(user_id=user_id, group_id=group_id, student_uid=student_uid)
    db.session.add(s)
    db.session.commit()
    return {"id": s.id}


@api_bp.post("/enrollments")
@require_roles(Role.DEAN, Role.VICE_DEAN)
def create_enrollment():
    payload = request.get_json(force=True)
    e = Enrollment(
        student_id=payload["student_id"],
        course_id=payload["course_id"],
        year=int(payload["year"]),
        semester=int(payload["semester"]),
    )
    db.session.add(e)
    db.session.commit()
    return {"id": e.id}


# Attendance: teacher can add within 1 day; vice_dean 30 days; dean full
@api_bp.post("/attendance")
@jwt_required()
def add_attendance():
    ident = get_jwt_identity()
    payload = request.get_json(force=True)
    enrollment_id = int(payload["enrollment_id"])
    present = bool(payload.get("present", False))
    activity_score = payload.get("activity_score")
    att = Attendance(
        enrollment_id=enrollment_id,
        date=payload.get("date"),
        present=present,
        activity_score=activity_score,
        created_by=ident.get("id"),
    )
    db.session.add(att)
    db.session.commit()
    return {"id": att.id}


@api_bp.put("/attendance/<int:att_id>")
@jwt_required()
def update_attendance(att_id: int):
    ident = get_jwt_identity()
    role = ident.get("role")
    att = db.session.get(Attendance, att_id)
    if not att:
        return {"message": "Not found"}, 404
    # edit windows
    if role == Role.TEACHER and not can_edit_within(att.created_at, 1):
        return {"message": "Edit window closed"}, 403
    if role == Role.VICE_DEAN and not can_edit_within(att.created_at, 30):
        return {"message": "Edit window closed"}, 403
    # dean allowed anytime
    payload = request.get_json(force=True)
    if "present" in payload:
        att.present = bool(payload["present"])
    if "activity_score" in payload:
        att.activity_score = payload["activity_score"]
    db.session.commit()
    return {"ok": True}


# Behavior notes: comment-like notes
@api_bp.post("/behavior")
@jwt_required()
def add_behavior():
    ident = get_jwt_identity()
    payload = request.get_json(force=True)
    b = Behavior(
        student_id=payload["student_id"],
        course_id=payload.get("course_id"),
        date=payload.get("date"),
        note=payload["note"],
        created_by=ident.get("id"),
    )
    db.session.add(b)
    db.session.commit()
    return {"id": b.id}


# Ratings derived or manual
@api_bp.post("/ratings")
@jwt_required()
def add_rating():
    ident = get_jwt_identity()
    payload = request.get_json(force=True)
    r = Rating(
        enrollment_id=payload["enrollment_id"],
        period=payload["period"],  # "2m" or "4m"
        value=payload["value"],
        created_by=ident.get("id"),
    )
    db.session.add(r)
    db.session.commit()
    return {"id": r.id}


@api_bp.post("/exams")
@jwt_required()
def add_exam():
    ident = get_jwt_identity()
    payload = request.get_json(force=True)
    ex = Exam(
        enrollment_id=payload["enrollment_id"],
        exam_type=payload["exam_type"],
        score=payload["score"],
        date=payload["date"],
        created_by=ident.get("id"),
    )
    db.session.add(ex)
    db.session.commit()
    return {"id": ex.id}


def _counts_for_role(identity):
    role = identity.get("role")
    user_id = identity.get("id")
    # Base counts
    students_q = db.select(func.count()).select_from(Student)
    groups_q = db.select(func.count()).select_from(Group)
    courses_q = db.select(func.count()).select_from(Course)
    enroll_q = db.select(func.count()).select_from(Enrollment)

    if role == Role.DEAN:
        pass  # full
    elif role == Role.VICE_DEAN:
        pass  # similar to dean for counts; detailed endpoints will filter
    elif role == Role.TEACHER:
        # limit to courses where teacher_id=user_id
        courses_q = db.select(func.count()).select_from(Course).filter_by(teacher_id=user_id)
        enroll_q = (
            db.select(func.count())
            .select_from(Enrollment)
            .join(Course, Course.id == Enrollment.course_id)
            .filter(Course.teacher_id == user_id)
        )
        # students in those enrollments
        students_q = (
            db.select(func.count())
            .select_from(Student)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(Course, Course.id == Enrollment.course_id)
            .filter(Course.teacher_id == user_id)
        )
    elif role == Role.STUDENT:
        # only self
        students_q = (
            db.select(func.count())
            .select_from(Student)
            .join(User, User.id == Student.user_id)
            .filter(User.id == user_id)
        )
        # groups: their group only
        groups_q = (
            db.select(func.count())
            .select_from(Group)
            .join(Student, Student.group_id == Group.id)
            .join(User, User.id == Student.user_id)
            .filter(User.id == user_id)
        )
        # courses/enrollments they are enrolled in
        enroll_q = db.select(func.count()).select_from(Enrollment).join(Student).join(User).filter(User.id == user_id)
        courses_q = (
            db.select(func.count())
            .select_from(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .join(Student, Student.id == Enrollment.student_id)
            .join(User, User.id == Student.user_id)
            .filter(User.id == user_id)
        )
    else:
        # parent: similar to student but filtered later by child mapping (not modeled yet)
        pass

    return {
        "students": db.session.execute(students_q).scalar() or 0,
        "groups": db.session.execute(groups_q).scalar() or 0,
        "courses": db.session.execute(courses_q).scalar() or 0,
        "enrollments": db.session.execute(enroll_q).scalar() or 0,
    }


@api_bp.get("/visibility/counts")
@jwt_required()
def visibility_counts():
    ident = get_jwt_identity()
    return _counts_for_role(ident)


# Dean-only example endpoint to create accounts for students/teachers
@api_bp.post("/admin/create_user")
@require_roles(Role.DEAN)
def admin_create_user():
    payload = request.get_json(force=True)
    email = payload["email"]
    password = payload["password"]
    role = payload["role"]
    full_name = payload.get("full_name", "")
    if role not in {Role.STUDENT, Role.TEACHER, Role.VICE_DEAN, Role.DEAN, Role.PARENT}:
        return {"message": "Invalid role"}, 400
    if db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none():
        return {"message": "Email already exists"}, 409
    user = User(email=email, role=role, full_name=full_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return {"id": user.id, "email": user.email, "role": user.role}

