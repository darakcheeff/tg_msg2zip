import os
import shutil
import zipfile
import telegram
import telegram.ext
from telegram import Update
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import CallbackContext
from telegram import Update, Message, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext.filters import MessageFilter


def start(update: Update, context):
    """Handler для команды /start"""
    update.message.reply_text(
        "Привет! Я бот, который может скачивать картинки из сообщений и сохранять их в архиве. "
        "Просто перешли мне сообщение с картинкой и я сделаю все остальное."
    )


class HasImageFilter(MessageFilter):
    """Filter для сообщений с картинкой"""
    def filter(self, message):
        return bool(message.photo) or bool(message.document and message.document.mime_type.startswith("image/"))


def save_file(update: Update, context):
    """Handler для сохранения файла"""
    # Получаем информацию о файле
    file = None
    if update.message.photo:
        file = update.message.photo[-1]
    elif update.message.document:
        file = update.message.document
    else:
        update.message.reply_text("Сообщение не содержит файлов.")
        return

    # Создаем папку с ID пользователя в папке tmp
    if isinstance(update.message, Message):
        user_dir = f"tmp/{update.message.from_user.id}"
        os.makedirs(user_dir, exist_ok=True)

    # Скачиваем файл в папку пользователя
    file.get_file().download(custom_path=f"{user_dir}/{file.file_unique_id}.jpg")

    # Отправляем сообщение пользователю
    update.message.reply_text(f"Файл {file.file_name} сохранен.")

    # Если есть другие файлы в сообщении, сохраняем их тоже
    if update.message.photo:
        for i, photo in enumerate(update.message.photo[:-1]):
            photo.get_file().download(custom_path=f"{user_dir}/{i}.jpg")
    elif update.message.document:
        for i, page in enumerate(update.message.document.pages):
            page.get_file().download(custom_path=f"{user_dir}/{i}.jpg")


def create_archive(update: Update, context):
    """Handler для создания архива"""
    # Получаем путь к папке пользователя
    user_dir = f"tmp/{update.message.from_user.id}"

    # Проверяем, что папка существует
    if not os.path.isdir(user_dir):
        update.message.reply_text("У вас нет сохраненных файлов.")
        return

    # Создаем архив
    zip_name = f"{update.message.from_user.id}.zip"
    with zipfile.ZipFile(zip_name, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for file in os.listdir(user_dir):
            zip_file.write(f"{user_dir}/{file}", file)

    # Отправляем архив пользователю
    with open(zip_name, "rb") as file:
        context.bot.send_document(chat_id=update.message.chat_id, document=file)
    file.close()

    # Удаляем временную директорию со всем содержимым
    shutil.rmtree(user_dir)

    # Удаляем файл архива
    os.remove(zip_name)

    print(f"Архив {zip_name} отправлен, а временные файлы удалены.")
    def delete_empty_dirs():
    """Deletes empty directories in the tmp directory"""
    for user_dir in os.scandir("tmp"):
        if user_dir.is_dir() and not any(user_dir.iterdir()):
            shutil.rmtree(user_dir)
            print(f"Empty directory {user_dir} removed.")


def error_handler(update: Update, context: CallbackContext):
    """Log errors caused by updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

    
def main():
    # read the token from the token.txt file
    with open("token.txt") as f:
        token = f.read().strip()

    # create the bot and dispatcher
    bot = telegram.Bot(token=token)
    updater = telegram.ext.Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    # add the message handler to the dispatcher
    dispatcher.add_handler(MessageHandler(Filters.document | Filters.photo, save_file))

    # add the command handlers to the dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("create_archive", create_archive))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # add error handler to the dispatcher
    dispatcher.add_error_handler(error_handler)

    # start the bot
    updater.start_polling()

    # run the scheduler to check for empty directories to delete
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_empty_dirs, "interval", minutes=30)
    scheduler.start()

    # idle the bot to keep it running
    updater.idle()

def help_command(update: Update, context: CallbackContext) -> None:
    """Отправить сообщение с описанием доступных команд"""
    update.message.reply_text(
        "Список доступных команд:\n"
        "/start - Начать диалог\n"
        "/help - Вывести справку"
    )


if __name__ == "__main__":
    main()

