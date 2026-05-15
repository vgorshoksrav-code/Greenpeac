# handlers/payment_handler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from config import ADMIN_ID, SEND_BOT_USERNAME
from database import get_user, get_balance, set_state
from keyboards import main_menu, payment_type_kb, confirm_card

ASK_AMOUNT, ASK_TYPE = range(10, 12)

STATES = {
    ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_amount)],
    ASK_TYPE:   [
        CallbackQueryHandler(pay_crypto, pattern="^pay_crypto$"),
        CallbackQueryHandler(pay_card,   pattern="^pay_card$"),
    ],
}


async def top_up_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if not user or user["status"] != "approved":
        await query.answer("Нет доступа.", show_alert=True)
        return ConversationHandler.END
    await query.edit_message_text(
        f"💰 Ваш текущий баланс: <b>{get_balance(query.from_user.id):.2f} EUR</b>\n\n"
        "Введите сумму пополнения (EUR):",
        parse_mode="HTML"
    )
    return ASK_AMOUNT


async def got_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму (число больше 0).")
        return ASK_AMOUNT

    ctx.user_data["topup_amount"] = amount
    await update.message.reply_text(
        f"💵 Сумма: <b>{amount:.2f} EUR</b>\n\nВыберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_type_kb()
    )
    return ASK_TYPE


async def pay_crypto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    amount = ctx.user_data.get("topup_amount", 0)
    user   = get_user(query.from_user.id)
    sid    = user["short_id"] if user else "NOREF"

    # Direct link to @send bot with comment containing short_id for identification
    send_url = f"https://t.me/{SEND_BOT_USERNAME}?start=send_{amount}_{sid}"
    await query.edit_message_text(
        f"💎 <b>Оплата криптовалютой</b>\n\n"
        f"Сумма: <b>{amount:.2f} EUR</b>\n\n"
        f"Перейдите в бот @{SEND_BOT_USERNAME} и отправьте платёж.\n"
        f"В комментарии к переводу обязательно укажите ваш ID: <code>{sid}</code>\n\n"
        f"🔗 <a href='{send_url}'>Открыть @{SEND_BOT_USERNAME}</a>",
        parse_mode="HTML",
        reply_markup=main_menu(query.from_user.id)
    )
    return ConversationHandler.END


async def pay_card(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    amount = ctx.user_data.get("topup_amount", 0)
    tg_id  = query.from_user.id
    user   = get_user(tg_id)
    sid    = user["short_id"] if user else "?"

    # Store pending card payment for admin
    set_state(f"card_amount_{tg_id}", str(amount))
    set_state(f"card_pending_{tg_id}", str(amount))

    # Notify admin
    await ctx.bot.send_message(
        chat_id    = ADMIN_ID,
        text       = (
            f"💳 Оплата картой (UA)\n\n"
            f"👤 {user['full_name']} | ID бота: <code>{sid}</code>\n"
            f"📱 TG ID: <code>{tg_id}</code>\n"
            f"💵 Сумма: <b>{amount:.2f} EUR</b>\n\n"
            "Отправьте пользователю карту командой:\n"
            f"<code>/add {sid} НОМЕР_КАРТЫ</code>"
        ),
        parse_mode = "HTML",
        reply_markup = confirm_card(tg_id)
    )

    await query.edit_message_text(
        f"💳 Ожидайте реквизиты карты.\n"
        f"Сумма к оплате: <b>{amount:.2f} EUR</b>\n\n"
        "Администратор скоро пришлёт вам карту для оплаты.",
        parse_mode="HTML",
        reply_markup=main_menu(tg_id)
    )
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu(update.effective_user.id))
    return ConversationHandler.END


# fix forward refs
STATES = {
    ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_amount)],
    ASK_TYPE:   [
        CallbackQueryHandler(pay_crypto, pattern="^pay_crypto$"),
        CallbackQueryHandler(pay_card,   pattern="^pay_card$"),
    ],
}
