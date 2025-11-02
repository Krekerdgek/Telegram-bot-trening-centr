# -*- coding: utf-8 -*-
import logging
import sqlite3
import os
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.error import Conflict
import secrets
import string

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота из переменных окружения Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8365124344:AAHlMzG3xIGLEEOt_G3OH4W3MFrBHawNuSY")

# ID администраторов (ЗАМЕНИТЕ НА РЕАЛЬНЫЕ ID TELEGRAM)
ADMIN_IDS = [123456789]  # Замените на ваш Telegram ID

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

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

# ==================== АДМИН-ПАНЕЛЬ ====================

def get_admin_stats():
    """Получает статистику для админ-панели"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Активные пользователи
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = TRUE")
    active_users = cursor.fetchone()[0]
    
    # Все пользователи
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Группы
    cursor.execute("SELECT COUNT(*) FROM groups")
    groups_count = cursor.fetchone()[0]
    
    # Балансы
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'active_users': active_users,
        'total_users': total_users,
        'groups_count': groups_count,
        'total_balance': total_balance
    }

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает панель администратора"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return
    
    stats = get_admin_stats()
    
    # Клавиатура админ-панели
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🎯 Рассылка по группам", callback_data="admin_broadcast_groups")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "👨‍💼 *ПАНЕЛЬ АДМИНИСТРАТОРА*\n\n"
        "📊 *Текущая статистика:*\n"
        f"• 👥 Активных пользователей: {stats['active_users']}\n"
        f"• 📈 Всего зарегистрировано: {stats['total_users']}\n"
        f"• 🎯 Учебных групп: {stats['groups_count']}\n"
        f"• 💰 Общий баланс: {stats['total_balance']} руб.\n\n"
        "Выберите действие:"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок в админ-панели"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    callback_data = query.data
    
    if callback_data == "admin_stats":
        stats = get_admin_stats()
        message = (
            "📊 *Детальная статистика:*\n\n"
            f"👥 *Пользователи:*\n"
            f"• Активных: {stats['active_users']}\n"
            f"• Всего: {stats['total_users']}\n"
            f"• Конверсия: {(stats['active_users']/stats['total_users']*100):.1f}%\n\n"
            f"🎯 *Группы:* {stats['groups_count']}\n\n"
            f"💰 *Финансы:*\n"
            f"• Общий баланс: {stats['total_balance']} руб.\n"
            f"• Средний баланс: {stats['total_balance']/max(stats['active_users'], 1):.0f} руб."
        )
        await query.edit_message_text(message, parse_mode='Markdown')
        
    elif callback_data == "admin_broadcast_all":
        await query.edit_message_text(
            "📢 *Рассылка всем пользователям*\n\n"
            "Отправьте сообщение для рассылки в формате:\n"
            "`/broadcast Ваш текст сообщения`\n\n"
            "Пример:\n"
            "`/broadcast Всем привет! Напоминаем о завтрашнем занятии.`\n\n"
            "💡 *Совет:* Используйте эмодзи для привлечения внимания 🎓✨",
            parse_mode='Markdown'
        )
        
    elif callback_data == "admin_broadcast_groups":
        await show_group_broadcast_menu(query)
        
    elif callback_data == "admin_users":
        await show_users_list(query)

async def show_group_broadcast_menu(query):
    """Показывает меню рассылки по группам"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT group_id, group_name FROM groups")
    groups = cursor.fetchall()
    conn.close()
    
    keyboard = []
    for group_id, group_name in groups:
        keyboard.append([InlineKeyboardButton(f"🎯 {group_name}", callback_data=f"broadcast_group_{group_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎯 *Рассылка по группам*\n\n"
        "Выберите группу для рассылки:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_users_list(query):
    """Показывает список пользователей"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.student_name, u.phone, g.group_name, u.balance 
        FROM users u 
        LEFT JOIN groups g ON u.group_id = g.group_id 
        WHERE u.is_verified = TRUE 
        LIMIT 15
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("❌ Нет активных пользователей")
        return
    
    message = "👥 *Последние 15 пользователей:*\n\n"
    for user in users:
        name, phone, group, balance = user
        message += f"• **{name or 'Не указано'}** ({phone})\n"
        message += f"  Группа: {group or 'Не назначена'}\n"
        message += f"  Баланс: {balance} руб.\n\n"
    
    # Кнопка назад
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# ==================== РАССЫЛКИ ====================

async def send_broadcast(context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Отправляет рассылку всем пользователям"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Получаем всех верифицированных пользователей
    cursor.execute("SELECT user_id FROM users WHERE is_verified = TRUE")
    users = cursor.fetchall()
    conn.close()
    
    sent_count = 0
    failed_count = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=message_text,
                parse_mode='Markdown'
            )
            sent_count += 1
            # Задержка чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"❌ Не удалось отправить пользователю {user[0]}: {e}")
            failed_count += 1
    
    return sent_count, failed_count

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для рассылки сообщений"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 *Использование рассылки:*\n"
            "`/broadcast Ваше сообщение`\n\n"
            "Пример:\n"
            "`/broadcast Привет! Новый курс стартует 1 декабря 🎓`\n\n"
            "💡 *Форматирование:*\n"
            "• *жирный текст*\n"
            "• _курсив_\n"
            "• `моноширинный`",
            parse_mode='Markdown'
        )
        return
    
    message_text = " ".join(context.args)
    
    # Добавляем подпись от учебного центра
    full_message = f"📢 *Важное сообщение:*\n\n{message_text}\n\n— Учебный центр 'В два счёта'"
    
    await update.message.reply_text("🔄 Начинаю рассылку... Это может занять несколько минут.")
    
    sent, failed = await send_broadcast(context, full_message)
    
    await update.message.reply_text(
        f"📊 *Результаты рассылки:*\n"
        f"✅ Отправлено: {sent} пользователям\n"
        f"❌ Не удалось: {failed}",
        parse_mode='Markdown'
    )

# ==================== ОСНОВНЫЕ ФУНКЦИИ БОТА ====================

# Команда /start с описанием бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Если администратор - предлагаем админ-панель
    if is_admin(user_id):
        keyboard = [
            [KeyboardButton("🎯 Открыть админ-панель")],
            [KeyboardButton("📱 Пользовательский режим")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            "👋 *Приветствую, администратор!*\n\n"
            "Вы можете перейти в админ-панель или использовать бот как обычный пользователь.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Описание возможностей бота для обычных пользователей
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
    
    # ДЕБАГ: логируем поиск
    print(f"🔍 Поиск пользователя с кодом: '{code}'")
    
    # Ищем пользователя по коду (игнорируя user_id)
    cursor.execute('SELECT * FROM users WHERE personal_code = ?', (code,))
    user = cursor.fetchone()
    
    if user:
        print(f"✅ Пользователь найден: {user}")
        # Обновляем user_id на реальный из Telegram
        cursor.execute('UPDATE users SET user_id = ?, is_verified = TRUE WHERE personal_code = ?', 
                     (user_id, code))
        conn.commit()
        
        # Получаем обновленные данные пользователя
        cursor.execute('SELECT student_name FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        student_name = user_data[0] if user_data else "Пользователь"
        
        await update.message.reply_text(
            f"✅ *Авторизация успешна!*\n\n"
            f"👋 Добро пожаловать, {student_name}!",
            parse_mode='Markdown'
        )
        await show_main_menu(update, context)
    else:
        print(f"❌ Пользователь с кодом '{code}' не найден")
        # Показываем какие коды есть в базе для отладки
        cursor.execute('SELECT personal_code FROM users')
        all_codes = [row[0] for row in cursor.fetchall()]
        print(f"Доступные коды в базе: {all_codes}")
        
        await update.message.reply_text(
            f"❌ *Неверный код.*\n\n"
            f"Попробуйте еще раз.\n"
            f"Доступные тестовые коды: 123456, 111111, 222222\n"
            f"Коды в базе: {', '.join(all_codes) if all_codes else 'нет кодов'}",
            parse_mode='Markdown'
        )
    
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
    
    print(f"📨 Получено сообщение: '{text}' от пользователя {user_id}")
    
    # Обработка админ-команд
    if is_admin(user_id):
        if text == "🎯 Открыть админ-панель":
            await show_admin_panel(update, context)
            return
        elif text == "📱 Пользовательский режим":
            await show_auth_menu(update, context)
            return
    
    # Если ожидаем ввод кода
    if context.user_data.get('waiting_for_code'):
        print(f"🔍 Ожидаем код, получено: '{text}'")
        await verify_personal_code(update, context)
        return
    
    # Если не авторизован - показываем меню авторизации
    if not is_authenticated(user_id):
        print(f"🔐 Пользователь {user_id} не авторизован")
        if text == "🔐 Ввод персонального кода":
            print("📝 Запрос на ввод кода")
            await handle_personal_code_input(update, context)
        elif text in ["📱 Авторизация по номеру телефона", "💳 Баланс и оплата", "📅 Ближайшие занятия", "👤 Личный кабинет", "💬 Чат школы"]:
            print("🚫 Попытка доступа к функциям без авторизации")
            await show_auth_menu(update, context)
        else:
            print("🔄 Показ меню авторизации")
            await show_auth_menu(update, context)
        return
    
    # Обработка команд для авторизованных пользователей
    print(f"🎯 Авторизованный пользователь выбрал: '{text}'")
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
    # Автоматическая инициализация базы данных при запуске
    print("🔍 Проверяем базу данных...")
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    try:
        # Проверяем есть ли пользователи
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT personal_code FROM users")
        codes = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 В базе пользователей: {user_count}, коды: {codes}")
        
        if user_count == 0:
            print("🔄 База пустая, запускаем инициализацию...")
            conn.close()
            # Импортируем и запускаем инициализацию
            from init_database import init_database
            init_database()
        else:
            print("✅ База данных уже инициализирована")
            conn.close()
            
    except sqlite3.OperationalError:
        print("🔄 База не существует, создаем...")
        conn.close()
        from init_database import init_database
        init_database()
    
    # Добавляем обработчик ошибок
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.error(f'Update {update} caused error {context.error}')
        
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", show_admin_panel))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^broadcast_"))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота с обработкой конфликтов
    print("🤖 Бот запущен! Ожидаем сообщения...")
    try:
        application.run_polling()
    except Conflict as e:
        print(f"⚠️ Обнаружен конфликт: {e}")
        print("🔄 Перезапускаем бота через 10 секунд...")
        time.sleep(10)
        main()  # Рекурсивный перезапуск
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
