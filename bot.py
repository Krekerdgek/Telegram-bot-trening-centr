# -*- coding: utf-8 -*-
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import secrets
import string

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "8365124344:AAHlMzG3xIGLEEOt_G3OH4W3MFrBHawNuSY"

# Инициализация базы данных
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

# Генерация персонального кода
def generate_personal_code():
    return ''.join(secrets.choice(string.digits) for _ in range(6))

# Проверка авторизации
def is_authenticated(user_id):
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_verified FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0]

# Команда /start с описанием бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Описание возможностей бота
    welcome_text = """
🎓 *Добро пожаловать в учебный центр "В два счёта"!*

🤖 *Этот бот поможет вам:*

📅 *Узнать расписание*
• Какая у вас группа
• Время и место занятий  
• Изменения в расписании
• Пропущенные занятия
• Информация о преподавателях

💳 *Контролировать финансы*
• Текущий баланс абонемента
• Быстрая оплата занятий
• История платежей

👤 *Личный кабинет*
• Ваши персональные данные
• Контактная информация
• Учебный прогресс

💬 *Общение*
• Ссылки на чаты школы
• Общение с группой

🔐 *Для начала работы необходимо авторизоваться*
    """
    
    if is_authenticated(user_id):
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        await show_auth_menu(update, context)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Помощь по использованию бота*

*Основные функции:*

📅 *Ближайшие занятия* - покажет ваше расписание на ближайшие дни
💳 *Баланс и оплата* - информация о балансе и оплата занятий
👤 *Личный кабинет* - ваши персональные данные
💬 *Чат школы* - переход в чаты для общения

*Способы авторизации:*
📱 *По номеру телефона* - используйте ваш зарегистрированный номер
🔐 *По персональному коду* - код, выданный учебным центром

*Если возникли проблемы:*
• Проверьте подключение к интернету
• Убедитесь, что используете правильный номер телефона или код
• При необходимости обратитесь в учебный центр

