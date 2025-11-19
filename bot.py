# -*- coding: utf-8 -*-
import logging
import sqlite3
import os
import time
import asyncio
import pandas as pd
import io
import requests
from datetime import datetime, timedelta
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

# ID администраторов 
ADMIN_IDS = [844196448]  # Ваш Telegram ID

# Стоимость абонемента (руб.)
MONTHLY_SUBSCRIPTION = 2000

# ==================== УПРОЩЕННЫЙ ИИ ====================

class SimpleAI:
    def get_response(self, user_message):
        """Упрощенный ИИ для учебного центра"""
        user_lower = user_message.lower()
        
        # Расписание
        if any(word in user_lower for word in ['расписан', 'когда', 'время', 'заняти', 'день', 'недел']):
            return "📅 *Расписание занятий:*\n\nЗанятия проходят по будням с 16:00 до 20:00 и по субботам с 10:00 до 14:00.\n\nЧтобы узнать ваше персональное расписание, используйте кнопку '📅 Моё расписание' в главном меню! 🎓"
        
        # Оплата и баланс
        elif any(word in user_lower for word in ['оплат', 'баланс', 'деньг', 'стоимос', 'цена', 'плат', 'денег', 'рубл', 'стоит']):
            return f"💳 *Оплата и баланс:*\n\nСтоимость абонемента: {MONTHLY_SUBSCRIPTION} руб./месяц\nИндивидуальные занятия: от 500 руб./урок\n\nТочную информацию о вашем балансе и вариантах оплаты можно найти в разделе '💳 Баланс и оплата' 💰"
        
        # Программы обучения
        elif any(word in user_lower for word in ['программ', 'предмет', 'математ', 'русск', 'лог', 'развити', 'обучен', 'курс', 'урок']):
            return "📚 *Наши программы:*\n\n• Математика (1-11 класс)\n• Русский язык и литература\n• Подготовка к школе\n• Развитие логики\n• Английский язык\n• Подготовка к ОГЭ/ЕГЭ\n\nПодробности у администратора! 🎯"
        
        # Преподаватели
        elif any(word in user_lower for word in ['преподавател', 'учител', 'педагог', 'тренер', 'кто учит']):
            return "👨‍🏫 *Наши преподаватели:*\n\nВсе наши педагоги - дипломированные специалисты с опытом работы от 5 лет. Они используют современные методики обучения и индивидуальный подход к каждому ученику! ✨"
        
        # Контакты
        elif any(word in user_lower for word in ['контакт', 'телефон', 'адрес', 'связ', 'написат', 'звонит', 'где', 'локац']):
            return "🌐 *Контакты:*\n\n• Адрес: Ивановская область, г. Родники, ул. Любимова д.36\n• Телефон: +7(901)689-34-22\n• ВКонтакте: vk.com/vdvascheta37\n• Режим работы: Пн-Пт 10:00-19:00\n\nПриходите к нам! 📍"
        
        # Приветствие
        elif any(word in user_lower for word in ['привет', 'здравств', 'добрый', 'начать', 'старт']):
            return "👋 *Добро пожаловать в учебный центр 'В два счёта'!*\n\nЯ помогу вам с информацией о:\n• 📅 Расписании занятий\n• 💳 Оплате и балансе\n• 📚 Учебных программах\n• 👨‍🏫 Преподавателях\n• 🌐 Контактах\n\nЗадайте ваш вопрос! 🎓"
        
        # Общий ответ
        else:
            return "🤖 *Чем могу помочь?*\n\nЗадайте вопрос о:\n• 📅 Расписании занятий\n• 💳 Оплате и балансе  \n• 📚 Учебных программах\n• 👨‍🏫 Преподавателях\n• 🌐 Контактах и адресе\n\nИли используйте кнопки меню для быстрого доступа! ✨"

