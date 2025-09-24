from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from database.models import db, User, Student, Teacher, Group, Subject, Course, Attendance, Grade, BehaviorRecord
from datetime import datetime, timedelta
import json

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/students/search')
@login_required
def search_students():
    """Ҷустуҷӯи донишҷӯён"""
    query = request.args.get('q', '').strip()
    group_id = request.args.get('group_id')
    course = request.args.get('course')
    limit = min(int(request.args.get('limit', 20)), 100)
    
    students_query = Student.query.join(User).join(Group)
    
    # Фильтр аз рӯи ҷустуҷӯ
    if query:
        students_query = students_query.filter(
            db.or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                Student.student_id.ilike(f'%{query}%')
            )
        )
    
    # Фильтр аз рӯи гуруҳ
    if group_id:
        students_query = students_query.filter(Student.group_id == group_id)
    
    # Фильтр аз рӯи курс
    if course:
        students_query = students_query.filter(Group.course_number == course)
    
    # Маҳдудият дастрасӣ барои муаллим
    if current_user.role == 'teacher':
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        if teacher:
            course_groups = Course.query.filter_by(teacher_id=teacher.id).with_entities(Course.group_id).distinct()
            group_ids = [cg.group_id for cg in course_groups]
            students_query = students_query.filter(Student.group_id.in_(group_ids))
    
    students = students_query.limit(limit).all()
    
    result = []
    for student in students:
        result.append({
            'id': student.id,
            'student_id': student.student_id,
            'full_name': student.user.full_name,
            'group_name': student.group.name if student.group else '',
            'course_number': student.group.course_number if student.group else None,
            'status': student.status
        })
    
    return jsonify({
        'success': True,
        'data': result,
        'count': len(result)
    })

@api.route('/attendance/bulk_save', methods=['POST'])
@login_required
def bulk_save_attendance():
    """Сабти якбораи ҳузур"""
    if current_user.role not in ['teacher', 'vice_dean', 'dean']:
        return jsonify({'success': False, 'error': 'Дастрасӣ рад карда шуд'}), 403
    
    data = request.get_json()
    course_id = data.get('course_id')
    date_str = data.get('date')
    attendance_data = data.get('attendance', [])
    
    if not all([course_id, date_str, attendance_data]):
        return jsonify({'success': False, 'error': 'Маълумоти ноқис'}), 400
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'success': False, 'error': 'Дарс ёфт нашуд'}), 404
        
        # Текшириши дастрасӣ барои муаллим
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or course.teacher_id != teacher.id:
                return jsonify({'success': False, 'error': 'Дастрасӣ рад карда шуд'}), 403
        
        saved_count = 0
        for item in attendance_data:
            student_id = item.get('student_id')
            status = item.get('status', 'absent')
            activity_score = item.get('activity_score')
            comments = item.get('comments', '')
            
            # Ёфтан ё сохтани сабти ҳузур
            attendance = Attendance.query.filter_by(
                course_id=course_id,
                student_id=student_id,
                date=date
            ).first()
            
            if not attendance:
                attendance = Attendance(
                    course_id=course_id,
                    student_id=student_id,
                    date=date,
                    created_by=current_user.id
                )
            
            # Текшириши имкони таҳрир
            if attendance.can_edit(current_user):
                attendance.status = status
                attendance.activity_score = float(activity_score) if activity_score else None
                attendance.comments = comments
                
                db.session.add(attendance)
                saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} сабти ҳузур нигоҳ дошта шуд',
            'saved_count': saved_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/grades/save', methods=['POST'])
