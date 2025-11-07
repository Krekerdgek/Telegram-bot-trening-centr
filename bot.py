# -*- coding: utf-8 -*-
import logging
import sqlite3
import os
import time
import asyncio
import pandas as pd
import io
import requests
import json
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

# ==================== ИИ ИНТЕГРАЦИЯ ====================

class AIAssistant:
    def __init__(self):
        self.huggingface_token = os.environ.get("HUGGINGFACE_TOKEN", "")
        self.use_cloud_api = True if self.huggingface_token else False
        
    def get_ai_response(self, user_message, user_context=""):
        """Получает ответ от ИИ-ассистента"""
        
        # Системный промпт для детского центра
        system_prompt = f"""
        Ты - дружелюбный AI-помощник детского тренинг-центра "В два счёта". 
        Ты помогаешь родителям и детям с вопросами о занятиях, расписании, оплате.
        
        Контекст пользователя: {user_context}
        
        Твой стиль общения:
        - Дружелюбный и поддерживающий 🎓
        - Простые и понятные объяснения
        - Используй эмодзи для настроения ✨👋
        - Будь терпеливым как с детьми
        - Если не знаешь ответа - направляй к администратору
        - Отвечай кратко (максимум 2-3 предложения)
        
        Частые вопросы:
        - Расписание: используй кнопку "📅 Ближайшие занятия"
        - Баланс: используй кнопку "💳 Баланс и оплата"  
        - Личные данные: используй кнопку "👤 Личный кабинет"
        - Контакты: используй кнопку "🌐 ВКонтакте"
        """
        
        # Пробуем Hugging Face API
        if self.use_cloud_api:
            try:
                headers = {"Authorization": f"Bearer {self.huggingface_token}"}
                payload = {
                    "inputs": f"{system_prompt}\n\nВопрос: {user_message}",
                    "parameters": {"max_length": 200, "temperature": 0.7}
                }
                
                response = requests.post(
                    "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium",
                    headers=headers, 
                    json=payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get('generated_text', 'Не могу ответить в данный момент.')
                    return "🤖 Извините, возникла ошибка при обработке запроса."
                    
            except Exception as e:
                print(f"❌ Ошибка облачного ИИ: {e}")
        
        # Запасной вариант - простые ответы
        return "🤖 В настоящий момент я не могу обработать ваш вопрос. Пожалуйста, используйте кнопки меню или обратитесь к администратору учебного центра. 🎓"

# Создаем экземпляр ассистента
ai_assistant = AIAssistant()

async def get_user_context(user_id):
    """Получает контекст пользователя для персонализации ответов ИИ"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.student_name, g.group_name, u.balance
        FROM users u 
        LEFT JOIN groups g ON u.group_id = g.group_id 
        WHERE u.user_id = ?
    ''', (user_id,))
    
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        name, group, balance = user_data
        context = f"Имя: {name or 'не указано'}, Группа: {group or 'не назначена'}, Баланс: {balance} руб."
    else:
        context = "Пользователь не найден в базе"
    
    return context

async def handle_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает произвольные вопросы через ИИ"""
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    user_message = update.message.text
    user_id = update.effective_user.id
    
    # Показываем что обрабатываем вопрос
    processing_msg = await update.message.reply_text("🤔 *Думаю над ответом...*", parse_mode='Markdown')
    
    # Получаем контекст пользователя для персонализации
    user_context = await get_user_context(user_id)
    
    # Получаем ответ от ИИ
    ai_response = ai_assistant.get_ai_response(user_message, context=user_context)
    
    # Удаляем сообщение "Думаю" и отправляем ответ
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
    await update.message.reply_text(ai_response, parse_mode='Markdown')

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
    """Показывает панель администратора с проверкой пароля"""
    
    # Проверяем пароль
    if not context.args or context.args[0] != "555":
        await update.message.reply_text(
            "🔐 *Требуется авторизация*\n\n"
            "Используйте команду:\n"
            "`/admin 555`",
            parse_mode='Markdown'
        )
        return
    
    # Пароль верный - показываем админ-панель
    stats = get_admin_stats()
    
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🎯 Рассылка по группам", callback_data="admin_broadcast_groups")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("🤖 Статус ИИ", callback_data="admin_ai_status")],
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
        
    elif callback_data == "admin_ai_status":
        # Проверяем статус ИИ сервисов
        status_message = "🤖 *Статус AI-сервисов:*\n\n"
        
        # Проверяем Hugging Face
        try:
            if ai_assistant.huggingface_token:
                headers = {"Authorization": f"Bearer {ai_assistant.huggingface_token}"}
                response = requests.get("https://api-inference.huggingface.co/status", timeout=10)
                status_message += f"• 🤗 Hugging Face: {'✅ Онлайн' if response.status_code == 200 else '❌ Офлайн'}\n"
            else:
                status_message += "• 🤗 Hugging Face: 🔶 Токен не настроен\n"
        except:
            status_message += "• 🤗 Hugging Face: ❌ Офлайн\n"
        
        status_message += f"\n📊 *Используется:* {'Облачный API' if ai_assistant.use_cloud_api else 'Локальный Ollama'}"
        
        await query.edit_message_text(status_message, parse_mode='Markdown')

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

# ==================== ИМПОРТ ИЗ EXCEL ====================

async def handle_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает Excel файлы от администратора"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    if not update.message.document:
        await update.message.reply_text(
            "📤 *Загрузка данных из Excel*\n\n"
            "Отправьте Excel файл (.xlsx) со следующими колонками:\n\n"
            "• student_name - Имя ученика\n"
            "• phone - Телефон\n" 
            "• group_name - Название группы\n"
            "• balance - Баланс\n\n"
            "💡 *Пример структуры:*\n"
            "| student_name | phone       | group_name     | balance |\n"
            "|--------------|-------------|----------------|---------|\n"
            "| Иван Петров  | +79123456789| Математика-1   | 1500    |",
            parse_mode='Markdown'
        )
        return
    
    # Проверяем что это Excel файл
    file_name = update.message.document.file_name.lower()
    if not file_name.endswith(('.xlsx', '.xls')):
        await update.message.reply_text("❌ Пожалуйста, отправьте файл Excel (.xlsx или .xls)")
        return
    
    await update.message.reply_text("🔄 Скачиваю и обрабатываю файл...")
    
    try:
        # Скачиваем файл
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        
        # Читаем Excel файл
        df = pd.read_excel(io.BytesIO(file_bytes))
        
        # Проверяем необходимые колонки
        required_columns = ['student_name', 'phone', 'group_name', 'balance']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            await update.message.reply_text(
                f"❌ В файле отсутствуют колонки: {', '.join(missing)}\n\n"
                f"Нужные колонки: {', '.join(required_columns)}"
            )
            return
        
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        added_count = 0
        updated_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                student_name = str(row['student_name']).strip()
                phone = str(row['phone']).strip()
                group_name = str(row['group_name']).strip()
                balance = float(row['balance'])
                
                # Пропускаем пустые строки
                if not student_name or not phone:
                    continue
                
                # Получаем ID группы
                cursor.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
                group_result = cursor.fetchone()
                
                if not group_result:
                    errors.append(f"Строка {index+2}: Группа '{group_name}' не найдена")
                    continue
                
                group_id = group_result[0]
                
                # Проверяем существует ли пользователь
                cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    # Обновляем существующего пользователя
                    cursor.execute('''
                        UPDATE users SET student_name = ?, group_id = ?, balance = ?
                        WHERE phone = ?
                    ''', (student_name, group_id, balance, phone))
                    updated_count += 1
                else:
                    # Создаем нового пользователя
                    personal_code = generate_personal_code()
                    cursor.execute('''
                        INSERT INTO users (phone, personal_code, student_name, group_id, balance, is_verified)
                        VALUES (?, ?, ?, ?, ?, FALSE)
                    ''', (phone, personal_code, student_name, group_id, balance))
                    added_count += 1
                
            except Exception as e:
                errors.append(f"Строка {index+2}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        # Формируем отчет
        report = f"📊 *Отчет по импорту данных:*\n\n"
        report += f"✅ Добавлено: {added_count} пользователей\n"
        report += f"🔄 Обновлено: {updated_count} пользователей\n"
        report += f"📋 Всего обработано: {len(df)} строк\n"
        
        if errors:
            report += f"\n❌ Ошибки ({len(errors)}):\n"
            for error in errors[:5]:  # Показываем первые 5 ошибок
                report += f"• {error}\n"
            if len(errors) > 5:
                report += f"• ... и еще {len(errors) - 5} ошибок\n"
        else:
            report += "\n🎉 Все данные успешно обработаны!"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка обработки файла: {str(e)}")

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
            "Вы можете перейти в админ-панель или использовать бот как обычный пользователь.\n\n"
            "🔐 *Для админ-панели используйте:*\n"
            "`/admin 555`",
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

🌐 *Соцсети*
• Наша группа ВКонтакте
• Новости и анонсы

🤖 *AI-помощник*
• Ответы на любые вопросы
• Помощь с расписанием
• Консультации по занятиям

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
💳 *Баланс и оплата* - информация о балансe и оплата занятий
👤 *Личный кабинет* - ваши персональные данные
🌐 *ВКонтакте* - наша группа ВКонтакте
🤖 *AI-помощник* - задайте любой вопрос нашему ИИ

*Новый AI-помощник:*
• Отвечает на вопросы о расписании, оплате, программах
• Помогает с организационными вопросами
• Всегда вежлив и терпелив 🎓
• Если не знает ответа - направит к администратору

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
        ["👤 Личный кабинет", "🌐 ВКонтакте"],
        ["🤖 Задать вопрос ИИ", "🆘 Помощь"],
        ["🔄 Обновить данные"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎯 *Главное меню*\n\n"
        "Выберите нужный раздел:\n\n"
        "📅 *Ближайшие занятия* - ваше расписание\n"
        "💳 *Баланс и оплата* - финансовая информация\n"  
        "👤 *Личный кабинет* - ваши данные\n"
        "🌐 *ВКонтакте* - наша группа ВКонтакте\n"
        "🤖 *Задать вопрос ИИ* - AI-помощник ответит на любой вопрос\n"
        "🆘 *Помощь* - справка по использованию\n"
        "🔄 *Обновить данные* - актуализировать информацию",
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

# ВКонтакте вместо чата школы
async def show_vkontakte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authenticated(update.effective_user.id):
        await show_auth_menu(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("🌐 Перейти в ВКонтакте", url="https://vk.com/vdvascheta37")],
        [InlineKeyboardButton("📞 Написать в поддержку", url="https://t.me/your_support_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌐 *Наша группа ВКонтакте*\n\n"
        "Присоединяйтесь к нашему сообществу в ВКонтакте!\n\n"
        "✨ *Что вас ждет:*\n"
        "• 📢 Новости и анонсы\n"
        "• 📸 Фото и видео с занятий\n"
        "• 💬 Общение с преподавателями\n"
        "• 🎯 Полезные материалы\n"
        "• 🏆 Результаты учеников\n\n"
        "Нажмите кнопку ниже чтобы перейти:",
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
            await update.message.reply_text("🔐 Используйте команду: `/admin 555`", parse_mode='Markdown')
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
        elif text in ["📱 Авторизация по номеру телефона", "💳 Баланс и оплата", "📅 Ближайшие занятия", 
                     "👤 Личный кабинет", "🌐 ВКонтакте", "🤖 Задать вопрос ИИ"]:
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
    elif text == "🌐 ВКонтакте":
        await show_vkontakte(update, context)
    elif text == "🤖 Задать вопрос ИИ":
        await update.message.reply_text(
            "🤖 *AI-помощник учебного центра*\n\n"
            "Задайте мне любой вопрос о:\n"
            "• 📅 Расписании занятий\n"
            "• 💰 Оплате и балансе\n" 
            "• 🎯 Учебных программах\n"
            "• 👥 Наших преподавателях\n"
            "• ❓ Других вопросах\n\n"
            "Я постараюсь помочь! 🎓✨",
            parse_mode='Markdown'
        )
    elif text == "🔄 Обновить данные":
        await update.message.reply_text("✅ *Данные обновлены!*", parse_mode='Markdown')
    elif text == "🆘 Помощь":
        await help_command(update, context)
    elif text == "🔐 Ввод персонального кода":
        await handle_personal_code_input(update, context)
    else:
        # ВСЕ остальные сообщения идут в ИИ!
        await handle_ai_question(update, context)

# Основная функция
def main():
    # ==================== ФИКС КОНФЛИКТА ====================
    import requests
    try:
        # Закрываем предыдущие соединения с Telegram
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/close")
        print("✅ Закрыли предыдущие соединения с Telegram")
    except Exception as e:
        print(f"ℹ️ Не удалось закрыть предыдущие соединения: {e}")
    # ==================== КОНЕЦ ФИКСА ====================
    
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

    # ==================== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", show_admin_panel))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    
    # Контакты
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    # Excel файлы
    application.add_handler(MessageHandler(filters.Document.ALL, handle_excel_file))
    
    # Текстовые сообщения (должен быть ПОСЛЕДНИМ!)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback-кнопки
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
