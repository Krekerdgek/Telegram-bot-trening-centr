# -*- coding: utf-8 -*-
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ID администраторов (замените на реальные ID владельцев)
ADMIN_IDS = [123456789, 987654321]  # Пример ID

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

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
        [InlineKeyboardButton("🔧 Настройки", callback_data="admin_settings")]
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
            f"• Средний баланс: {stats['total_balance']/stats['active_users']:.0f} руб."
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
        
    elif callback_data == "admin_users":
        await show_users_list(query)

async def show_users_list(query):
    """Показывает список пользователей"""
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.student_name, u.phone, g.group_name, u.balance 
        FROM users u 
        LEFT JOIN groups g ON u.group_id = g.group_id 
        WHERE u.is_verified = TRUE 
        LIMIT 10
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("❌ Нет активных пользователей")
        return
    
    message = "👥 *Последние 10 пользователей:*\n\n"
    for user in users:
        name, phone, group, balance = user
        message += f"• {name or 'Не указано'} ({phone})\n"
        message += f"  Группа: {group or 'Не назначена'}\n"
        message += f"  Баланс: {balance} руб.\n\n"
    
    await query.edit_message_text(message, parse_mode='Markdown')