# Создаем экземпляр ИИ
simple_ai = SimpleAI()

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

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        keyboard = [
            [KeyboardButton("🎯 Открыть админ-панель")],
            [KeyboardButton("📱 Пользовательский режим")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            "👋 *Приветствую, администратор!*\n\n"
            "Вы можете перейти в админ-панель или использовать бот как обычный пользователь.\n\n"
            "🔐 *Для админ-панели используйте:*\n"
            "`/admin 555`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    welcome_text = """
🎓 *Добро пожаловать в учебный центр "В два счёта"!*

🤖 *Этот бот поможет вам:*

📅 *Узнать расписание*
• Ваше расписание по дням недели
• Ближайшие занятия
• Время и место занятий

💳 *Контролировать финансы*
• Текущий баланс
• Автоматическое списание абонемента
• История платежей

👤 *Личный кабинет*
• Ваши персональные данные
• Статистика посещений
• Контактная информация

🌐 *Соцсети*
• Наша группа ВКонтакте
• Новости и анонсы

🤖 *Умный помощник*
• Ответы на вопросы о занятиях
• Информация о программах
• Консультации по обучению

🔐 *Для начала работы необходимо авторизоваться*
    """
    
    if is_authenticated(user_id):
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        await show_auth_menu(update, context)

async def show_auth_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню авторизации"""
    keyboard = [
        [KeyboardButton("📱 Отправить номер телефона", request_contact=True)],
        [KeyboardButton("🔐 Ввести код вручную")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "🔐 *Авторизация*\n\n"
        "Для доска к функциям бота необходимо авторизоваться.\n\n"
        "Вы можете:\n"
        "• 📱 *Отправить номер телефона* - автоматическая авторизация\n"
        "• 🔐 *Ввести код вручную* - если у вас есть персональный код\n\n"
        "Выберите способ авторизации:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📅 Моё расписание", "💳 Баланс и оплата"],
        ["👤 Личный кабинет", "🌐 ВКонтакте"],
        ["🤖 Умный помощник", "🆘 Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎯 *Главное меню*\n\n"
        "Выберите нужный раздел:\n\n"
        "📅 *Моё расписание* - расписание по дням недели\n"
        "💳 *Баланс и оплата* - финансовая информация\n"  
        "👤 *Личный кабинет* - ваши данные и статистика\n"
        "🌐 *ВКонтакте* - наша группа ВКонтакте\n"
        "🤖 *Умный помощник* - ответит на любой вопрос\n"
        "🆘 *Помощь* - справка по использованию",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по использованию бота"""
    help_text = """
🆘 *Помощь по использованию бота:*

*Основные команды:*
/start - Главное меню
/profile - Личный кабинет  
/schedule - Моё расписание
/balance - Баланс и оплата

*Основные функции:*
📅 *Расписание* - ваше расписание занятий
💳 *Баланс* - информация о платежах и балансе
👤 *Профиль* - ваши данные и статистика
🤖 *Помощник* - ответы на вопросы

*Для администраторов:*
/admin 555 - Панель управления
/broadcast - Рассылка сообщений

*Если возникли проблемы:*
1. Проверьте авторизацию (/start)
2. Обновите меню (/start)
3. Напишите в поддержку: +7(901)689-34-22
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== АВТОРИЗАЦИЯ ====================

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает отправку номера телефона"""
    user_id = update.effective_user.id
    contact = update.message.contact
    
    if contact:
        phone = contact.phone_number
        # Убираем + если есть
        if phone.startswith('+'):
            phone = phone[1:]
        
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        # Ищем пользователя по номеру телефона
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        
        if user:
            # Обновляем user_id и верифицируем
            cursor.execute(
                'UPDATE users SET user_id = ?, is_verified = TRUE WHERE phone = ?',
                (user_id, phone)
            )
            conn.commit()
            
            await update.message.reply_text(
                "✅ *Авторизация успешна!*\n\n"
                f"Добро пожаловать, {user[3]}! Теперь вам доступны все функции бота.",
                parse_mode='Markdown'
            )
            await show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ *Номер телефона не найден.*\n\n"
                "Обратитесь к администратору для получения доступа.",
                parse_mode='Markdown'
            )
        
        conn.close()
    else:
        await update.message.reply_text("❌ Не удалось получить номер телефона.")

async def handle_personal_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод персонального кода"""
    user_id = update.effective_user.id
    personal_code = update.message.text.strip()
    
    await verify_personal_code(update, context, personal_code)

async def verify_personal_code(update: Update, context: ContextTypes.DEFAULT_TYPE, personal_code: str):
    """Проверяет персональный код и авторизует пользователя"""
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE personal_code = ?', (personal_code,))
    user = cursor.fetchone()
    
    if user:
        # Обновляем user_id и верифицируем
        cursor.execute(
            'UPDATE users SET user_id = ?, is_verified = TRUE WHERE personal_code = ?',
            (user_id, personal_code)
        )
        conn.commit()
        
        await update.message.reply_text(
            "✅ *Авторизация успешна!*\n\n"
            f"Добро пожаловать, {user[3]}! Теперь вам доступны все функции бота.",
            parse_mode='Markdown'
        )
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ *Неверный персональный код.*\n\n"
            "Проверьте код и попробуйте снова или обратитесь к администратору.",
            parse_mode='Markdown'
        )
    
    conn.close()

# ==================== ФУНКЦИОНАЛ ПОЛЬЗОВАТЕЛЯ ====================

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает баланс пользователя"""
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_id = update.effective_user.id
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance, student_name FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        balance, name = user_data
        
        response = f"💳 *Баланс и оплата*\n\n"
        response += f"👤 *Студент:* {name}\n"
        response += f"💰 *Текущий баланс:* {balance} руб.\n"
        response += f"📅 *Стоимость абонемента:* {MONTHLY_SUBSCRIPTION} руб./месяц\n\n"
        
        if balance >= MONTHLY_SUBSCRIPTION:
            response += "✅ *Статус:* Оплата за следующий месяц обеспечена\n"
        else:
            needed = MONTHLY_SUBSCRIPTION - balance
            response += f"⚠️ *Статус:* Необходимо пополнить на {needed} руб.\n"
        
        response += "\n💡 *Автоматическое списание:*\n"
        response += "Абонемент автоматически списывается 1 числа каждого месяца\n"
        response += "Напоминание приходит 16 числа при нулевом балансе\n\n"
        response += "📞 *По вопросам оплаты:* +7(901)689-34-22"
        
        keyboard = [
            [InlineKeyboardButton("💳 Пополнить баланс", url="https://example.com/payment")],
            [InlineKeyboardButton("📞 Связаться с администратором", url="https://t.me/your_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Данные не найдены.")

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает личный кабинет пользователя"""
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_id = update.effective_user.id
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.student_name, u.phone, u.balance, g.group_name, u.personal_code, u.lessons_attended
        FROM users u
        LEFT JOIN groups g ON u.group_id = g.group_id
        WHERE u.user_id = ?
    ''', (user_id,))
    
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        name, phone, balance, group_name, personal_code, lessons_attended = user_data
        
        # Определяем статус платежа
        payment_status = "✅ Оплачено" if balance >= MONTHLY_SUBSCRIPTION else "❌ Требуется оплата"
        
        response = "👤 *Ваш личный кабинет:*\n\n"
        response += f"📛 *Имя:* {name or 'Не указано'}\n"
        response += f"📱 *Телефон:* {phone}\n"
        response += f"💰 *Баланс:* {balance} руб.\n"
        response += f"🎯 *Группа:* {group_name or 'Не назначена'}\n"
        response += f"📊 *Занятий посещено:* {lessons_attended}\n"
        response += f"💳 *Статус оплаты:* {payment_status}\n"
        response += f"🔐 *Персональный код:* `{personal_code}`\n\n"
        
        if balance < MONTHLY_SUBSCRIPTION:
            response += f"💡 *Для продолжения занятий необходимо пополнить баланс на {MONTHLY_SUBSCRIPTION - balance} руб.*\n\n"
        
        response += "Используйте кнопку '📅 Моё расписание' для просмотра вашего расписания!"
        
        keyboard = [
            [InlineKeyboardButton("💳 Пополнить баланс", url="https://example.com/payment")],
            [InlineKeyboardButton("📅 Моё расписание", callback_data="my_schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ *Данные не найдены.*", parse_mode='Markdown')

async def show_vkontakte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ссылку на ВКонтакте"""
    keyboard = [
        [InlineKeyboardButton("🌐 Перейти в группу ВКонтакте", url="https://vk.com/vdvascheta37")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌐 *Наша группа ВКонтакте:*\n\n"
        "Присоединяйтесь к нашему сообществу!\n\n"
        "В группе вы найдете:\n"
        "• 📢 Новости и анонсы\n"
        "• 📚 Полезные материалы\n"
        "• 📸 Фото с занятий\n"
        "• 💬 Общение с преподавателями\n"
        "• 🎯 Информацию о мероприятиях",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_my_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание пользователя по дням недели"""
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_id = update.effective_user.id
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Получаем группу пользователя
    cursor.execute('SELECT group_id FROM users WHERE user_id = ?', (user_id,))
    user_group = cursor.fetchone()
    
    if not user_group or not user_group[0]:
        await update.message.reply_text("❌ *У вас не назначена группа.*\n\nОбратитесь к администратору.")
        conn.close()
        return
    
    group_id = user_group[0]
    
    # Получаем расписание группы
    cursor.execute('''
        SELECT day_of_week, start_time, end_time, subject 
        FROM schedule 
        WHERE group_id = ? 
        ORDER BY day_of_week, start_time
    ''', (group_id,))
    
    schedule_data = cursor.fetchall()
    conn.close()
    
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    if schedule_data:
        response = "📅 *Ваше расписание:*\n\n"
        
        current_day = None
        for day_num, start_time, end_time, subject in schedule_data:
            if day_num != current_day:
                if current_day is not None:
                    response += "\n"
                response += f"*{days_of_week[day_num-1]}:*\n"
                current_day = day_num
            
            response += f"🕒 {start_time} - {end_time}: {subject}\n"
        
        response += "\n📍 *Адрес:* Ивановская область, г. Родники, ул. Любимова д.36"
    else:
        response = "❌ *Расписание для вашей группы пока не составлено.*\n\nОбратитесь к администратору."
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Проверяем авторизацию
    if not is_authenticated(user_id):
        # Если не авторизован, проверяем специальные команды
        if user_message == "🔐 Ввести код вручную":
            await update.message.reply_text(
                "🔢 *Ввод персонального кода*\n\n"
                "Пожалуйста, введите ваш 6-значный персональный код:",
                parse_mode='Markdown'
            )
            return
        elif user_message.isdigit() and len(user_message) == 6:
            await verify_personal_code(update, context, user_message)
            return
        else:
            await show_auth_menu(update, context)
            return
    
    # Обрабатываем команды главного меню для авторизованных пользователей
    if user_message == "📅 Моё расписание":
        await show_my_schedule(update, context)
    elif user_message == "💳 Баланс и оплата":
        await show_balance(update, context)
    elif user_message == "👤 Личный кабинет":
        await show_profile(update, context)
    elif user_message == "🌐 ВКонтакте":
        await show_vkontakte(update, context)
    elif user_message == "🤖 Умный помощник":
        await update.message.reply_text(
            "🤖 *Умный помощник*\n\n"
            "Задайте ваш вопрос о:\n"
            "• 📅 Расписании занятий\n"
            "• 💳 Оплате и балансе\n"
            "• 📚 Учебных программах\n"
            "• 👨‍🏫 Преподавателях\n"
            "• 🌐 Контактах и адресе\n\n"
            "Я постараюсь помочь! ✨",
            parse_mode='Markdown'
        )
    elif user_message == "🆘 Помощь":
        await help_command(update, context)
    elif user_message == "🎯 Открыть админ-панель" and is_admin(user_id):
        await update.message.reply_text(
            "🔐 *Для доступа к админ-панели используйте команду:*\n"
            "`/admin 555`",
            parse_mode='Markdown'
        )
    elif user_message == "📱 Пользовательский режим" and is_admin(user_id):
        await show_main_menu(update, context)
    else:
        # Обрабатываем через ИИ
        response = simple_ai.get_response(user_message)
        await update.message.reply_text(response, parse_mode='Markdown')

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
    
    # Пользователи с нулевым балансом
    cursor.execute("SELECT COUNT(*) FROM users WHERE balance <= 0 AND is_verified = TRUE")
    zero_balance_users = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'active_users': active_users,
        'total_users': total_users,
        'groups_count': groups_count,
        'total_balance': total_balance,
        'zero_balance_users': zero_balance_users
    }

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает панель администратора с проверкой пароля"""
    
    user_id = update.effective_user.id
    print(f"🔐 АДМИН: Запрос от пользователя {user_id}")
    
    # Сначала проверяем ID пользователя
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав доступа к админ-панели")
        return
    
    # Затем проверяем пароль
    if not context.args or context.args[0] != "555":
        await update.message.reply_text("🔐 *Требуется авторизация*\n\nНеверный пароль доступа.", parse_mode='Markdown')
        return
    
    print("✅ АДМИН: Пароль верный, показываем панель")
    
    # Пароль верный - показываем админ-панель
    stats = get_admin_stats()
    
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🎯 Рассылка по группам", callback_data="admin_broadcast_groups")],
        [InlineKeyboardButton("👤 Выборочная рассылка", callback_data="admin_broadcast_select")],
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
        f"• 💰 Общий баланс: {stats['total_balance']} руб.\n"
        f"• 🔴 С нулевым балансом: {stats['zero_balance_users']}\n\n"
        "Выберите действие:"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок в админ-панели"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещен. Недостаточно прав.")
        return
    
    callback_data = query.data
    
    if callback_data == "admin_stats":
        stats = get_admin_stats()
        message = (
            "📊 *Детальная статистика:*\n\n"
            f"👥 *Пользователи:*\n"
            f"• Активных: {stats['active_users']}\n"
            f"• Всего: {stats['total_users']}\n"
            f"• Конверсия: {(stats['active_users']/stats['total_users']*100):.1f}%\n"
            f"• С нулевым балансом: {stats['zero_balance_users']}\n\n"
            f"🎯 *Группы:* {stats['groups_count']}\n\n"
            f"💰 *Финансы:*\n"
            f"• Общий баланс: {stats['total_balance']} руб.\n"
            f"• Средний баланс: {stats['total_balance']/max(stats['active_users'], 1):.0f} руб.\n"
            f"• Стоимость абонемента: {MONTHLY_SUBSCRIPTION} руб."
        )
        await query.edit_message_text(message, parse_mode='Markdown')
        
    elif callback_data == "admin_broadcast_all":
        await query.edit_message_text(
            "📢 *Рассылка всем пользователям*\n\n"
            "Отправьте сообщение для рассылки в формате:\n"
            "`/broadcast Ваш текст сообщения`\n\n"
            "Пример:\n"
            "`/broadcast Всем привет! Напоминаем о завтрашнем занятии.`",
            parse_mode='Markdown'
        )
        
    elif callback_data == "admin_broadcast_groups":
        await show_group_broadcast_menu(query)
        
    elif callback_data == "admin_broadcast_select":
        await show_selective_broadcast_menu(query)
        
    elif callback_data == "admin_users":
        await show_users_list(query)
        
    elif callback_data == "admin_back":
        await show_admin_panel_from_callback(query)
        
    elif callback_data == "my_schedule":
        await show_my_schedule_from_callback(query, context)

async def show_my_schedule_from_callback(query, context):
    """Показывает расписание при нажатии кнопки"""
    user_id = query.from_user.id
    
    if not is_authenticated(user_id):
        await query.edit_message_text("❌ Сначала нужно авторизоваться!")
        return
    
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    # Получаем группу пользователя
    cursor.execute('SELECT group_id FROM users WHERE user_id = ?', (user_id,))
    user_group = cursor.fetchone()
    
    if not user_group or not user_group[0]:
        await query.edit_message_text("❌ У вас не назначена группа.\n\nОбратитесь к администратору.")
        conn.close()
        return
    
    group_id = user_group[0]
    
    # Получаем расписание группы
    cursor.execute('''
        SELECT day_of_week, start_time, end_time, subject 
        FROM schedule 
        WHERE group_id = ? 
        ORDER BY day_of_week, start_time
    ''', (group_id,))
    
    schedule_data = cursor.fetchall()
    conn.close()
    
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    if schedule_data:
        response = "📅 *Ваше расписание:*\n\n"
        
        current_day = None
        for day_num, start_time, end_time, subject in schedule_data:
            if day_num != current_day:
                if current_day is not None:
                    response += "\n"
                response += f"*{days_of_week[day_num-1]}:*\n"
                current_day = day_num
            
            response += f"🕒 {start_time} - {end_time}: {subject}\n"
        
        response += "\n📍 *Адрес:* Ивановская область, г. Родники, ул. Любимова д.36"
    else:
        response = "❌ *Расписание для вашей группы пока не составлено.*\n\nОбратитесь к администратору."
    
    await query.edit_message_text(response, parse_mode='Markdown')

async def show_admin_panel_from_callback(query):
    """Показывает админ-панель при нажатии кнопки назад"""
    stats = get_admin_stats()
    
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🎯 Рассылка по группам", callback_data="admin_broadcast_groups")],
        [InlineKeyboardButton("👤 Выборочная рассылка", callback_data="admin_broadcast_select")],
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
        f"• 💰 Общий баланс: {stats['total_balance']} руб.\n"
        f"• 🔴 С нулевым балансом: {stats['zero_balance_users']}\n\n"
        "Выберите действие:"
    )
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_selective_broadcast_menu(query):
    """Показывает меню выборочной рассылки"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, student_name, phone 
        FROM users 
        WHERE is_verified = TRUE 
        ORDER BY student_name
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("❌ Нет активных пользователей для рассылки")
        return
    
    keyboard = []
    # Группируем пользователей по 2 в строке
    for i in range(0, len(users), 2):
        row = []
        for j in range(i, min(i+2, len(users))):
            user_id, name, phone = users[j]
            display_name = name if name else phone
            row.append(InlineKeyboardButton(
                f"👤 {display_name}", 
                callback_data=f"select_user_{user_id}"
            ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("📢 Разослать выбранным", callback_data="send_to_selected")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 *Выборочная рассылка*\n\n"
        "Выберите пользователей для рассылки:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
        SELECT u.user_id, u.student_name, u.phone, g.group_name, u.balance, u.lessons_attended
        FROM users u 
        LEFT JOIN groups g ON u.group_id = g.group_id 
        WHERE u.is_verified = TRUE 
        LIMIT 20
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("❌ Нет активных пользователей")
        return
    
    message = "👥 *Последние 20 пользователей:*\n\n"
    for user in users:
        user_id, name, phone, group, balance, attended = user
        message += f"• **{name or 'Не указано'}** ({phone})\n"
        message += f"  Группа: {group or 'Не назначена'}\n"
        message += f"  Баланс: {balance} руб.\n"
        message += f"  Занятий посещено: {attended}\n\n"
    
    # Кнопка назад
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# ==================== РАССЫЛКИ ====================

async def send_broadcast(context: ContextTypes.DEFAULT_TYPE, message_text: str, user_ids=None):
    """Отправляет рассылку пользователям"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    if user_ids:
        # Рассылка конкретным пользователям
        users = [(user_id,) for user_id in user_ids]
    else:
        # Рассылка всем верифицированным пользователям
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
            "`/broadcast Всем привет! Напоминаем о завтрашнем занятии.`",
            parse_mode='Markdown'
        )
        return
    
    message_text = " ".join(context.args)
    full_message = f"📢 *Важное сообщение:*\n\n{message_text}\n\n— Учебный центр 'В два счёта'"
    
    await update.message.reply_text("🔄 Начинаю рассылку... Это может занять несколько минут.")
    
    sent, failed = await send_broadcast(context, full_message)
    
    await update.message.reply_text(
        f"📊 *Результаты рассылки:*\n"
        f"✅ Отправлено: {sent} пользователям\n"
        f"❌ Не удалось: {failed}",
        parse_mode='Markdown'
    )

# ==================== ОБРАБОТКА EXCEL ФАЙЛОВ ====================

async def handle_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает загрузку Excel файлов для обновления данных"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для этой операции")
        return
    
    document = update.message.document
    
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await update.message.reply_text("❌ Пожалуйста, загрузите файл в формате Excel (.xlsx или .xls)")
        return
    
    try:
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Читаем Excel
        df = pd.read_excel(io.BytesIO(file_bytes))
        
        # Обрабатываем данные
        await process_excel_data(update, df)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {str(e)}")

async def process_excel_data(update: Update, df):
    """Обрабатывает данные из Excel файла"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    updated_count = 0
    added_count = 0
    
    for index, row in df.iterrows():
        try:
            # Предполагаем структуру Excel: phone, student_name, group_id, balance
            phone = str(row.get('phone', '')).strip()
            student_name = str(row.get('student_name', '')).strip()
            group_id = int(row.get('group_id', 0))
            balance = float(row.get('balance', 0))
            
            if not phone:
                continue
            
            # Проверяем существует ли пользователь
            cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Обновляем существующего пользователя
                cursor.execute('''
                    UPDATE users 
                    SET student_name = ?, group_id = ?, balance = ?
                    WHERE phone = ?
                ''', (student_name, group_id, balance, phone))
                updated_count += 1
            else:
                # Добавляем нового пользователя
                personal_code = generate_personal_code()
                cursor.execute('''
                    INSERT INTO users (phone, personal_code, student_name, group_id, balance, is_verified)
                    VALUES (?, ?, ?, ?, ?, FALSE)
                ''', (phone, personal_code, student_name, group_id, balance))
                added_count += 1
                
        except Exception as e:
            print(f"Ошибка при обработке строки {index}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"📊 *Данные обновлены:*\n\n"
        f"✅ Добавлено: {added_count} пользователей\n"
        f"✏️ Обновлено: {updated_count} пользователей\n\n"
        f"Файл успешно обработан!",
        parse_mode='Markdown'
    )

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def main():
    print("🚀 ЗАПУСК БОТА...")
    
    # ФИКС КОНФЛИКТА - закрываем предыдущие соединения
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/close", timeout=3)
        print("✅ Закрыли предыдущие соединения с Telegram")
        time.sleep(2)
    except Exception as e:
        print(f"ℹ️ Не удалось закрыть предыдущие соединения: {e}")
    
    # Инициализация базы данных
    print("🔍 Проверяем базу данных...")
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"📊 В базе пользователей: {user_count}")
        
        if user_count == 0:
            print("🔄 База пустая, запускаем инициализацию...")
            conn.close()
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
    
    # Создаем приложение БЕЗ JobQueue
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", show_admin_panel))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("balance", show_balance))
    application.add_handler(CommandHandler("schedule", show_my_schedule))
    
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_excel_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчики для кнопок
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^broadcast_"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^select_"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^my_schedule"))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^send_to_selected"))
    
    # УБРАНЫ JobQueue обработчики чтобы избежать ошибок
    
    # Запускаем бота
    print("🤖 Бот запущен! Ожидаем сообщения...")
    try:
        application.run_polling()
    except Conflict as e:
        print(f"⚠️ Обнаружен конфликт: {e}")
        print("🔄 Перезапускаем бота через 10 секунд...")
        time.sleep(10)
        main()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