@login_required
def save_grade():
    """Сабти баҳо"""
    if current_user.role not in ['teacher', 'vice_dean', 'dean']:
        return jsonify({'success': False, 'error': 'Дастрасӣ рад карда шуд'}), 403
    
    data = request.get_json()
    course_id = data.get('course_id')
    student_id = data.get('student_id')
    grade_type = data.get('grade_type')
    score = data.get('score')
    comments = data.get('comments', '')
    
    if not all([course_id, student_id, grade_type]):
        return jsonify({'success': False, 'error': 'Маълумоти ноқис'}), 400
    
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'success': False, 'error': 'Дарс ёфт нашуд'}), 404
        
        # Текшириши дастрасӣ барои муаллим
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or course.teacher_id != teacher.id:
                return jsonify({'success': False, 'error': 'Дастрасӣ рад карда шуд'}), 403
        
        # Ёфтан ё сохтани баҳо
        grade = Grade.query.filter_by(
            course_id=course_id,
            student_id=student_id,
            grade_type=grade_type
        ).first()
        
        if not grade:
            grade = Grade(
                course_id=course_id,
                student_id=student_id,
                grade_type=grade_type,
                created_by=current_user.id
            )
        
        # Текшириши имкони таҳрир
        if grade.can_edit(current_user):
            grade.score = float(score) if score else None
            grade.comments = comments
            grade.date_taken = datetime.now().date()
            
            db.session.add(grade)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Баҳо бомуваффақият сабт карда шуд'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Вақти таҳрир гузаштааст'
            }), 403
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/behavior/save', methods=['POST'])
@login_required
def save_behavior():
    """Сабти арзёбии рафтор"""
    if current_user.role not in ['teacher', 'vice_dean', 'dean']:
        return jsonify({'success': False, 'error': 'Дастрасӣ рад карда шуд'}), 403
    
    data = request.get_json()
    student_id = data.get('student_id')
    behavior_type = data.get('behavior_type')
    rating = data.get('rating')
    description = data.get('description', '')
    date_str = data.get('date')
    
    if not all([student_id, behavior_type, rating]):
        return jsonify({'success': False, 'error': 'Маълумоти ноқис'}), 400
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
        
        behavior_record = BehaviorRecord(
            student_id=student_id,
            date=date,
            behavior_type=behavior_type,
            rating=int(rating),
            description=description,
            created_by=current_user.id
        )
        
        db.session.add(behavior_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Арзёбии рафтор сабт карда шуд'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/statistics/dashboard')
@login_required
def dashboard_statistics():
    """Статистика барои dashboard"""
    stats = {}
    
    if current_user.role in ['dean', 'vice_dean']:
        # Умумӣ статистика
        stats['total_students'] = Student.query.filter_by(status='active').count()
        stats['total_teachers'] = Teacher.query.count()
        stats['total_groups'] = Group.query.filter_by(is_active=True).count()
        stats['total_subjects'] = Subject.query.filter_by(is_active=True).count()
        
        # Статистикаи ҳузур (ҳафтаи охир)
        week_ago = datetime.now().date() - timedelta(days=7)
        total_attendance = Attendance.query.filter(Attendance.date >= week_ago).count()
        present_count = Attendance.query.filter(
            Attendance.date >= week_ago,
            Attendance.status == 'present'
        ).count()
        
        stats['attendance_rate'] = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # Статистикаи курсҳо
        stats['courses_by_year'] = {}
        for i in range(1, 5):
            count = Group.query.filter_by(course_number=i, is_active=True).count()
            stats['courses_by_year'][f'course_{i}'] = count
    
    elif current_user.role == 'teacher':
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        if teacher:
            # Дарсҳои муаллим
            my_courses = Course.query.filter_by(teacher_id=teacher.id, is_active=True).all()
            stats['my_courses_count'] = len(my_courses)
            
            # Донишҷӯёни ман
            group_ids = [course.group_id for course in my_courses]
            stats['my_students_count'] = Student.query.filter(
                Student.group_id.in_(group_ids),
                Student.status == 'active'
            ).count() if group_ids else 0
    
    elif current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        if student:
            # Маълумоти донишҷӯ
            stats['my_group'] = student.group.name if student.group else ''
            stats['my_course'] = student.group.course_number if student.group else 0
            
            # Ҳузури ман (моҳи охир)
            month_ago = datetime.now().date() - timedelta(days=30)
            my_attendance = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date >= month_ago
            ).count()
            
            my_present = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date >= month_ago,
                Attendance.status == 'present'
            ).count()
            
            stats['my_attendance_rate'] = (my_present / my_attendance * 100) if my_attendance > 0 else 0
    
    return jsonify({
        'success': True,
        'data': stats
    })

@api.route('/reports/attendance_summary')
@login_required
def attendance_summary_report():
    """Ҳисоботи хулосавии ҳузур"""
    if current_user.role not in ['dean', 'vice_dean', 'teacher']:
        return jsonify({'success': False, 'error': 'Дастрасӣ рад карда шуд'}), 403
    
    group_id = request.args.get('group_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not all([group_id, start_date, end_date]):
        return jsonify({'success': False, 'error': 'Маълумоти ноқис'}), 400
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        students = Student.query.filter_by(group_id=group_id, status='active').all()
        
        report_data = []
        for student in students:
            total_classes = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date.between(start, end)
            ).count()
            
            present_classes = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date.between(start, end),
                Attendance.status == 'present'
            ).count()
            
            attendance_rate = (present_classes / total_classes * 100) if total_classes > 0 else 0
            
            report_data.append({
                'student_id': student.student_id,
                'full_name': student.user.full_name,
                'total_classes': total_classes,
                'present_classes': present_classes,
                'absent_classes': total_classes - present_classes,
                'attendance_rate': round(attendance_rate, 2)
            })
        
        return jsonify({
            'success': True,
            'data': report_data,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500