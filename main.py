from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, CommandHandler, JobQueue, CallbackContext
from datetime import datetime, timedelta
import database
import os
from dotenv import load_dotenv

NAME, PHONE, DATE, TIME, CLIENT, EDIT_CLIENT = range(6)


async def client_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, находится ли пользователь в процессе добавления клиента
    if context.user_data.get('editing_client', False):
        # Сбрасываем флаг editing_client и возвращаемся в начальное состояние
        context.user_data['editing_client'] = False
        return NAME
    
    # Получаем записи из базы данных
    clients = database.get_clients(user_id=update.effective_user.id)

    if clients:
        # Отправляем информацию о каждом клиенте с кнопкой "Изменить запись" и "Удалить запись"
        for client in clients:
            phone_number = client['phone']
            
            # Создаем гиперссылку на номер телефона
            phone_link = f"{phone_number}"
            
            client_info = (
                f"Имя: {client['name']}\n"
                f"Телефон: {phone_link}\n"
                f"Дата записи: {client['date']} {client['time']}"
            )
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Удалить запись", callback_data=f"delete_{client['id']}")]
            ])

            # Отправляем информацию о клиенте с клавиатурой
            await context.bot.send_message(chat_id=update.effective_chat.id, text=client_info, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Нет записей')


async def handle_delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обрабатываем нажатие кнопки "Удалить запись"
    query = update.callback_query
    client_id = int(query.data.split('_')[1])

    # Удаляем запись из базы данных
    database.delete_client(client_id=client_id, user_id=update.effective_user.id)

    # Удаляем сообщение с информацией о клиенте и кнопками
    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

async def handle_edit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Устанавливаем флаг editing_client в True при обработке кнопки редактирования
    context.user_data['editing_client'] = True

    # Продолжаем процесс редактирования
    query = update.callback_query
    client_id = int(query.data.split('_')[1])
    context.user_data.clear()
    database.delete_client(client_id)

    # Получаем информацию о клиенте по ID и отправляем сообщение
    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    await add_client(update, context)

async def add_client(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Проверяем, находится ли пользователь в процессе редактирования клиента
    if context.user_data.get('editing_client', False):
        # Сбрасываем флаг editing_client
        context.user_data['editing_client'] = False
        return NAME

    message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Введите имя клиента:")
    context.user_data['client_message_id'] = message.message_id
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['name'] = name

    # Удаляем предыдущее сообщение бота
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['client_message_id'])

    # Отправляем новое сообщение с инструкцией
    message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Введите номер телефона клиента:")
    context.user_data['client_message_id'] = message.message_id

    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data['phone'] = phone
    # Вызываем функцию для отправки клавиатуры с датой
    await get_date_inline_keyboard(update, context)
    return DATE

async def get_date_inline_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Получаем текущую дату
    current_date = datetime.now()

    # Получаем следующие 6 дней
    dates = [current_date + timedelta(days=i) for i in range(6)]

    # Форматируем дни и месяцы в строки
    formatted_dates = [date.strftime('%d.%m') for date in dates]

    # Проверяем доступность времени на выбранные даты
    available_dates = []
    for date in formatted_dates:
        occupied_hours = get_occupied_hours(date, user_id=update.effective_user.id)
        if current_date.hour >= 22 or (current_date.date() == datetime.strptime(date, '%d.%m').date() and current_date.hour >= 22) or len(occupied_hours) < 7:
            available_dates.append(date)

    # Если нет доступных дат, сообщаем об этом и завершаем процесс
    if not available_dates:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, все временные слоты на следующие 6 дней уже заняты.")
        return None

    # Создаем кнопки только для доступных дат
    keyboard = [
        [InlineKeyboardButton(date, callback_data=f'date_{date}') for date in available_dates]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение с новой инструкцией и клавиатурой
    await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=context.user_data['client_message_id'],
                                         text='Выберите дату:', reply_markup=reply_markup)
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_date = update.callback_query.data.split('_')[1]
    context.user_data['date'] = selected_date

    # Обновляем сообщение с новой инструкцией
    await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=context.user_data['client_message_id'],
                                         text="Теперь выберите время:")

    # Вызываем функцию для отправки клавиатуры с временем
    await get_time_inline_keyboard(update, context)
    return TIME


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_time = update.callback_query.data.split('_')[1]
    context.user_data['time'] = selected_time

    # Получаем дату и время записи
    appointment_datetime_str = f"{context.user_data['date']} {selected_time}"
    appointment_datetime = datetime.strptime(appointment_datetime_str, '%d.%m %H:%M')

    # Устанавливаем задачу на напоминание за час до записи
    job_context = {'chat_id': update.effective_chat.id, 'client_info': get_client_info(context.user_data)}
    context.job_queue.run_once(send_reminder, appointment_datetime - timedelta(minutes=30), context=job_context)

    # Вызываем функцию для отправки информации о клиенте
    await get_client(update, context)
    return CLIENT

def get_client_info(user_data):
    return f"Имя: {user_data.get('name', 'Не указано')}\nТелефон: {user_data.get('phone', 'Не указан')}\nДата записи: {user_data.get('date', 'Не указана')} {user_data.get('time', 'Не указано')}"

async def send_reminder(context: CallbackContext):
    chat_id = context.job.context['chat_id']
    client_info = context.job.context['client_info']
    reminder_message = f"Напоминание о клиенте через час:\n{client_info}"
    
    await context.bot.send_message(chat_id=chat_id, text=reminder_message)

