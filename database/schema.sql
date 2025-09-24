-- Ҷадвали корбарон
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    middle_name VARCHAR(80),
    role VARCHAR(20) NOT NULL CHECK (role IN ('dean', 'vice_dean', 'teacher', 'student', 'parent')),
    phone VARCHAR(20),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали гуруҳҳо
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    course_number INTEGER NOT NULL CHECK (course_number BETWEEN 1 AND 4),
    specialty VARCHAR(100),
    year_started INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали фанҳо
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE,
    credits INTEGER DEFAULT 3,
    hours_total INTEGER,
    hours_lecture INTEGER,
    hours_practice INTEGER,
    course_number INTEGER CHECK (course_number BETWEEN 1 AND 4),
    semester INTEGER CHECK (semester BETWEEN 1 AND 8),
    is_active BOOLEAN DEFAULT TRUE
);

-- Ҷадвали донишҷӯён
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    group_id INTEGER REFERENCES groups(id),
    admission_year INTEGER,
    birth_date DATE,
    passport_number VARCHAR(20),
    parent_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'graduated', 'expelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали муаллимон
CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    employee_id VARCHAR(20) UNIQUE,
    position VARCHAR(100),
    degree VARCHAR(50),
    department VARCHAR(100),
    hire_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали дарсҳо (пайвандкунандаи муаллим ва фан ва гуруҳ)
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id),
    teacher_id INTEGER REFERENCES teachers(id),
    group_id INTEGER REFERENCES groups(id),
    semester INTEGER,
    academic_year VARCHAR(9),
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали ҳузур
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id),
    student_id INTEGER REFERENCES students(id),
    date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'present' CHECK (status IN ('present', 'absent', 'late', 'excused')),
    activity_score DECIMAL(3,1) CHECK (activity_score BETWEEN 0 AND 6.5),
    comments TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, student_id, date)
);

-- Ҷадвали баҳоҳо
CREATE TABLE grades (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id),
    student_id INTEGER REFERENCES students(id),
    grade_type VARCHAR(20) CHECK (grade_type IN ('midterm_1', 'midterm_2', 'final', 'resit')),
    score DECIMAL(4,2),
    max_score DECIMAL(4,2) DEFAULT 100,
    date_taken DATE,
    comments TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали арзёбии рафтор
CREATE TABLE behavior_records (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    date DATE NOT NULL,
    behavior_type VARCHAR(30) CHECK (behavior_type IN ('discipline', 'ethics', 'participation', 'leadership')),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ҷадвали ҳисоботҳо
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    report_type VARCHAR(50),
    student_id INTEGER REFERENCES students(id),
    course_id INTEGER REFERENCES courses(id),
    semester INTEGER,
    academic_year VARCHAR(9),
    data JSONB,
    generated_by INTEGER REFERENCES users(id),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексҳо барои беҳтар кардани кор
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_students_student_id ON students(student_id);
CREATE INDEX idx_attendance_course_date ON attendance(course_id, date);
CREATE INDEX idx_grades_course_student ON grades(course_id, student_id);
CREATE INDEX idx_behavior_student_date ON behavior_records(student_id, date);

-- Маълумотҳои ибтидоӣ
INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES
('dean@university.tj', 'scrypt:32768:8:1$hashed_password', 'Ҷамшед', 'Раҳимов', 'dean'),
('vicedean@university.tj', 'scrypt:32768:8:1$hashed_password', 'Фарида', 'Аҳмадова', 'vice_dean');

-- Сохтани гуруҳҳо (44 гуруҳ дар 4 курс)
INSERT INTO groups (name, course_number, specialty) VALUES
('1-ИТ-А', 1, 'Технологияҳои иттилоотӣ'),
('1-ИТ-Б', 1, 'Технологияҳои иттилоотӣ'),
('1-ЭК-А', 1, 'Иқтисодиёт'),
('1-ЭК-Б', 1, 'Иқтисодиёт'),
('1-ФИЛ-А', 1, 'Филология'),
('1-ФИЛ-Б', 1, 'Филология'),
('1-ТАР-А', 1, 'Таърих'),
('1-ТАР-Б', 1, 'Таърих'),
('1-МАТ-А', 1, 'Математика'),
('1-МАТ-Б', 1, 'Математика'),
('1-ФИЗ-А', 1, 'Физика');

-- Ва ҳамчунин барои курсҳои 2, 3, 4...