import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ============================================================
BOT_TOKEN = "8651620772:AAFYJWsxI3voZLpY-QQY-LjTGfwo6irbz7k"
ADMIN_ID  = 448737168
OPB_LINK  = "https://openbudget.uz/boards/initiatives/initiative/53/2b0b7b9e-0dd1-4554-9738-0083d433c869"
SUPPORT   = "@Xusniddinxojiyev"
# ============================================================

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# { user_id: {"name","phone","username","answer","waiting_screenshot","done"} }
members: dict = {}

def full_name(user):
    n = (user.first_name or "")
    if user.last_name:
        n += f" {user.last_name}"
    return n.strip() or f"ID:{user.id}"

def phone_keyboard():
    btn = KeyboardButton("📱 Raqamni yuborish", request_contact=True)
    return ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)

def vote_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha, ovoz berdim", callback_data="ha"),
        InlineKeyboardButton("❌ Yo'q", callback_data="yoq"),
    ]])

def after_link_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗳 Open Budjetga o'tish", url=OPB_LINK)],
        [InlineKeyboardButton("✅ Ovoz berdim", callback_data="after_voted")],
        [InlineKeyboardButton("❌ Hali bermaganman", callback_data="yoq")],
    ])

def screenshot_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ Screenshot yo'q", callback_data="skip_screenshot")
    ]])

def bot_link(context):
    return f"https://t.me/{context.bot.username}"

# ─── GURUHDA XABAR ───────────────────────────────────────────

