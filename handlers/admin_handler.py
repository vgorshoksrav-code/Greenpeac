# handlers/admin_handler.py
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID, DEFAULT_SURCHARGE
from database import (
    get_user, update_user_status, increment_reject,
    update_balance, get_balance, set_surcharge,
    get_user_by_short_id, stats, blocked_users,
    all_approved_users, get_order, update_order_status,
    create_promo, list_promos, set_state, get_state, del_state
)
from keyboards import main_menu, admin_menu_kb, approve_reject_order, confirm_card

# ─── Admin guard ───────────────────────────────────────────────────────────────

def is_admin(tg_id: int) -> bool:
    return tg_id == ADMIN_ID


# ─── Approve / Reject registration ────────────────────────────────────────────

async def handle_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    tg_id = int(query.data.split("_")[-1])
    update_user_status(tg_id, "approved")

    await query.edit_message_text(query.message.text + "\n\n✅ Принят.")
    await ctx.bot.send_message(
        chat_id    = tg_id,
        text       = (
            "🎉 Поздравляем! Вас приняли в закрытый клуб <b>Greenpeace</b>! 🌿\n\n"
            "Теперь вам доступны все функции бота."
        ),
        parse_mode = "HTML",
        reply_markup = main_menu(tg_id)
    )


async def handle_reject_req(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    tg_id = int(query.data.split("_")[-1])
    # Store waiting-for-reason state
    set_state(f"reject_reg_{ADMIN_ID}", str(tg_id))
    await query.edit_message_text(query.message.text + "\n\n⏳ Введите причину отклонения:")


# ─── Approve / Reject order ────────────────────────────────────────────────────

async def handle_approve_ord(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    order_id = int(query.data.split("_")[-1])
    order    = get_order(order_id)
    if not order:
        await query.answer("Заказ не найден.")
        return

    update_order_status(order_id, "approved")
    # Deduct from balance
    update_balance(order["tg_id"], -order["amount"])

    await query.edit_message_text(query.message.text + "\n\n✅ Заказ принят.")
    await ctx.bot.send_message(
        chat_id = order["tg_id"],
        text    = (
            f"✅ Ваш заказ <b>#{order_id}</b> принят!\n"
            f"💸 Списано: {order['amount']:.2f} EUR\n"
            f"💰 Остаток: {get_balance(order['tg_id']):.2f} EUR"
        ),
        parse_mode = "HTML",
        reply_markup = main_menu(order["tg_id"])
    )


async def handle_reject_ord(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    order_id = int(query.data.split("_")[-1])
    set_state(f"reject_ord_{ADMIN_ID}", str(order_id))
    await query.edit_message_text(query.message.text + "\n\n⏳ Введите причину отклонения заказа:")


# ─── Card payment confirm ──────────────────────────────────────────────────────

async def confirm_card_pay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    tg_id  = int(query.data.split("_")[-1])
    amount = float(get_state(f"card_amount_{tg_id}") or 0)
    update_balance(tg_id, amount)
    del_state(f"card_amount_{tg_id}")

    await query.edit_message_text(query.message.text + "\n\n✅ Оплата подтверждена, баланс пополнен.")
    await ctx.bot.send_message(
        chat_id = tg_id,
        text    = (
            f"✅ Ваш баланс пополнен на <b>{amount:.2f} EUR</b>!\n"
            f"💰 Текущий баланс: {get_balance(tg_id):.2f} EUR"
        ),
        parse_mode = "HTML",
        reply_markup = main_menu(tg_id)
    )


# ─── Admin menu ────────────────────────────────────────────────────────────────

async def admin_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    total, blk, orders = stats()
    text = (
        "🔧 <b>Админ-панель Greenpeace</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"🚫 Заблокированных: <b>{blk}</b>\n"
        f"🛒 Успешных заказов: <b>{orders}</b>"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=admin_menu_kb())


async def admin_blocked(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    users = blocked_users()
    if not users:
        await query.edit_message_text("Заблокированных пользователей нет.", reply_markup=admin_menu_kb())
        return

    lines = [f"• {u['full_name']} | ID: <code>{u['short_id']}</code> | TG: <code>{u['tg_id']}</code>" for u in users]
    await query.edit_message_text(
        "🚫 <b>Заблокированные пользователи:</b>\n\n" + "\n".join(lines),
        parse_mode = "HTML",
        reply_markup = admin_menu_kb()
    )


# ─── Broadcast ────────────────────────────────────────────────────────────────

async def admin_broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    set_state(f"broadcast_{ADMIN_ID}", "waiting")
    await query.edit_message_text("📢 Введите текст рассылки:")


# ─── Promo codes ──────────────────────────────────────────────────────────────

async def admin_promo_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    promos = list_promos()
    lines  = [f"• <code>{p['code']}</code> — {p['amount']} EUR | {p['used']}/{p['activations']} активаций" for p in promos]
    text   = "🎟 <b>Промокоды:</b>\n\n" + ("\n".join(lines) if lines else "Нет промокодов.")
    kb     = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Создать промокод", callback_data="promo_create")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_promo_create(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    set_state(f"promo_create_{ADMIN_ID}", "waiting")
    await query.edit_message_text(
        "🎟 Создание промокода.\n\n"
        "Введите в формате:\n"
        "<code>КОД СУММА АКТИВАЦИИ</code>\n\n"
        "Пример: <code>GREEN10 10 5</code>",
        parse_mode = "HTML"
    )


# ─── /add command: admin sends card to user ───────────────────────────────────

async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    # /add SHORT_ID CARD_NUMBER
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /add <short_id> <номер_карты>")
        return

    short_id = args[0]
    card     = " ".join(args[1:])
    user     = get_user_by_short_id(short_id)
    if not user:
        await update.message.reply_text(f"Пользователь с ID {short_id} не найден.")
        return

    amount = float(get_state(f"card_pending_{user['tg_id']}") or 0)
    if amount:
        update_balance(user["tg_id"], amount)
        del_state(f"card_pending_{user['tg_id']}")

    await ctx.bot.send_message(
        chat_id = user["tg_id"],
        text    = (
            f"💳 Реквизиты для оплаты ({amount:.2f} EUR):\n\n"
            f"<code>{card}</code>\n\n"
            "После оплаты баланс будет пополнен администратором."
        ),
        parse_mode = "HTML"
    )
    await update.message.reply_text(f"✅ Карта отправлена пользователю {short_id}.")


# ─── /set command: set user surcharge ────────────────────────────────────────

async def cmd_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = ctx.args
    if len(args) != 2:
        await update.message.reply_text("Использование: /set <short_id> <наценка>")
        return
    short_id  = args[0]
    try:
        surcharge = float(args[1].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Наценка должна быть числом.")
        return

    user = get_user_by_short_id(short_id)
    if not user:
        await update.message.reply_text(f"Пользователь с ID {short_id} не найден.")
        return

    set_surcharge(user["tg_id"], surcharge)
    await update.message.reply_text(f"✅ Наценка для {user['full_name']} установлена: {surcharge} EUR")


# ─── Generic text router (admin inputs: reject reason, broadcast, promo) ──────

async def router_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    text  = update.message.text

    # ── Admin reject registration reason ──────────────────────────────────────
    if is_admin(tg_id):
        pending_reg = get_state(f"reject_reg_{ADMIN_ID}")
        if pending_reg:
            target_id = int(pending_reg)
            del_state(f"reject_reg_{ADMIN_ID}")

            rejects = increment_reject(target_id)
            if rejects >= 3:
                update_user_status(target_id, "blocked")
                await ctx.bot.send_message(
                    target_id,
                    "🚫 Ваша заявка отклонена 3 раза. Вы заблокированы в боте."
                )
            else:
                await ctx.bot.send_message(
                    target_id,
                    f"❌ Ваша заявка отклонена.\n\n📋 Причина: {text}"
                )
            await update.message.reply_text("✅ Причина отправлена пользователю.")
            return

        # ── Admin reject order reason ─────────────────────────────────────────
        pending_ord = get_state(f"reject_ord_{ADMIN_ID}")
        if pending_ord:
            order_id = int(pending_ord)
            del_state(f"reject_ord_{ADMIN_ID}")
            order = get_order(order_id)
            update_order_status(order_id, "rejected")
            if order:
                await ctx.bot.send_message(
                    order["tg_id"],
                    f"❌ Ваш заказ #{order_id} отклонён.\n\n📋 Причина: {text}",
                    reply_markup = main_menu(order["tg_id"])
                )
            await update.message.reply_text("✅ Причина отправлена пользователю.")
            return

        # ── Broadcast ─────────────────────────────────────────────────────────
        if get_state(f"broadcast_{ADMIN_ID}") == "waiting":
            del_state(f"broadcast_{ADMIN_ID}")
            users = all_approved_users()
            sent  = 0
            for row in users:
                try:
                    await ctx.bot.send_message(row["tg_id"], text)
                    sent += 1
                except Exception:
                    pass
            await update.message.reply_text(f"📢 Рассылка завершена. Отправлено: {sent}")
            return

        # ── Promo create ──────────────────────────────────────────────────────
        if get_state(f"promo_create_{ADMIN_ID}") == "waiting":
            del_state(f"promo_create_{ADMIN_ID}")
            parts = text.strip().split()
            if len(parts) != 3:
                await update.message.reply_text("Неверный формат. Пример: GREEN10 10 5")
                return
            try:
                code, amount, acts = parts[0].upper(), float(parts[1]), int(parts[2])
                create_promo(code, amount, acts)
                await update.message.reply_text(f"✅ Промокод <code>{code}</code> создан!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {e}")
            return

    # ── User flows handled by ConversationHandlers (fallthrough is fine) ──────
