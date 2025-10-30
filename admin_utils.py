# -*- coding: utf-8 -*-
import sqlite3

def init_db():
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
    
    conn.commit()
    conn.close()
    print("Таблицы созданы успешно!")

def add_sample_data():
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Добавляем группы
    groups = [
        (1, "Математика-1", "Иванов И.И.", "Пн, Ср, Пт - 18:00"),
        (2, "Физика-1", "Петров П.П.", "Вт, Чт - 17:00"),
        (3, "Программирование-1", "Сидоров С.С.", "Пн, Ср - 19:00")
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO groups VALUES (?, ?, ?, ?)', groups)
    print("Группы добавлены!")
    
    # Добавляем занятия
    lessons = [
        (1, 1, "2024-01-15", "18:00", "Аудитория 101", "Иванов И.И.", "scheduled"),
        (2, 1, "2024-01-17", "18:00", "Аудитория 101", "Иванов И.И.", "scheduled"),
        (3, 2, "2024-01-16", "17:00", "Аудитория 202", "Петров П.П.", "scheduled"),
        (4, 3, "2024-01-15", "19:00", "Аудитория 303", "Сидоров С.С.", "scheduled")
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)', lessons)
    print("Занятия добавлены!")
    
    # Добавляем тестового пользователя
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, phone, personal_code, student_name, group_id, balance, is_verified) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (123456789, "+79123456789", "123456", "Иван Петров", 1, 1500.0, True))
    print("Тестовый пользователь добавлен!")
    
    conn.commit()
    conn.close()
    print("Все данные успешно добавлены в базу!")

def check_database():
    """Функция для проверки содержимого базы данных"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    print("\n=== ПРОВЕРКА БАЗЫ ДАННЫХ ===")
    
    # Проверяем таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Таблицы в базе:", [table[0] for table in tables])
    
    # Проверяем группы
    cursor.execute("SELECT * FROM groups")
    groups = cursor.fetchall()
    print(f"\nГруппы ({len(groups)} шт.):")
    for group in groups:
        print(f"  ID: {group[0]}, Название: {group[1]}, Преподаватель: {group[2]}")
    
    # Проверяем пользователей
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    print(f"\nПользователи ({len(users)} шт.):")
    for user in users:
        print(f"  ID: {user[0]}, Имя: {user[3]}, Телефон: {user[1]}")
    
    # Проверяем занятия
    cursor.execute("SELECT * FROM lessons")
    lessons = cursor.fetchall()
    print(f"\nЗанятия ({len(lessons)} шт.):")
    for lesson in lessons:
        print(f"  ID: {lesson[0]}, Группа: {lesson[1]}, Дата: {lesson[2]}, Время: {lesson[3]}")
    
    conn.close()

if __name__ == '__main__':
    print("Начинаем создание базы данных...")
    init_db()          # Создаем таблицы
    add_sample_data()  # Добавляем данные
    check_database()   # Показываем что получилось
    print("\nБаза данных готова к использованию!")
    input("Нажмите Enter для выхода...")