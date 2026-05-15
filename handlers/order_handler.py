# handlers/order_handler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from config import ADMIN_ID
from database import get_user, get_balance, get_surcharge, create_order
from keyboards import main_menu, approve_reject_order

ASK_WHAT = 20

STATES = {
    ASK_WHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_what)],
}


async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if not user or user["status"] != "approved":
        await query.answer("Нет доступа.", show_alert=True)
        return ConversationHandler.END

    balance = get_balance(query.from_user.id)
    await query.edit_message_text(
        f"💰 Ваш баланс: <b>{balance:.2f} EUR</b>\n\n"
        "🛒 Что будете заказывать? Опишите заказ:",
        parse_mode="HTML"
    )
    return ASK_WHAT


async def got_what(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id       = update.effective_user.id
    description = update.message.text
    surcharge   = get_surcharge(tg_id)
    balance     = get_balance(tg_id)
    user        = get_user(tg_id)

    # We don't know exact price yet – admin will decide; store order with 0 now
    # The actual amount will be set when admin approves (simplified: surcharge only shown)
    total = surcharge  # placeholder – in full implementation admin would specify price

    order_id = create_order(tg_id, description, total)

    await update.message.reply_text(
        f"✅ Заявка #{order_id} отправлена!\n"
        f"📋 Заказ: {description}\n"
        f"💸 Наценка сервиса: {surcharge:.2f} EUR\n\n"
        "Ожидайте решения администратора.",
        reply_markup=main_menu(tg_id)
    )

    sid = user["short_id"] if user else "?"
    await update.context.bot.send_message(
        chat_id    = ADMIN_ID,
        text       = (
            f"🛒 <b>Новый заказ #{order_id}</b>\n\n"
            f"👤 {update.effective_user.full_name} | ID: <code>{sid}</code>\n"
            f"📱 TG: <code>{tg_id}</code>\n"
            f"💰 Баланс: {balance:.2f} EUR\n"
            f"📋 Описание: {description}\n"
            f"💸 Наценка: {surcharge:.2f} EUR"
        ),
        parse_mode = "HTML",
        reply_markup = approve_reject_order(order_id)
    )
    return ConversationHandler.END


# Need to access bot inside got_what via update.get_bot()
# Patching: use ctx.bot instead
async def got_what(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id       = update.effective_user.id
    description = update.message.text
    surcharge   = get_surcharge(tg_id)
    balance     = get_balance(tg_id)
    user        = get_user(tg_id)
    sid         = user["short_id"] if user else "?"

    order_id = create_order(tg_id, description, surcharge)

    await update.message.reply_text(
        f"✅ Заявка <b>#{order_id}</b> отправлена!\n"
        f"📋 Заказ: {description}\n"
        f"💸 Наценка сервиса: {surcharge:.2f} EUR\n\n"
        "Ожидайте решения администратора.",
        parse_mode="HTML",
        reply_markup=main_menu(tg_id)
    )

    await ctx.bot.send_message(
        chat_id    = ADMIN_ID,
        text       = (
            f"🛒 <b>Новый заказ #{order_id}</b>\n\n"
            f"👤 {update.effective_user.full_name} | ID: <code>{sid}</code>\n"
            f"📱 TG: <code>{tg_id}</code>\n"
            f"💰 Баланс пользователя: {balance:.2f} EUR\n"
            f"📋 Описание: {description}\n"
            f"💸 Наценка: {surcharge:.2f} EUR"
        ),
        parse_mode = "HTML",
        reply_markup = approve_reject_order(order_id)
    )
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu(update.effective_user.id))
    return ConversationHandler.END


STATES = {
    ASK_WHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_what)],
}