def is_future_time(selected_date, selected_time, current_datetime):
    # Преобразуем выбранную дату и время в объект datetime
    selected_datetime = datetime.strptime(f'{selected_date} {selected_time}', '%d.%m %H:%M')

    # Преобразуем текущую дату и время в строку с форматом "%d.%m %H:%M"
    current_datetime_str = current_datetime.strftime('%d.%m %H:%M')

    # Проверяем, является ли выбранная дата и время будущими
    return selected_datetime > datetime.strptime(current_datetime_str, '%d.%m %H:%M')

async def get_time_inline_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Получаем текущую дату и время
    current_datetime = datetime.now()
    print(f'Current Datetime: {current_datetime}')

    # Получаем выбранную пользователем дату
    selected_date = context.user_data.get('date')
    print(f'Selected Date: {selected_date}')

    # Если дата выбрана, проверяем доступные часы на этот день
    if selected_date:
        # Получаем занятые часы для выбранной даты из базы данных
        occupied_hours = get_occupied_hours(selected_date,user_id=update.effective_user.id)
        print(f'Occupied Hours: {occupied_hours}')

        # Фильтруем доступные часы
        times = [time for time in ['10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'] if time not in occupied_hours and is_future_time(selected_date, time, current_datetime)]
        print(f'Available Times: {times}')
    else:
        # Если дата не выбрана, используем все доступные часы
        times = ['10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']

    # Создаем кнопки с временем
    time_buttons = [InlineKeyboardButton(time, callback_data=f'time_{time}') for time in times]

    reply_markup = InlineKeyboardMarkup([time_buttons])

    # Обновляем сообщение с новой инструкцией и клавиатурой
    await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=context.user_data['client_message_id'],
                                         text='Выберите время:', reply_markup=reply_markup)
    return TIME


def get_occupied_hours(selected_date, user_id):
    # Здесь вам нужно получить из базы данных список часов, которые уже заняты для выбранной даты
    # Например, используя функцию get_clients_from_database()
    occupied_hours = []

    # Получаем записи из базы данных
    clients = database.get_clients(user_id)

    # Форматируем дату в строку для сравнения
    selected_date_str = datetime.strptime(selected_date, '%d.%m').strftime('%d.%m')

    # Получаем список занятых часов для выбранной даты
    for client in clients:
        client_date = client['date']
        client_time = client['time']

        if client_date == selected_date_str and client_time not in occupied_hours:
            occupied_hours.append(client_time)

    return occupied_hours

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_time = update.callback_query.data.split('_')[1]
    context.user_data['time'] = selected_time

    # Вызываем функцию для отправки информации о клиенте
    await context.bot.delete_message(chat_id=update.effective_chat.id,message_id=context.user_data['client_message_id'])
    await get_client(update, context)
    return CLIENT

async def get_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_number = context.user_data.get('phone', 'Не указан')
    
    # Создаем гиперссылку на номер телефона
    phone_link = f"{phone_number}"
    
    client_info = (
        f"Клиент успешно добавлен!\n"
        f"Имя: {context.user_data.get('name', 'Не указано')}\n"
        f"Телефон: {phone_link}\n"
        f"Дата записи: {context.user_data.get('date', 'Не указана')} {context.user_data.get('time', 'Не указано')}"
    )
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=client_info)

    database.add_client(data=context.user_data, user_id=update.effective_user.id)
    # Очищаем данные пользователя
    context.user_data.clear()

    # Возвращаем состояние NAME для возможности добавления нового клиента
    return NAME

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    db_path = f'databases/{user_id}_clients.db'
    db_folder = 'databases'

    if not os.path.exists(db_folder):
        os.makedirs(db_folder)


    if not os.path.exists(db_path):
        database.create_user_table(user_id)


    keyboard = [
        [KeyboardButton("Добавить клиента"), KeyboardButton("Мои записи")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    context.user_data['editing_client'] = False

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Привет! Я бот для записи твоих клиенток на реснички! \n\nТвой уникальный номер: {update.effective_user.id}", reply_markup=reply_markup)

def main():

    load_dotenv()
    token = os.environ.get('LASH_TOKEN')
    application = ApplicationBuilder().token(token).build()

    # Обработчик команды /start
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # Обработчик команды "Мои записи"
    clients_handler = MessageHandler(filters.Regex('^Мои записи$'), client_view)
    application.add_handler(clients_handler)
    
    # Изменение записи клиента
    edit_handler = CallbackQueryHandler(handle_edit_button, pattern=r'^edit_\d+$')
    application.add_handler(edit_handler)

    # Удаление записи клиента
    delete_handler = CallbackQueryHandler(handle_delete_button, pattern=r'^delete_\d+$')
    application.add_handler(delete_handler)

    # Обработчики команд и входов в диалог
    conv_handler = ConversationHandler(
        per_message=False,
        entry_points=[MessageHandler(filters.Regex('^Добавить клиента$'), add_client)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DATE: [CallbackQueryHandler(get_date, pattern=r'^date_\d{2}\.\d{2}$')],
            TIME: [CallbackQueryHandler(get_time, pattern=r'^time_\d{2}:\d{2}$')],
            CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_client)],
        },
        fallbacks=[]
    )

    # Добавляем обработчики в приложение
    application.add_handler(conv_handler)

    # Запускаем приложение
    application.run_polling()

if __name__ == '__main__':
    main()