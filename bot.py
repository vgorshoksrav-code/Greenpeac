import logging
import asyncio
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from config import BOT_TOKEN
from handlers import (
    start_handler, registration_handler, admin_handler,
    payment_handler, order_handler, profile_handler, promo_handler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ── Registration flow ──────────────────────────────────────────────
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler.start)],
        states=registration_handler.STATES,
        fallbacks=[CommandHandler("start", start_handler.start)],
        allow_reentry=True,
    )

    # ── Payment flow ───────────────────────────────────────────────────
    pay_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(payment_handler.top_up_start, pattern="^topup$")
        ],
        states=payment_handler.STATES,
        fallbacks=[CommandHandler("cancel", payment_handler.cancel)],
    )

    # ── Order flow ─────────────────────────────────────────────────────
    order_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(order_handler.order_start, pattern="^order$")
        ],
        states=order_handler.STATES,
        fallbacks=[CommandHandler("cancel", order_handler.cancel)],
    )

    # ── Admin commands ─────────────────────────────────────────────────
    app.add_handler(reg_conv)
    app.add_handler(pay_conv)
    app.add_handler(order_conv)

    # Admin /add and /set commands
    app.add_handler(CommandHandler("add", admin_handler.cmd_add))
    app.add_handler(CommandHandler("set", admin_handler.cmd_set))

    # Callback buttons (approve/reject/etc.)
    app.add_handler(CallbackQueryHandler(admin_handler.handle_approve,     pattern=r"^approve_reg_"))
    app.add_handler(CallbackQueryHandler(admin_handler.handle_reject_req,  pattern=r"^reject_reg_"))
    app.add_handler(CallbackQueryHandler(admin_handler.handle_approve_ord, pattern=r"^approve_ord_"))
    app.add_handler(CallbackQueryHandler(admin_handler.handle_reject_ord,  pattern=r"^reject_ord_"))
    app.add_handler(CallbackQueryHandler(admin_handler.confirm_card_pay,   pattern=r"^confirm_card_"))

    # Admin menu
    app.add_handler(CallbackQueryHandler(admin_handler.admin_menu,         pattern="^admin_menu$"))
    app.add_handler(CallbackQueryHandler(admin_handler.admin_blocked,      pattern="^admin_blocked$"))
    app.add_handler(CallbackQueryHandler(admin_handler.admin_broadcast_start, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_handler.admin_promo_menu,   pattern="^admin_promo$"))
    app.add_handler(CallbackQueryHandler(admin_handler.admin_promo_create, pattern="^promo_create$"))

    # User menu buttons
    app.add_handler(CallbackQueryHandler(profile_handler.show_profile,     pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(profile_handler.show_stats,       pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(profile_handler.support,          pattern="^support$"))

    # Promo
    app.add_handler(CallbackQueryHandler(promo_handler.use_promo_start,    pattern="^use_promo$"))

    # Broadcast state handler (message after admin_broadcast button)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        admin_handler.router_text
    ))

    logger.info("Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
