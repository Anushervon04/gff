import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tajikistan-education-crm-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost/education_crm'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Конфигуратсияи таълимӣ
    COURSES = ['Курси 1', 'Курси 2', 'Курси 3', 'Курси 4']
    GROUPS_PER_COURSE = 11  # 44 гуруҳ / 4 курс = 11 гуруҳ дар ҳар курс
    SUBJECTS_COUNT = 58
    
    # Ролҳои корбарон
    ROLES = {
        'dean': 'Декан',
        'vice_dean': 'Замдекан', 
        'teacher': 'Муаллим',
        'student': 'Донишҷӯ',
        'parent': 'Волидон'
    }
    
    # Танзимоти баҳогузорӣ
    GRADE_SYSTEM = {
        'attendance_weight': 0.3,  # 30% барои ҳузур
        'activity_weight': 0.2,    # 20% барои фаъолият
        'midterm_weight': 0.25,    # 25% барои рейтинги миёна
        'final_weight': 0.25       # 25% барои имтиҳони ниҳоӣ
    }
    
    # Вақтҳои таҳрир
    EDIT_TIMEOUTS = {
        'attendance_teacher': 1,    # 1 рӯз барои муаллим
        'grades_teacher': 7,        # 7 рӯз барои баҳо
        'grades_vice_dean': 30      # 30 рӯз барои замдекан
    }