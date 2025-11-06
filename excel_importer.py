# -*- coding: utf-8 -*-
import pandas as pd
import sqlite3
import io
from telegram import Update
from telegram.ext import ContextTypes

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
    
    file = await update.message.document.get_file()
    file_bytes = await file.download_as_bytearray()
    
    await update.message.reply_text("🔄 Обрабатываю файл...")
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(io.BytesIO(file_bytes))
        
        # Проверяем необходимые колонки
        required_columns = ['student_name', 'phone', 'group_name', 'balance']
        if not all(col in df.columns for col in required_columns):
            await update.message.reply_text(
                f"❌ В файле отсутствуют необходимые колонки. Нужны: {required_columns}"
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
                
                # Получаем ID группы
                cursor.execute("SELECT group_id FROM groups WHERE group_name = ?", (group_name,))
                group_result = cursor.fetchone()
                
                if not group_result:
                    errors.append(f"❌ Группа '{group_name}' не найдена для {student_name}")
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
                errors.append(f"❌ Ошибка в строке {index+2}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        # Формируем отчет
        report = f"📊 *Отчет по импорту данных:*\n\n"
        report += f"✅ Добавлено: {added_count} пользователей\n"
        report += f"🔄 Обновлено: {updated_count} пользователей\n"
        
        if errors:
            report += f"\n❌ Ошибки ({len(errors)}):\n"
            for error in errors[:5]:  # Показываем первые 5 ошибок
                report += f"• {error}\n"
            if len(errors) > 5:
                report += f"• ... и еще {len(errors) - 5} ошибок\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка обработки файла: {str(e)}")

def generate_personal_code():
    """Генерация персонального кода"""
    import secrets
    import string
    return ''.join(secrets.choice(string.digits) for _ in range(6))
