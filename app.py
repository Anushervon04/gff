from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import json

from config import Config
from database.models import db, User, Student, Teacher, Group, Subject, Course, Attendance, Grade, BehaviorRecord, Report

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Иницилизатсияи маълумоти
    db.init_app(app)
    
    # Танзимоти Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Барои дастрасӣ ба ин саҳифа ворид шавед.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Роутҳои асосӣ
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            user = User.query.filter_by(email=email, is_active=True).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash(f'Хуш омадед, {user.full_name}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Маълумоти нодуруст. Лутфан аз нав кӯшиш кунед.', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Шумо аз система баромадед.', 'info')
        return redirect(url_for('login'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == 'dean':
            return render_template('dashboard/dean.html')
        elif current_user.role == 'vice_dean':
            return render_template('dashboard/vice_dean.html')
        elif current_user.role == 'teacher':
            return render_template('dashboard/teacher.html')
        elif current_user.role == 'student':
            return render_template('dashboard/student.html')
        elif current_user.role == 'parent':
            return render_template('dashboard/parent.html')
        else:
            flash('Дастрасии ноҷоиз', 'error')
            return redirect(url_for('logout'))
    
    # Идоракунии донишҷӯён
    @app.route('/students')
    @login_required
    def students_list():
        if current_user.role not in ['dean', 'vice_dean', 'teacher']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        
        search = request.args.get('search', '')
        group_id = request.args.get('group_id', '')
        course = request.args.get('course', '')
        
        query = Student.query.join(User).join(Group)
        
        if search:
            query = query.filter(
                (User.first_name.contains(search)) |
                (User.last_name.contains(search)) |
                (Student.student_id.contains(search))
            )
        
        if group_id:
            query = query.filter(Student.group_id == group_id)
        
        if course:
            query = query.filter(Group.course_number == course)
        
        students = query.all()
        groups = Group.query.filter_by(is_active=True).all()
        
        return render_template('students/list.html', 
                             students=students, 
                             groups=groups,
                             search=search,
                             selected_group=group_id,
                             selected_course=course)
    
    @app.route('/students/add', methods=['GET', 'POST'])
    @login_required
    def add_student():
        if current_user.role not in ['dean', 'vice_dean']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('students_list'))
        
        if request.method == 'POST':
            # Сохтани корбари донишҷӯ
            user = User(
                email=request.form['email'],
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                middle_name=request.form.get('middle_name'),
                role='student',
                phone=request.form.get('phone'),
                address=request.form.get('address')
            )
            user.set_password(request.form['password'])
            
            # Сохтани профили донишҷӯ
            student = Student(
                user=user,
                student_id=request.form['student_id'],
                group_id=request.form['group_id'],
                admission_year=request.form.get('admission_year'),
                birth_date=datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date() if request.form.get('birth_date') else None,
                passport_number=request.form.get('passport_number')
            )
            
            try:
                db.session.add(user)
                db.session.add(student)
                db.session.commit()
                flash(f'Донишҷӯи {user.full_name} бомуваффақият илова карда шуд', 'success')
                return redirect(url_for('students_list'))
            except Exception as e:
                db.session.rollback()
                flash('Хатогӣ ҳангоми илова кардан', 'error')
        
        groups = Group.query.filter_by(is_active=True).all()
        return render_template('students/add.html', groups=groups)
    
    # Идоракунии ҳузур
    @app.route('/attendance')
    @login_required
    def attendance_list():
        if current_user.role not in ['dean', 'vice_dean', 'teacher']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        
        courses = Course.query.filter_by(is_active=True)
        
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if teacher:
                courses = courses.filter_by(teacher_id=teacher.id)
        
        courses = courses.all()
        return render_template('attendance/list.html', courses=courses)
    
    @app.route('/attendance/course/')
    @login_required
    def course_attendance(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Текшириши дастрасӣ
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or course.teacher_id != teacher.id:
                flash('Дастрасӣ рад карда шуд', 'error')
                return redirect(url_for('attendance_list'))
        elif current_user.role not in ['dean', 'vice_dean']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        
        # Гирифтани донишҷӯёни гуруҳ
        students = Student.query.filter_by(group_id=course.group_id, status='active').all()
        
        # Гирифтани таърихи имрӯз
        today = datetime.now().date()
        
        # Гирифтани ҳузури имрӯз
        attendance_records = {}
        for record in Attendance.query.filter_by(course_id=course_id, date=today).all():
            attendance_records[record.student_id] = record
        
        return render_template('attendance/course.html', 
                             course=course, 
                             students=students,
                             attendance_records=attendance_records,
                             today=today)
    
    @app.route('/attendance/save', methods=['POST'])
    @login_required
    def save_attendance():
        course_id = request.form['course_id']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        course = Course.query.get_or_404(course_id)
        
        # Текшириши дастрасӣ
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or course.teacher_id != teacher.id:
                flash('Дастрасӣ рад карда шуд', 'error')
                return redirect(url_for('attendance_list'))
        elif current_user.role not in ['dean', 'vice_dean']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        
        students = Student.query.filter_by(group_id=course.group_id, status='active').all()
        
        for student in students:
            status = request.form.get(f'status_{student.id}', 'absent')
            activity = request.form.get(f'activity_{student.id}')
            comments = request.form.get(f'comments_{student.id}', '')
            
            # Ёфтан ё сохтани сабти ҳузур
            attendance = Attendance.query.filter_by(
                course_id=course_id,
                student_id=student.id,
                date=date
            ).first()
            
            if not attendance:
                attendance = Attendance(
                    course_id=course_id,
                    student_id=student.id,
                    date=date,
                    created_by=current_user.id
                )
            
            # Текшириши имкони таҳрир
            if not attendance.can_edit(current_user):
                continue
            
            attendance.status = status
            attendance.activity_score = float(activity) if activity else None
            attendance.comments = comments
            
            db.session.add(attendance)
        
        try:
            db.session.commit()
            flash('Ҳузур бомуваффақият сабт карда шуд', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Хатогӣ ҳангоми сабт кардан', 'error')
        
        return redirect(url_for('course_attendance', course_id=course_id))
    
    # Ҳисоботҳо
    @app.route('/reports')
    @login_required
    def reports_list():
        if current_user.role not in ['dean', 'vice_dean', 'teacher']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('reports/list.html')
    
    @app.route('/reports/transcript/')
    @login_required
    def student_transcript(student_id):
        student = Student.query.get_or_404(student_id)
        
        # Текшириши дастрасӣ
        if current_user.role == 'student' and current_user.id != student.user_id:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        elif current_user.role == 'parent':
            if student.parent_id != current_user.id:
                flash('Дастрасӣ рад карда шуд', 'error')
                return redirect(url_for('dashboard'))
        elif current_user.role not in ['dean', 'vice_dean', 'teacher']:
            flash('Дастрасӣ рад карда шуд', 'error')
            return redirect(url_for('dashboard'))
        
        # Ҷамъовариии маълумоти транскрипт
        courses = Course.query.filter_by(group_id=student.group_id, is_active=True).all()
        
        transcript_data = {
            'student': student,
            'courses': [],
            'total_credits': 0,
            'total_gpa': 0
        }
        
        total_points = 0
        total_credits = 0
        
        for course in courses:
            # Ҳузур
            attendance_count = Attendance.query.filter_by(
                course_id=course.id,
                student_id=student.id,
                status='present'
            ).count()
            
            total_attendance = Attendance.query.filter_by(
                course_id=course.id,
                student_id=student.id
            ).count()
            
            attendance_percentage = (attendance_count / total_attendance * 100) if total_attendance > 0 else 0
            
            # Баҳоҳо
            grades = Grade.query.filter_by(
                course_id=course.id,
                student_id=student.id
            ).all()
            
            course_grades = {}
            for grade in grades:
                course_grades[grade.grade_type] = grade.score
            
            # Ҳисоби баҳои умумӣ
            final_grade = calculate_final_grade(attendance_percentage, course_grades)
            
            transcript_data['courses'].append({
                'course': course,
                'attendance_percentage': attendance_percentage,
                'grades': course_grades,
                'final_grade': final_grade
            })
            
            if final_grade and course.subject.credits:
                total_points += final_grade * course.subject.credits
                total_credits += course.subject.credits
        
        transcript_data['total_credits'] = total_credits
        transcript_data['total_gpa'] = (total_points / total_credits) if total_credits > 0 else 0
        
        return render_template('reports/transcript.html', data=transcript_data)
    
    def calculate_final_grade(attendance_percentage, grades):
        """Ҳисоби баҳои ниҳоӣ аз рӯи коэффициентҳо"""
        config = current_app.config['GRADE_SYSTEM']
        
        total = 0
        
        # Ҳузур (30%)
        attendance_grade = min(attendance_percentage / 100 * 100, 100)
        total += attendance_grade * config['attendance_weight']
        
        # Фаъолият (20%) - аз рӯи миёнаи балҳои фаъолият
        if 'activity' in grades:
            total += grades['activity'] * config['activity_weight']
        
        # Рейтинги миёна (25%)
        if 'midterm_1' in grades and 'midterm_2' in grades:
            midterm_avg = (grades['midterm_1'] + grades['midterm_2']) / 2
            total += midterm_avg * config['midterm_weight']
        
        # Имтиҳони ниҳоӣ (25%)
        if 'final' in grades:
            total += grades['final'] * config['final_weight']
        
        return total
    
    # API endpoints
    @app.route('/api/search_students')
    @login_required
    def api_search_students():
        query = request.args.get('q', '')
        group_id = request.args.get('group_id')
        
        students_query = Student.query.join(User)
        
        if query:
            students_query = students_query.filter(
                (User.first_name.contains(query)) |
                (User.last_name.contains(query)) |
                (Student.student_id.contains(query))
            )
        
        if group_id:
            students_query = students_query.filter(Student.group_id == group_id)
        
        students = students_query.limit(20).all()
        
        result = []
        for student in students:
            result.append({
                'id': student.id,
                'student_id': student.student_id,
                'full_name': student.user.full_name,
                'group_name': student.group.name if student.group else ''
            })
        
        return jsonify(result)
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        db.create_all()
        
        # Сохтани корбари декан агар вуҷуд надошта бошад
        if not User.query.filter_by(role='dean').first():
            dean = User(
                email='dean@university.tj',
                first_name='Ҷамшед',
                last_name='Раҳимов',
                role='dean'
            )
            dean.set_password('dean123')
            db.session.add(dean)
            db.session.commit()
            print("Корбари декан сохта шуд: dean@university.tj / dean123")
    
    app.run(debug=True, host='0.0.0.0', port=5000)