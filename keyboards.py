# keyboards.py  ── all InlineKeyboardMarkup builders in one place
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_ID


def main_menu(tg_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("💳 Пополнить", callback_data="topup"),
         InlineKeyboardButton("🛒 Заказать",  callback_data="order")],
        [InlineKeyboardButton("👤 Профиль",   callback_data="profile"),
         InlineKeyboardButton("📊 Статистика",callback_data="stats")],
        [InlineKeyboardButton("🎟 Промокод",  callback_data="use_promo"),
         InlineKeyboardButton("🆘 Поддержка", callback_data="support")],
    ]
    if tg_id == ADMIN_ID:
        rows.append([InlineKeyboardButton("🔧 Админ меню", callback_data="admin_menu")])
    return InlineKeyboardMarkup(rows)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика",        callback_data="admin_menu")],
        [InlineKeyboardButton("🚫 Заблокированные",   callback_data="admin_blocked")],
        [InlineKeyboardButton("📢 Рассылка",          callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎟 Промокоды",         callback_data="admin_promo")],
    ])


def approve_reject_reg(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Принять",   callback_data=f"approve_reg_{tg_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_reg_{tg_id}"),
    ]])


def approve_reject_order(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Принять",   callback_data=f"approve_ord_{order_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_ord_{order_id}"),
    ]])


def confirm_card(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_card_{tg_id}"),
    ]])


def payment_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💎 Криптовалюта", callback_data="pay_crypto"),
        InlineKeyboardButton("💳 Карта (UA)",   callback_data="pay_card"),
    ]])
