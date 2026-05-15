# handlers/registration_handler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from config import ADMIN_ID
from database import create_user, get_user
from keyboards import approve_reject_reg

ASK_SOURCE, ASK_BUY = range(2)

STATES = {
    ASK_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_source)],
    ASK_BUY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_buy)],
}


async def ask_source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user  = get_user(tg_id)
    if user and user["status"] == "blocked":
        await update.message.reply_text("🚫 Вы заблокированы.")
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Добро пожаловать в Greenpeace Club!\n\n"
        "Прежде чем продолжить, ответьте на пару вопросов.\n\n"
        "❓ Откуда вы узнали о нас?"
    )
    return ASK_SOURCE


async def got_source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["source"] = update.message.text
    await update.message.reply_text("🛍 Что планируете покупать?")
    return ASK_BUY


async def got_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    source = ctx.user_data.get("source", "—")
    buy    = update.message.text

    # Save to DB
    sid = create_user(
        tg_id      = user.id,
        username   = user.username or "",
        full_name  = user.full_name,
        source     = source,
        want_to_buy= buy,
    )

    await update.message.reply_text(
        "✅ Ваша заявка отправлена на рассмотрение администратору. "
        "Ожидайте ответа!"
    )

    # Notify admin
    text = (
        "🆕 Новая заявка на вступление!\n\n"
        f"👤 Имя: {user.full_name}\n"
        f"🔖 ID в боте: <code>{sid}</code>\n"
        f"📱 Telegram ID: <code>{user.id}</code>\n"
        f"🔗 Username: @{user.username or '—'}\n\n"
        f"📍 Откуда узнал: {source}\n"
        f"🛍 Что хочет купить: {buy}"
    )
    await ctx.bot.send_message(
        chat_id    = ADMIN_ID,
        text       = text,
        parse_mode = "HTML",
        reply_markup = approve_reject_reg(user.id)
    )
    return ConversationHandler.END


# forward-reference fix: define STATES after functions
STATES = {
    ASK_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_source)],
    ASK_BUY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_buy)],
}
