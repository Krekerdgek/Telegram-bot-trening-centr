# -*- coding: utf-8 -*-
import sqlite3
import os

def init_database():
    print("🔄 Инициализация базы данных...")
    
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей (ОБНОВЛЕНА - добавлено monthly_price)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT UNIQUE,
            personal_code TEXT UNIQUE,
            student_name TEXT,
            group_id INTEGER,
            balance REAL DEFAULT 0,
            monthly_price REAL DEFAULT 2000,
            is_verified BOOLEAN DEFAULT FALSE,
            lessons_attended INTEGER DEFAULT 0,
            last_payment_date TEXT
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
    
    # Таблица расписания по дням
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
    
    # НОВАЯ таблица платежей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            payment_date TEXT,
            description TEXT
        )
    ''')
    
    # Очищаем старые данные
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM groups") 
    cursor.execute("DELETE FROM lessons")
    cursor.execute("DELETE FROM schedule")
    cursor.execute("DELETE FROM payments")  # НОВОЕ - очищаем платежи
    
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
    
    # Добавляем тестовое расписание
    math_schedule = [
        (1, 1, '16:00', '17:30', 'Математика'),
        (1, 3, '16:00', '17:30', 'Математика'),
        (1, 5, '16:00', '17:30', 'Математика'),
    ]
    
    russian_schedule = [
        (2, 2, '17:00', '18:30', 'Русский язык'),
        (2, 4, '17:00', '18:30', 'Русский язык'),
    ]
    
    programming_schedule = [
        (3, 1, '19:00', '20:30', 'Программирование'),
        (3, 3, '19:00', '20:30', 'Программирование'),
    ]
    
    for schedule in math_schedule + russian_schedule + programming_schedule:
        cursor.execute('''
            INSERT OR IGNORE INTO schedule (group_id, day_of_week, start_time, end_time, subject)
            VALUES (?, ?, ?, ?, ?)
        ''', schedule)
    
    print("✅ Расписание добавлено")
    
    # Добавляем тестовых пользователей с ИНДИВИДУАЛЬНЫМИ ЦЕНАМИ
    test_users = [
        # phone, personal_code, student_name, group_id, balance, monthly_price, is_verified, lessons_attended, last_payment_date
        (None, "79123456789", "123456", "Иван Петров", 1, 3000.0, 1000.0, False, 0, None),
        (None, "79111111111", "111111", "Мария Сидорова", 2, 5000.0, 1500.0, False, 0, None),
        (None, "79222222222", "222222", "Алексей Иванов", 3, 2000.0, 1200.0, False, 0, None),
        (None, "79333333333", "333333", "Екатерина Смирнова", 1, 4500.0, 1500.0, False, 0, None),
        (None, "79444444444", "444444", "Дмитрий Козлов", 2, 6000.0, 2000.0, False, 0, None)
    ]
    
    for user in test_users:
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, phone, personal_code, student_name, group_id, balance, monthly_price, is_verified, lessons_attended, last_payment_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', user)
        print(f"✅ Добавлен: {user[3]} (код: {user[2]}, цена: {user[6]} руб./мес)")
    
    # Добавляем тестовые платежи
    test_payments = [
        (1, 3000.0, "2024-01-01 10:00:00", "Начальный баланс"),
        (2, 5000.0, "2024-01-01 10:00:00", "Начальный баланс"),
        (3, 2000.0, "2024-01-01 10:00:00", "Начальный баланс"),
        (4, 4500.0, "2024-01-01 10:00:00", "Начальный баланс"),
        (5, 6000.0, "2024-01-01 10:00:00", "Начальный баланс"),
    ]
    
    for payment in test_payments:
        cursor.execute('''
            INSERT OR IGNORE INTO payments (user_id, amount, payment_date, description)
            VALUES (?, ?, ?, ?)
        ''', payment)
    
    print("✅ Тестовые платежи добавлены")
    
    conn.commit()
    
    # Проверяем что добавилось
    cursor.execute("SELECT personal_code, student_name, monthly_price FROM users")
    users_data = cursor.fetchall()
    
    cursor.execute("SELECT group_name FROM groups")
    groups_data = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM lessons")
    lessons_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM schedule")
    schedule_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments")
    payments_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📊 *База данных успешно инициализирована!*")
    print(f"👥 Пользователей: {len(users_data)}")
    print(f"🎯 Групп: {len(groups_data)}") 
    print(f"📅 Занятий: {lessons_count}")
    print(f"📋 Расписаний: {schedule_count}")
    print(f"💳 Платежей: {payments_count}")
    
    print("\n🔐 *Тестовые коды для авторизации:*")
    for code, name, price in users_data:
        print(f"   {code} - {name} ({price} руб./мес)")
    
    print("\n🎯 *Учебные группы:*")
    for group in groups_data:
        print(f"   {group[0]}")
    
    print("\n💡 *Примеры расчета месяцев:*")
    print("   • Иван Петров: 3000 руб. / 1000 руб.мес = 3 месяца")
    print("   • Мария Сидорова: 5000 руб. / 1500 руб.мес = 3 месяца + 500 руб.")
    print("   • Алексей Иванов: 2000 руб. / 1200 руб.мес = 1 месяц + 800 руб.")
    
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
        table_names = [table[0] for table in tables]
        print(f"📋 Таблицы в базе: {table_names}")
        
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
        
        # Проверяем платежи (НОВОЕ)
        if 'payments' in table_names:
            cursor.execute("SELECT COUNT(*) FROM payments")
            payments_count = cursor.fetchone()[0]
            print(f"💳 Платежей: {payments_count}")
        
        # Проверяем наличие поля monthly_price (НОВОЕ)
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [column[1] for column in cursor.fetchall()]
        if 'monthly_price' in users_columns:
            print("✅ Поле monthly_price присутствует в таблице users")
        else:
            print("❌ Поле monthly_price отсутствует в таблице users")
        
        # Показываем тестовые коды и цены
        if users_count > 0:
            cursor.execute("SELECT personal_code, student_name, monthly_price FROM users LIMIT 5")
            test_users = cursor.fetchall()
            print("\n🔐 Тестовые коды и цены:")
            for code, name, price in test_users:
                print(f"   {code} - {name} ({price} руб./мес)")
        
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