async def group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhda kimdir xabar yozsa — o'chirib, botga yo'naltiramiz"""
    user = update.effective_user
    if not user or user.is_bot:
        return
    if user.id == ADMIN_ID:
        return  # Admin yoza oladi

    # Xabarni o'chirish
    try:
        await update.message.delete()
    except Exception:
        pass

    # Botga o'tish tugmasi bilan xabar
    name = full_name(user)
    link = bot_link(context)
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"⛔ {name}, guruhda yozish mumkin emas!\n\n"
            f"Yozishdan oldin botga kirib ro'yxatdan o'ting 👇"
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Botga o'tish", url=link)
        ]])
    )

    # 10 soniyadan keyin bu xabarni ham o'chirish
    context.job_queue.run_once(
        delete_message,
        when=10,
        data={"chat_id": msg.chat_id, "message_id": msg.message_id}
    )

async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    """Muddati o'tgan xabarni o'chirish"""
    try:
        await context.bot.delete_message(
            chat_id=context.job.data["chat_id"],
            message_id=context.job.data["message_id"]
        )
    except Exception:
        pass

# ─── /start (shaxsiy) ────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Guruhda /start bosilsa — faqat botga yo'naltir
    if chat.type in ["group", "supergroup"]:
        try:
            await update.message.delete()
        except Exception:
            pass
        link = bot_link(context)
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text="👆 Ro'yxatdan o'tish uchun botga o'ting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Botga o'tish", url=link)
            ]])
        )
        context.job_queue.run_once(
            delete_message, when=10,
            data={"chat_id": msg.chat_id, "message_id": msg.message_id}
        )
        return

    # Shaxsiy xabarda
    name = full_name(user)

    if user.id in members and members[user.id].get("done"):
        await update.message.reply_text(
            f"✅ Siz allaqachon ro'yxatdan o'tgansiz!\n"
            f"Yordam kerak bo'lsa: {SUPPORT}"
        )
        return

    if user.id not in members:
        members[user.id] = {
            "name": name, "phone": None,
            "username": user.username or "",
            "answer": None,
            "waiting_screenshot": False,
            "done": False
        }
    else:
        members[user.id]["name"] = name

    await update.message.reply_text(
        f"Salom, {name}! 👋\n\n"
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard()
    )

# ─── Raqam keldi ─────────────────────────────────────────────

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    phone = update.message.contact.phone_number
    name  = full_name(user)

    if user.id not in members:
        members[user.id] = {
            "name": name, "phone": None,
            "username": user.username or "",
            "answer": None,
            "waiting_screenshot": False,
            "done": False
        }

    members[user.id]["phone"] = phone
    members[user.id]["name"]  = name

    await update.message.reply_text(
        "Rahmat! 👍\n\nOpen Budjet taklifiga ovoz berdingizmi?",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("👇 Javob bering:", reply_markup=vote_keyboard())

# ─── Tugmalar ─────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    data  = query.data
    name  = full_name(user)

    await query.answer()

    if user.id not in members or not members[user.id].get("phone"):
        await query.edit_message_text("Iltimos /start bosing.")
        return

    phone = members[user.id]["phone"]
    uname = f"@{user.username}" if user.username else f"ID:{user.id}"

    # ── HA ──
    if data == "ha":
        members[user.id]["answer"] = "ha"
        members[user.id]["waiting_screenshot"] = True

        await query.edit_message_text(
            "✅ Zo'r!\n\n"
            "📸 Isboti uchun <b>screenshot yuboring</b> 👇\n\n"
            "Screenshotingiz bo'lmasa pastdagi tugmani bosing.",
            parse_mode="HTML",
            reply_markup=screenshot_keyboard()
        )
        await context.bot.send_message(
            ADMIN_ID,
            f"✅ <b>Ovoz BERGAN (screenshot kutilmoqda):</b>\n"
            f"👤 {name} | {uname}\n"
            f"📱 <code>{phone}</code>",
            parse_mode="HTML"
        )

    # ── YO'Q ──
    elif data == "yoq":
        members[user.id]["answer"] = "yoq"
        members[user.id]["waiting_screenshot"] = False

        await query.edit_message_text(
            "❌ Hali ovoz bermagansiz.\n\n"
            "👇 Quyidagi tugmani bosib ovoz bering,\n"
            "keyin <b>\"Ovoz berdim\"</b> tugmasini bosing:",
            parse_mode="HTML",
            reply_markup=after_link_keyboard()
        )
        await context.bot.send_message(
            ADMIN_ID,
            f"❌ <b>Ovoz BERMAGAN:</b>\n"
            f"👤 {name} | {uname}\n"
            f"📱 <code>{phone}</code>",
            parse_mode="HTML"
        )

    # ── LINKDAN KEYIN OVOZ BERDIM ──
    elif data == "after_voted":
        members[user.id]["answer"] = "ha"
        members[user.id]["waiting_screenshot"] = True

        await query.edit_message_text(
            "✅ Zo'r!\n\n"
            "📸 Isboti uchun <b>screenshot yuboring</b> 👇\n\n"
            "Screenshotingiz bo'lmasa pastdagi tugmani bosing.",
            parse_mode="HTML",
            reply_markup=screenshot_keyboard()
        )
        await context.bot.send_message(
            ADMIN_ID,
            f"✅ <b>Ovoz BERGAN (screenshot kutilmoqda):</b>\n"
            f"👤 {name} | {uname}\n"
            f"📱 <code>{phone}</code>",
            parse_mode="HTML"
        )

    # ── SCREENSHOT YO'Q ──
    elif data == "skip_screenshot":
        members[user.id]["waiting_screenshot"] = False
        members[user.id]["done"] = True

        await query.edit_message_text(
            f"✅ Rahmat!\n\n"
            f"Yordam kerak bo'lsa {SUPPORT} ga murojaat qiling."
        )
        await context.bot.send_message(
            ADMIN_ID,
            f"⚠️ <b>Screenshot tashlamadi:</b>\n"
            f"👤 {name} | {uname}\n"
            f"📱 <code>{phone}</code>",
            parse_mode="HTML"
        )

# ─── Screenshot keldi ─────────────────────────────────────────

async def photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        return
    if user.id not in members or not members[user.id].get("waiting_screenshot"):
        return

    name  = full_name(user)
    phone = members[user.id].get("phone") or "—"
    uname = f"@{user.username}" if user.username else f"ID:{user.id}"

    members[user.id]["waiting_screenshot"] = False
    members[user.id]["done"]               = True
    members[user.id]["answer"]             = "ha"

    await update.message.reply_text(
        f"✅ Rahmat! Screenshot qabul qilindi.\n\n"
        f"Yordam kerak bo'lsa {SUPPORT} ga murojaat qiling."
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=(
            f"📸 <b>Screenshot keldi:</b>\n"
            f"👤 {name} | {uname}\n"
            f"📱 <code>{phone}</code>"
        ),
        parse_mode="HTML"
    )

# ─── Admin buyruqlari ─────────────────────────────────────────

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not members:
        await update.message.reply_text("📭 Hali hech kim ro'yxatdan o'tmagan.")
        return

    voted_s   = [(uid, m) for uid, m in members.items() if m.get("answer") == "ha" and m.get("done")]
    no_screen = [(uid, m) for uid, m in members.items() if m.get("answer") == "ha" and not m.get("done")]
    not_voted = [(uid, m) for uid, m in members.items() if m.get("answer") == "yoq"]
    pending   = [(uid, m) for uid, m in members.items() if not m.get("answer")]

    lines = []
    if voted_s:
        lines.append(f"✅ <b>Ovoz bergan + screenshot ({len(voted_s)}):</b>")
        for i, (uid, m) in enumerate(voted_s, 1):
            uname = f"@{m['username']}" if m['username'] else f"ID:{uid}"
            lines.append(f"{i}. {m['name']} | {uname} | 📱 <code>{m.get('phone','—')}</code>")

    if no_screen:
        lines.append(f"\n⚠️ <b>Screenshot tashlamadi ({len(no_screen)}):</b>")
        for i, (uid, m) in enumerate(no_screen, 1):
            uname = f"@{m['username']}" if m['username'] else f"ID:{uid}"
            lines.append(f"{i}. {m['name']} | {uname} | 📱 <code>{m.get('phone','—')}</code>")

    if not_voted:
        lines.append(f"\n❌ <b>Ovoz bermagan ({len(not_voted)}):</b>")
        for i, (uid, m) in enumerate(not_voted, 1):
            uname = f"@{m['username']}" if m['username'] else f"ID:{uid}"
            lines.append(f"{i}. {m['name']} | {uname} | 📱 <code>{m.get('phone','—')}</code>")

    if pending:
        lines.append(f"\n⏳ <b>Hali kirmagan ({len(pending)}):</b>")
        for uid, m in pending:
            uname = f"@{m['username']}" if m['username'] else f"ID:{uid}"
            lines.append(f"  • {m['name']} | {uname}")

    text = "\n".join(lines)
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await update.message.reply_text(chunk, parse_mode="HTML")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total     = len(members)
    voted_s   = sum(1 for m in members.values() if m.get("answer") == "ha" and m.get("done"))
    no_screen = sum(1 for m in members.values() if m.get("answer") == "ha" and not m.get("done"))
    not_voted = sum(1 for m in members.values() if m.get("answer") == "yoq")
    pending   = sum(1 for m in members.values() if not m.get("answer"))
    await update.message.reply_text(
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Jami: {total}\n"
        f"✅ Ovoz bergan + screenshot: {voted_s}\n"
        f"⚠️ Screenshot tashlamadi: {no_screen}\n"
        f"❌ Ovoz bermagan: {not_voted}\n"
        f"⏳ Hali kirmagan: {pending}",
        parse_mode="HTML"
    )

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    targets = [(uid, m) for uid, m in members.items() if m.get("answer") != "ha"]
    if not targets:
        await update.message.reply_text("🎉 Hamma ovoz bergan!")
        return
    sent = failed = 0
    for uid, m in targets:
        try:
            await context.bot.send_message(
                uid,
                f"👋 {m['name']}, salom!\n\n"
                f"Hali ovoz bermagansiz.\n"
                f"👉 {OPB_LINK}\n\nOvoz bergach /start bosing."
            )
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"📨 Yuborildi: {sent} | Yuborilmadi: {failed}")

# ─── MAIN ─────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Shaxsiy
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("list",   list_command))
    app.add_handler(CommandHandler("stats",  stats_command))
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_received))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_received))

    # Guruhda — barcha xabarlarni ushlab, o'chirish
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.User(ADMIN_ID),
        group_message
    ))

    print("✅ Bot ishga tushdi!")
    print("Guruhga admin qiling va 'Xabarlarni o'chirish' huquqini bering!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()