*Команды:*
/start - начать работу с ботом
/help - показать эту справку
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def show_auth_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📱 Авторизация по номеру телефона", request_contact=True)],
        [KeyboardButton("🔐 Ввод персонального кода")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🔐 *Выберите способ авторизации:*\n\n"
        "📱 *По номеру телефона* - если ваш номер уже зарегистрирован в учебном центре\n"
        "🔐 *По персональному коду* - код, который вам выдали при записи",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📅 Ближайшие занятия", "💳 Баланс и оплата"],
        ["👤 Личный кабинет", "💬 Чат школы"],
        ["🔄 Обновить данные", "🆘 Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎯 *Главное меню*\n\n"
        "Выберите нужный раздел:\n\n"
        "📅 *Ближайшие занятия* - ваше расписание\n"
        "💳 *Баланс и оплата* - финансовая информация\n"  
        "👤 *Личный кабинет* - ваши данные\n"
        "💬 *Чат школы* - общение с сообществом\n"
        "🔄 *Обновить данные* - актуализировать информацию\n"
        "🆘 *Помощь* - справка по использованию",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработка номера телефона
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        user_id = update.effective_user.id
        
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        # Проверяем есть ли пользователь с таким номером
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        
        if user:
            # Обновляем user_id для существующего пользователя
            cursor.execute('UPDATE users SET user_id = ?, is_verified = TRUE WHERE phone = ?', 
                         (user_id, phone))
            await update.message.reply_text("✅ *Авторизация успешна!*", parse_mode='Markdown')
            await show_main_menu(update, context)
        else:
            # Создаем нового пользователя
            personal_code = generate_personal_code()
            cursor.execute(
                'INSERT INTO users (user_id, phone, personal_code, is_verified) VALUES (?, ?, ?, TRUE)',
                (user_id, phone, personal_code)
            )
            await update.message.reply_text(
                f"✅ *Регистрация успешна!*\n\n"
                f"🔐 *Ваш персональный код:* `{personal_code}`\n"
                f"📝 *Сохраните его для будущих входов*",
                parse_mode='Markdown'
            )
            await show_main_menu(update, context)
        
        conn.commit()
        conn.close()

# Обработка персонального кода
async def handle_personal_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Устанавливаем флаг, что ожидаем ввод кода
    context.user_data['waiting_for_code'] = True
    await update.message.reply_text(
        "🔢 *Введите ваш персональный код:*\n\n"
        "Код состоит из 6 цифр и был выдан вам при записи в учебный центр",
        parse_mode='Markdown'
    )

async def verify_personal_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE personal_code = ?', (code,))
    user = cursor.fetchone()
    
    if user:
        cursor.execute('UPDATE users SET user_id = ?, is_verified = TRUE WHERE personal_code = ?', 
                     (user_id, code))
        await update.message.reply_text("✅ *Авторизация успешна!*", parse_mode='Markdown')
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ *Неверный код.*\n\n"
            "Попробуйте еще раз или используйте авторизацию по номеру телефона.\n"
            "Если проблема сохраняется, обратитесь в учебный центр.",
            parse_mode='Markdown'
        )
    
    conn.commit()
    conn.close()
    context.user_data['waiting_for_code'] = False

# Ближайшие занятия
async def show_upcoming_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_id = update.effective_user.id
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Получаем информацию о пользователе и его занятиях
    cursor.execute('''
        SELECT u.group_id, g.group_name, l.lesson_date, l.lesson_time, 
               l.classroom, l.teacher, l.status
        FROM users u
        LEFT JOIN groups g ON u.group_id = g.group_id
        LEFT JOIN lessons l ON u.group_id = l.group_id
        WHERE u.user_id = ? AND l.lesson_date >= date('now')
        ORDER BY l.lesson_date, l.lesson_time
        LIMIT 5
    ''', (user_id,))
    
    lessons = cursor.fetchall()
    conn.close()
    
    if lessons:
        response = "📅 *Ваши ближайшие занятия:*\n\n"
        for lesson in lessons:
            group_id, group_name, date, time, classroom, teacher, status = lesson
            response += f"🎯 *Группа:* {group_name}\n"
            response += f"⏰ *Время:* {date} в {time}\n"
            response += f"🏫 *Аудитория:* {classroom}\n"
            response += f"👨‍🏫 *Преподаватель:* {teacher}\n"
            response += f"📊 *Статус:* {status}\n"
            response += "─" * 30 + "\n"
        
        response += "\n🔄 Для обновления информации используйте кнопку \"Обновить данные\""
    else:
        response = "❌ *Ближайшие занятия не найдены.*\n\nОбратитесь в учебный центр для уточнения расписания."
    
    await update.message.reply_text(response, parse_mode='Markdown')

# Баланс и оплата
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_id = update.effective_user.id
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    balance = cursor.fetchone()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", url="https://example.com/payment")],
        [InlineKeyboardButton("📊 История платежей", callback_data="payment_history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💰 *Ваш текущий баланс:* {balance[0] if balance else 0} руб.\n\n"
        "💡 *Для пополнения баланса нажмите кнопку ниже:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Личный кабинет
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_id = update.effective_user.id
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.student_name, u.phone, u.balance, g.group_name, u.personal_code
        FROM users u
        LEFT JOIN groups g ON u.group_id = g.group_id
        WHERE u.user_id = ?
    ''', (user_id,))
    
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        name, phone, balance, group_name, personal_code = user_data
        response = "👤 *Ваш личный кабинет:*\n\n"
        response += f"📛 *Имя:* {name or 'Не указано'}\n"
        response += f"📱 *Телефон:* {phone}\n"
        response += f"💰 *Баланс:* {balance} руб.\n"
        response += f"🎯 *Группа:* {group_name or 'Не назначена'}\n"
        response += f"🔐 *Персональный код:* `{personal_code}`\n\n"
        response += "💡 *Сохраните ваш персональный код для будущих входов*"
        
        keyboard = [
            [InlineKeyboardButton("💳 Пополнить баланс", url="https://example.com/payment")],
            [InlineKeyboardButton("✏️ Изменить данные", callback_data="edit_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ *Данные не найдены.*", parse_mode='Markdown')

# Чат школы
async def show_school_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 Общий чат школы", url="https://t.me/your_school_chat")],
        [InlineKeyboardButton("📚 Чат вашей группы", url="https://t.me/your_group_chat")],
        [InlineKeyboardButton("📞 Техподдержка", url="https://t.me/your_support_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💬 *Чаты учебного центра:*\n\n"
        "Выберите чат для общения:\n\n"
        "💬 *Общий чат школы* - общение со всеми учениками\n"
        "📚 *Чат вашей группы* - общение с вашей учебной группой\n"
        "📞 *Техподдержка* - помощь по техническим вопросам",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Если ожидаем ввод кода
    if context.user_data.get('waiting_for_code'):
        await verify_personal_code(update, context)
        return
    
    # Если не авторизован - показываем меню авторизации
    if not is_authenticated(user_id):
        if text == "🔐 Ввод персонального кода":
            await handle_personal_code_input(update, context)
        else:
            await show_auth_menu(update, context)
        return
    
    # Обработка команд для авторизованных пользователей
    if text == "📅 Ближайшие занятия":
        await show_upcoming_lessons(update, context)
    elif text == "💳 Баланс и оплата":
        await show_balance(update, context)
    elif text == "👤 Личный кабинет":
        await show_profile(update, context)
    elif text == "💬 Чат школы":
        await show_school_chat(update, context)
    elif text == "🔄 Обновить данные":
        await update.message.reply_text("✅ *Данные обновлены!*", parse_mode='Markdown')
    elif text == "🆘 Помощь":
        await help_command(update, context)
    elif text == "🔐 Ввод персонального кода":
        await handle_personal_code_input(update, context)
    else:
        await update.message.reply_text(
            "🤔 *Не понял ваше сообщение*\n\n"
            "Используйте кнопки меню для навигации или /help для справки",
            parse_mode='Markdown'
        )

# Основная функция
def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков в правильном порядке
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    print("Бот запущен! Ожидаем сообщения...")
    application.run_polling()

if __name__ == '__main__':
    main()