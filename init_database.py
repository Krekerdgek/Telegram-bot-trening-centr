# -*- coding: utf-8 -*-
import sqlite3
import os

def init_database():
    print("🔄 Инициализация базы данных...")
    
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT UNIQUE,
            personal_code TEXT UNIQUE,
            student_name TEXT,
            group_id INTEGER,
            balance REAL DEFAULT 0,
            is_verified BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Таблица групп
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            group_name TEXT,
            teacher TEXT,
            schedule_data TEXT
        )
    ''')
    
    # Таблица занятий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id INTEGER PRIMARY KEY,
            group_id INTEGER,
            lesson_date TEXT,
            lesson_time TEXT,
            classroom TEXT,
            teacher TEXT,
            status TEXT DEFAULT 'scheduled'
        )
    ''')
    
    # Таблица расписания по дням (НОВАЯ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            day_of_week INTEGER,
            start_time TEXT,
            end_time TEXT,
            subject TEXT
        )
    ''')
    
    # Очищаем старые данные
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM groups") 
    cursor.execute("DELETE FROM lessons")
    cursor.execute("DELETE FROM schedule")
    
    print("✅ Таблицы созданы/очищены")
    
    # Добавляем группы
    groups = [
        (1, "Математика-1", "Иванов И.И.", "Пн, Ср, Пт - 18:00"),
        (2, "Физика-1", "Петров П.П.", "Вт, Чт - 17:00"),
        (3, "Программирование-1", "Сидоров С.С.", "Пн, Ср - 19:00")
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO groups VALUES (?, ?, ?, ?)', groups)
    print("✅ Группы добавлены")
    
    # Добавляем занятия
    lessons = [
        (1, 1, "2024-01-15", "18:00", "Аудитория 101", "Иванов И.И.", "scheduled"),
        (2, 1, "2024-01-17", "18:00", "Аудитория 101", "Иванов И.И.", "scheduled"),
        (3, 2, "2024-01-16", "17:00", "Аудитория 202", "Петров П.П.", "scheduled"),
        (4, 3, "2024-01-15", "19:00", "Аудитория 303", "Сидоров С.С.", "scheduled"),
        (5, 1, "2024-01-19", "18:00", "Аудитория 101", "Иванов И.И.", "scheduled"),
        (6, 2, "2024-01-18", "17:00", "Аудитория 202", "Петров П.П.", "scheduled"),
        (7, 3, "2024-01-17", "19:00", "Аудитория 303", "Сидоров С.С.", "scheduled")
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)', lessons)
    print("✅ Занятия добавлены")
    
    # Добавляем тестовое расписание (НОВОЕ)
    math_schedule = [
        (1, 1, '16:00', '17:30', 'Математика'),
        (1, 3, '16:00', '17:30', 'Математика'),
        (1, 5, '16:00', '17:30', 'Математика'),
    ]
    
    russian_schedule = [
        (2, 2, '17:00', '18:30', 'Русский язык'),
        (2, 4, '17:00', '18:30', 'Русский язык'),
    ]
    
    for schedule in math_schedule + russian_schedule:
        cursor.execute('''
            INSERT OR IGNORE INTO schedule (group_id, day_of_week, start_time, end_time, subject)
            VALUES (?, ?, ?, ?, ?)
        ''', schedule)
    
    print("✅ Расписание добавлено")
    
    # Добавляем тестовых пользователей БЕЗ user_id (он установится при авторизации)
    test_users = [
        (None, "+79123456789", "123456", "Иван Петров", 1, 1500.0, False),
        (None, "+79111111111", "111111", "Мария Сидорова", 2, 2000.0, False),
        (None, "+79222222222", "222222", "Алексей Иванов", 3, 1800.0, False),
        (None, "+79333333333", "333333", "Екатерина Смирнова", 1, 1200.0, False),
        (None, "+79444444444", "444444", "Дмитрий Козлов", 2, 2500.0, False)
    ]
    
    for user in test_users:
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, phone, personal_code, student_name, group_id, balance, is_verified) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', user)
        print(f"✅ Добавлен: {user[3]} (код: {user[2]})")
    
    conn.commit()
    
    # Проверяем что добавилось
    cursor.execute("SELECT personal_code, student_name FROM users")
    users_data = cursor.fetchall()
    
    cursor.execute("SELECT group_name FROM groups")
    groups_data = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM lessons")
    lessons_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM schedule")
    schedule_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📊 *База данных успешно инициализирована!*")
    print(f"👥 Пользователей: {len(users_data)}")
    print(f"🎯 Групп: {len(groups_data)}") 
    print(f"📅 Занятий: {lessons_count}")
    print(f"📋 Расписаний: {schedule_count}")
    
    print("\n🔐 *Тестовые коды для авторизации:*")
    for code, name in users_data:
        print(f"   {code} - {name}")
    
    print("\n🎯 *Учебные группы:*")
    for group in groups_data:
        print(f"   {group[0]}")
    
    print("\n🚀 *Бот готов к работе!*")

def check_database():
    """Проверяет состояние базы данных"""
    print("\n🔍 Проверка базы данных...")
    
    try:
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 Таблицы в базе: {[table[0] for table in tables]}")
        
        # Проверяем пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"👥 Пользователей: {users_count}")
        
        # Проверяем группы
        cursor.execute("SELECT COUNT(*) FROM groups")
        groups_count = cursor.fetchone()[0]
        print(f"🎯 Групп: {groups_count}")
        
        # Проверяем занятия
        cursor.execute("SELECT COUNT(*) FROM lessons")
        lessons_count = cursor.fetchone()[0]
        print(f"📅 Занятий: {lessons_count}")
        
        # Проверяем расписание
        cursor.execute("SELECT COUNT(*) FROM schedule")
        schedule_count = cursor.fetchone()[0]
        print(f"📋 Расписаний: {schedule_count}")
        
        # Показываем тестовые коды
        if users_count > 0:
            cursor.execute("SELECT personal_code, student_name FROM users LIMIT 5")
            test_users = cursor.fetchall()
            print("\n🔐 Тестовые коды:")
            for code, name in test_users:
                print(f"   {code} - {name}")
        
        conn.close()
        
        return users_count > 0
        
    except Exception as e:
        print(f"❌ Ошибка при проверке базы: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("🎓 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ УЧЕБНОГО ЦЕНТРА")
    print("=" * 50)
    
    # Проверяем, нужно ли инициализировать
    if not check_database():
        print("\n🔄 База данных пустая или повреждена, запускаем инициализацию...")
        init_database()
    else:
        print("\n✅ База данных уже инициализирована!")
        print("💡 Если нужно пересоздать базу, удалите файл school_bot.db")
