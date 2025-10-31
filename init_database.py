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
    
    # Очищаем старые данные
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM groups") 
    cursor.execute("DELETE FROM lessons")
    
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
        (4, 3, "2024-01-15", "19:00", "Аудитория 303", "Сидоров С.С.", "scheduled")
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)', lessons)
    print("✅ Занятия добавлены")
    
    # Добавляем тестовых пользователей
    test_users = [
        (None, "+79123456789", "123456", "Иван Петров", 1, 1500.0, False),
        (None, "+79111111111", "111111", "Мария Сидорова", 2, 2000.0, False),
        (None, "+79222222222", "222222", "Алексей Иванов", 3, 1800.0, False)
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
    cursor.execute("SELECT personal_code FROM users")
    codes = [row[0] for row in cursor.fetchall()]
    print(f"📊 Коды в базе: {codes}")
    
    conn.close()
    print("🎉 База данных успешно инициализирована!")
    print("🔐 Тестовые коды: 123456, 111111, 222222")

if __name__ == '__main__':
    init_database()
