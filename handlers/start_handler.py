# handlers/start_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, init_db
from keyboards import main_menu

init_db()


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from handlers.registration_handler import ask_source
    tg_id = update.effective_user.id
    user  = get_user(tg_id)

    if user is None:
        # Brand-new user – begin registration
        return await ask_source(update, ctx)

    if user["status"] == "blocked":
        await update.message.reply_text("🚫 Вы заблокированы в этом боте.")
        return

    if user["status"] == "pending":
        await update.message.reply_text(
            "⏳ Ваша заявка на рассмотрении. Ожидайте решения администратора."
        )
        return

    # Already approved
    await update.message.reply_text(
        f"👋 С возвращением, {update.effective_user.first_name}!\n"
        "Выберите действие:",
        reply_markup=main_menu(tg_id)
    )
