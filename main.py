# main.py
"""
Бот для бронирования массажей (Aiogram 3.x)
Версия: без базы данных — заявки пересылаются администраторам в личные сообщения.
Требования:
 - .env с BOT_TOKEN и ADMIN_IDS
 - Папка images/ рядом с main.py с картинками:
     service1.jpg, service2.jpg, service3.jpg, confirmation.jpg (имена можно менять в константах)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Логирование и загрузка .env
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("booking-bot")

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split() if x]

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

# -----------------------------------------------------------------------------
# Инициализация бота и диспетчера
# -----------------------------------------------------------------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -----------------------------------------------------------------------------
# Путь к локальной папке с картинками
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.join(BASE_DIR, "images")
# Пути к файлам (если не найдены — бот отправит текст)
SERVICE_IMG_1 = os.path.join(IMG_DIR, "service1.jpg")
SERVICE_IMG_2 = os.path.join(IMG_DIR, "service2.jpg")
SERVICE_IMG_3 = os.path.join(IMG_DIR, "service3.jpg")
CONFIRM_IMG = os.path.join(IMG_DIR, "confirmation.jpg")
MAIN_BANNER_IMG = os.path.join(IMG_DIR, "banner.jpg")  # опционально локальный баннер

# -----------------------------------------------------------------------------
# Данные по услугам: тексты RU/EN, цены, локальные картинки
# -----------------------------------------------------------------------------
SERVICES: Dict[str, Dict[str, Any]] = {
    "classic": {
        "title_ru": "Классический массаж",
        "title_en": "Classic massage",
        "desc_ru": "Классическая техника массажа всего тела — расслабление мышц, проработка зажимов, улучшение кровообращения.",
        "desc_en": "Basic full-body technique — relaxation, improves circulation.",
        "base_price_60": 60,
        "image_path": SERVICE_IMG_1,
    },
    "relax": {
        "title_ru": "Расслабляющий массаж",
        "title_en": "Relaxing massage",
        "desc_ru": "Медленные техники, фокус на релаксации и снижении стресса.",
        "desc_en": "Slow techniques, focus on relaxation and stress relief.",
        "base_price_60": 55,
        "image_path": SERVICE_IMG_2,
    },
    "deep_trigger": {
        "title_ru": "Глубокий массаж",
        "title_en": "Deep tissue massage",
        "desc_ru": "Глубокая проработка мышц и триггерных точек.",
        "desc_en": "Deep work with muscle knots and trigger points.",
        "base_price_60": 70,
        "image_path": SERVICE_IMG_3,
    },
}

# -----------------------------------------------------------------------------
# Параметры длительностей (добавлен 60 как дефолт)
# -----------------------------------------------------------------------------
DURATION_OPTIONS: List[Tuple[int, str, str]] = [
    (30, "30 мин", "30 min"),
    (45, "45 мин", "45 min"),
    (60, "1 час", "1 hour"),
    (90, "1 ч 30 мин", "1.5 hours"),
]

# -----------------------------------------------------------------------------
# Слоты: часы
# -----------------------------------------------------------------------------
SLOT_START = 10  # 10:00
SLOT_END = 19    # 19:00

# -----------------------------------------------------------------------------
# Тексты (RU / EN)
# -----------------------------------------------------------------------------
TEXT: Dict[str, Dict[str, str]] = {
    "ru": {
        "greet_both": "🌟 Привет! Я помогу подобрать и забронировать массаж. / Hello! I will help you to select and book a massage.\n\nРусский — нажмите 🇷🇺\nEnglish — нажмите 🇬🇧",
        "greet_caption": "🌟 Тут по шагам ты сможешь выбрать массаж, время, дату и оформить бронь.\n\nВыберите подходящий вид массажа:",
        "choose_service": "Выберите вид массажа:",
        "duration_prompt": "⏰ Подтверди длительность сеанса:",
        "calendar_prompt": "📅 Выберите дату (доступно 14 дней):",
        "slots_prompt": "🕐 Какое желаемое время?:",
        "summary_title": "📋 Ваш выбор:",
        "need_date_time": "❗ Сначала выберите дату и время.",
        "book_now": "📩 Забронировать сейчас",
        "cancel_back": "◀️ Отменить / Назад в меню",
        "choose_contact": "📞 Укажите контакт для связи (можно использовать @username или номер +...):",
        "use_username": "Использовать Telegram @{username}",
        "enter_contact": "Ввести контакт вручную",
        "booking_saved": "✅ Спасибо! Заявка отправлена. Администратор проверит и свяжется по оставленному контакту.\n Узанть больше про практики можно тут: https://body-mind-harmony-guide.lovable.app/ и канал @itsmartmassage",
        "booking_confirmed": "✅ Ваш массаж забронирован, с вами свяжется специалист.",
        "updated": "✅ Обновлено",
        "no_bookings": "📝 У вас пока нет заявок.",
        "my_bookings_title": "📋 Ваши заявки:",
        "minutes": "мин",
        "view_cart": "🛒 Корзина",
        "added_to_cart": "✅ Добавлено в корзину.",
        "delete": "❌ Удалить",
    },
    "en": {
        "greet_both": "🌟 Hello! / Привет!\n\nEnglish — press 🇬🇧\nРусский — press 🇷🇺",
        "greet_caption": "🌟 Hi — I can help you pick and book a massage.\n\nChoose a massage type:",
        "choose_service": "Choose a massage type:",
        "duration_prompt": "⏰ Choose duration:",
        "calendar_prompt": "📅 Choose date (14 days):",
        "slots_prompt": "🕐 Choose time (slot):",
        "summary_title": "📋 Your selection:",
        "need_date_time": "❗ First choose date and time.",
        "book_now": "📩 Book now",
        "cancel_back": "◀️ Cancel / Back to menu",
        "choose_contact": "📞 Provide contact (or use @username or +phone):",
        "use_username": "Use Telegram @{username}",
        "enter_contact": "Enter contact manually",
        "booking_saved": "✅ Booking saved. Await confirmation.",
        "booking_confirmed": "✅ Thank you, your massage is booked, the specialist will contact you. \n You could learn more about practice: https://body-mind-harmony-guide.lovable.app/",
        "updated": "✅ Updated",
        "no_bookings": "📝 You have no bookings yet.",
        "my_bookings_title": "📋 Your bookings:",
        "minutes": "min",
        "view_cart": "🛒 View cart",
        "added_to_cart": "✅ Added to cart.",
        "delete": "❌ Remove",
    },
}

# -----------------------------------------------------------------------------
# FSM: состояния
# -----------------------------------------------------------------------------
class Flow(StatesGroup):
    choosing_language = State()
    choosing_service = State()
    choosing_duration = State()
    choosing_datetime = State()
    summary = State()
    entering_contact = State()
    viewing_cart = State()

# -----------------------------------------------------------------------------
# Утилиты
# -----------------------------------------------------------------------------
def calc_price(service_key: str, duration_min: int) -> int:
    base = SERVICES[service_key]["base_price_60"]
    return int(round(base * duration_min / 60))

def get_lang_from_state(data: Dict[str, Any]) -> str:
    return data.get("lang", "ru")

def svc_title(key: str, lang: str) -> str:
    return SERVICES[key]["title_ru"] if lang == "ru" else SERVICES[key]["title_en"]

def svc_desc(key: str, lang: str) -> str:
    return SERVICES[key]["desc_ru"] if lang == "ru" else SERVICES[key]["desc_en"]

def sanitize_contact_input(raw: str) -> str:
    if not raw:
        return ""
    allowed = set("0123456789@+abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -()")
    return "".join(c for c in raw.strip() if c in allowed)

# -----------------------------------------------------------------------------
# Keyboards
# -----------------------------------------------------------------------------
def lang_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇷🇺 Русский", callback_data="lang:ru")
    b.button(text="🇬🇧 English", callback_data="lang:en")
    b.adjust(2)
    return b.as_markup()

def service_list_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key in SERVICES.keys():
        b.button(text=svc_title(key, lang), callback_data=f"svc:{key}")
    b.adjust(1)
    return b.as_markup()

def service_card_kb(current_key: str, lang: str, cart_exists: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    # выделенная кнопка "Забронировать" — помещаем эмодзи и верхний регистр
    b.button(text=f"🎯 {TEXT[lang]['book_now'].upper()}", callback_data=f"book:{current_key}")
    # другие услуги
    for k in SERVICES.keys():
        if k != current_key:
            b.button(text=svc_title(k, lang), callback_data=f"svc:{k}")
    # показать корзину, если есть
    if cart_exists:
        b.button(text=TEXT[lang]["view_cart"], callback_data="cart:view")
    b.adjust(1)
    return b.as_markup()

def duration_kb(current_service: str, current_duration: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for minutes, label_ru, label_en in DURATION_OPTIONS:
        label = label_ru if lang == "ru" else label_en
        price = calc_price(current_service, minutes)
        mark = "• " if minutes == current_duration else ""
        b.button(text=f"{mark}{label} — €{price}", callback_data=f"dur:{minutes}")
    b.adjust(1)
    return b.as_markup()

def calendar_kb_4x(start_date: datetime) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    days = [start_date + timedelta(days=i) for i in range(14)]
    for i, d in enumerate(days):
        label = d.strftime("%d %b")
        b.button(text=label, callback_data=f"cal:{d.date().isoformat()}")
        if (i + 1) % 4 == 0:
            b.adjust(4)
    if len(days) % 4 != 0:
        b.adjust(4)
    return b.as_markup()

def slots_kb_for_date(date_iso: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    hours = [f"{h:02d}:00" for h in range(SLOT_START, SLOT_END + 1)]
    for i, t in enumerate(hours):
        payload = f"dt:{date_iso}|{t}"
        b.button(text=t, callback_data=payload)
        if (i + 1) % 4 == 0:
            b.adjust(4)
    if len(hours) % 4 != 0:
        b.adjust(4)
    return b.as_markup()

def summary_kb(lang: str, cart_exists: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=TEXT[lang]["book_now"], callback_data="submit:now")
    b.adjust(1)
    if cart_exists:
        b.button(text=TEXT[lang]["view_cart"], callback_data="cart:view")
        b.adjust(1)
    return b.as_markup()

def cart_items_kb(cart: List[Dict[str, Any]], lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for idx, _ in enumerate(cart):
        b.button(text=f"{TEXT[lang]['delete']} {idx+1}", callback_data=f"cart:del:{idx}")
    b.button(text=TEXT[lang]["book_now"], callback_data="cart:checkout")
    b.adjust(1)
    return b.as_markup()

# -----------------------------------------------------------------------------
# Формирование текста сводки
# -----------------------------------------------------------------------------
def build_summary_text(data: Dict[str, Any], lang: str) -> str:
    svc_key = data.get("service")
    svc_name = svc_title(svc_key, lang) if svc_key else "—"
    duration = int(data.get("duration_min", 60))
    price = calc_price(svc_key, duration) if svc_key else 0
    date = data.get("date") or "—"
    time = data.get("time") or "—"
    minutes_label = TEXT[lang].get("minutes", "min")
    return (
        f"{TEXT[lang]['summary_title']}\n"
        f"• {svc_name}\n"
        f"• {duration} {minutes_label}\n"
        f"• €{price}\n"
        f"• {date} {time}"
    )

# -----------------------------------------------------------------------------
# Хендлеры
# -----------------------------------------------------------------------------
@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Flow.choosing_language)
    # Показываем двуязычное приветствие с выбором языка
    # Попытаемся отправить локальный баннер, если есть; иначе отправляем текст + клавиатуру
    if os.path.exists(MAIN_BANNER_IMG):
        try:
            photo = FSInputFile(MAIN_BANNER_IMG)
            await message.answer_photo(photo=photo, caption=TEXT["ru"]["greet_both"], reply_markup=lang_kb())
            return
        except Exception:
            logger.exception("Failed to send local banner, sending text")
    await message.answer(TEXT["ru"]["greet_both"], reply_markup=lang_kb())

@dp.message(F.text == "/info")
async def cmd_info(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Тут можно быстро выбрать нужный тип массажа, далее забронировать дату и время, "
        "оставив контакт для связи.\n\n"
        "Специалист ответит по выбранному виду связи для подтверждения выезда.\n"
        "Чтобы начать бронирование, нажмите /start.\n\n"
        "Больше: https://body-mind-harmony-guide.lovable.app/ и канал @itsmartmassage"
    )

@dp.message(F.text == "/menu")
async def cmd_menu(message: Message, state: FSMContext):
    # просто показываем список услуг (если язык не в state — предложим выбор языка)
    data = await state.get_data()
    lang = get_lang_from_state(data)
    # Если язык не выбран — перенаправляем на старт (выбор языка)
    if "lang" not in data:
        await cmd_start(message, state)
        return
    await message.answer(TEXT[lang]["choose_service"], reply_markup=service_list_kb(lang))

@dp.callback_query(F.data.startswith("lang:"), Flow.choosing_language)
async def set_language(call: CallbackQuery, state: FSMContext):
    _, _, lang = call.data.partition(":")
    if lang not in ("ru", "en"):
        lang = "ru"
    await state.update_data(lang=lang, cart=[])
    await state.set_state(Flow.choosing_service)
    await call.answer()
    # Отправляем баннер (локальный если есть) и список услуг
    if os.path.exists(MAIN_BANNER_IMG):
        try:
            await call.message.answer_photo(photo=FSInputFile(MAIN_BANNER_IMG), caption=TEXT[lang]["greet_caption"], reply_markup=service_list_kb(lang))
            return
        except Exception:
            logger.exception("Failed to send local banner image")
    await call.message.answer(TEXT[lang]["greet_caption"], reply_markup=service_list_kb(lang))

@dp.callback_query(F.data.startswith("svc:"), Flow.choosing_service)
async def on_service_selected(call: CallbackQuery, state: FSMContext):
    _, _, key = call.data.partition(":")
    data = await state.get_data()
    lang = get_lang_from_state(data)
    if key not in SERVICES:
        await call.answer("Invalid service", show_alert=True)
        return
    svc = SERVICES[key]
    caption = (
        f"{svc_title(key, lang)}\n\n"
        f"{svc_desc(key, lang)}\n\n"
        f"⏰ 60 {TEXT[lang]['minutes']} по умолчанию\n"
        f"💰 €{svc['base_price_60']}"
    )
    # сохраняем выбор услуги
    await state.update_data(service=key, duration_min=60, username=call.from_user.username or "")
    cart = (await state.get_data()).get("cart") or []
    await call.answer()
    # Отправляем локальное изображение, если существует
    image_path = svc.get("image_path")
    if image_path and os.path.exists(image_path):
        try:
            photo = FSInputFile(image_path)
            await call.message.answer_photo(photo=photo, caption=caption, reply_markup=service_card_kb(key, lang, bool(cart)))
            return
        except Exception:
            logger.exception("Error sending service image")
    # fallback: текст и inline
    await call.message.answer(caption, reply_markup=service_card_kb(key, lang, bool(cart)))

@dp.callback_query(F.data.startswith("book:"), Flow.choosing_service)
async def on_book_click(call: CallbackQuery, state: FSMContext):
    _, _, key = call.data.partition(":")
    data = await state.get_data()
    lang = get_lang_from_state(data)
    if key not in SERVICES:
        await call.answer("Invalid", show_alert=True)
        return
    await state.update_data(service=key)
    await state.set_state(Flow.choosing_duration)
    await call.answer()
    data = await state.get_data()
    await call.message.answer(build_summary_text(data, lang), reply_markup=duration_kb(key, data.get("duration_min", 60), lang))
    await call.message.answer(TEXT[lang]["calendar_prompt"], reply_markup=calendar_kb_4x(datetime.now()))

@dp.callback_query(F.data.startswith("dur:"), Flow.choosing_duration)
async def on_duration_change(call: CallbackQuery, state: FSMContext):
    _, minutes = call.data.split(":", 1)
    try:
        minutes_int = int(minutes)
    except ValueError:
        await call.answer("Invalid", show_alert=True)
        return
    await state.update_data(duration_min=minutes_int)
    data = await state.get_data()
    lang = get_lang_from_state(data)
    await call.answer()
    await call.message.answer(TEXT[lang]["updated"])
    await call.message.answer(build_summary_text(data, lang), reply_markup=duration_kb(data["service"], minutes_int, lang))
    if not data.get("date"):
        await state.set_state(Flow.choosing_datetime)
        await call.message.answer(TEXT[lang]["calendar_prompt"], reply_markup=calendar_kb_4x(datetime.now()))
    else:
        await state.set_state(Flow.summary)
        cart = data.get("cart") or []
        await call.message.answer(build_summary_text(data, lang), reply_markup=summary_kb(lang, bool(cart)))

@dp.callback_query(F.data.startswith("cal:"), Flow.choosing_duration)
@dp.callback_query(F.data.startswith("cal:"), Flow.choosing_datetime)
async def pick_date(call: CallbackQuery, state: FSMContext):
    _, _, iso = call.data.partition(":")
    data_prev = await state.get_data()
    lang = get_lang_from_state(data_prev)
    await state.update_data(date=iso)
    await state.set_state(Flow.choosing_datetime)
    await call.answer(f"📅 {iso}")
    await call.message.answer(TEXT[lang]["slots_prompt"], reply_markup=slots_kb_for_date(iso))

@dp.callback_query(F.data.startswith("dt:"), Flow.choosing_datetime)
async def pick_datetime_one_step(call: CallbackQuery, state: FSMContext):
    _, _, payload = call.data.partition(":")
    try:
        date_iso, timestr = payload.split("|", 1)
    except Exception:
        await call.answer("Invalid", show_alert=True)
        return
    prev = await state.get_data()
    lang = get_lang_from_state(prev)
    await state.update_data(date=date_iso, time=timestr)
    await state.set_state(Flow.summary)
    await call.answer(f"🕐 {date_iso} {timestr}")
    data = await state.get_data()
    cart = data.get("cart") or []
    await call.message.answer(build_summary_text(data, lang), reply_markup=summary_kb(lang, bool(cart)))

@dp.callback_query(F.data == "cart:add", F.state.in_({Flow.summary, Flow.choosing_service, Flow.choosing_duration}))
async def add_current_to_cart(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    if not data.get("date") or not data.get("time"):
        await call.answer(TEXT[lang]["need_date_time"], show_alert=True)
        return
    item = {
        "service": data["service"],
        "duration_min": int(data.get("duration_min", 60)),
        "date": data["date"],
        "time": data["time"],
        "price": calc_price(data["service"], int(data.get("duration_min", 60))),
    }
    cart = data.get("cart") or []
    cart.append(item)
    await state.update_data(cart=cart)
    await call.answer()
    # подтверждение и кнопка "корзина"
    kb = InlineKeyboardBuilder()
    kb.button(text=TEXT[lang]["view_cart"], callback_data="cart:view")
    kb.adjust(1)
    await call.message.answer(TEXT[lang]["added_to_cart"], reply_markup=kb.as_markup())

@dp.callback_query(F.data == "cart:view")
async def view_cart(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    cart = data.get("cart") or []
    await state.set_state(Flow.viewing_cart)
    await call.answer()
    if not cart:
        await call.message.answer(TEXT[lang]["no_bookings"])
        return
    lines = [TEXT[lang]["view_cart"], ""]
    for idx, item in enumerate(cart):
        svc_name = svc_title(item["service"], lang)
        lines.append(f"{idx+1}. {svc_name}, {item['duration_min']} {TEXT[lang].get('minutes','min')}, €{item['price']}, {item['date']} {item['time']}")
    kb = cart_items_kb(cart, lang)
    await call.message.answer("\n".join(lines), reply_markup=kb)

@dp.callback_query(F.data.startswith("cart:del:"), Flow.viewing_cart)
async def cart_delete_item(call: CallbackQuery, state: FSMContext):
    _, _, idx_str = call.data.partition(":")
    try:
        idx = int(idx_str)
    except ValueError:
        await call.answer("Error", show_alert=True)
        return
    data = await state.get_data()
    cart = data.get("cart") or []
    if 0 <= idx < len(cart):
        cart.pop(idx)
    await state.update_data(cart=cart)
    await call.answer()
    await view_cart(call, state)

@dp.callback_query(F.data == "cart:checkout", Flow.viewing_cart)
async def cart_checkout(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    cart = data.get("cart") or []
    if not cart:
        await call.answer(TEXT[lang]["no_bookings"], show_alert=True)
        return
    username = call.from_user.username or ""
    await state.update_data(username=username)
    await state.set_state(Flow.entering_contact)
    kb = InlineKeyboardBuilder()
    if username:
        kb.button(text=TEXT[lang]["use_username"].format(username=username), callback_data=f"use_contact:@{username}")
    kb.button(text=TEXT[lang]["enter_contact"], callback_data="enter_contact_manual")
    kb.adjust(1)
    await call.answer()
    await call.message.answer(TEXT[lang]["choose_contact"], reply_markup=kb.as_markup())

@dp.callback_query(F.data == "enter_contact_manual", Flow.entering_contact)
async def enter_contact_manual_cb(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    await state.set_state(Flow.entering_contact)
    await call.answer()
    await call.message.answer(TEXT[lang]["choose_contact"])

@dp.callback_query(F.data.startswith("use_contact:"), Flow.entering_contact)
async def use_contact_cb(call: CallbackQuery, state: FSMContext):
    _, _, contact_value = call.data.partition(":")
    contact_value = contact_value.strip()
    data = await state.get_data()
    lang = get_lang_from_state(data)
    cart = data.get("cart") or []
    
    # Проверяем есть ли заявки в корзине ИЛИ одиночная заявка
    has_cart_items = bool(cart)
    has_single_booking = bool(data.get("service") and data.get("date") and data.get("time"))
    
    if not has_cart_items and not has_single_booking:
        await call.answer(TEXT[lang]["no_bookings"], show_alert=True)
        return
    
    saved_ok = True
    try:
        if has_cart_items:
            # Отправляем все позиции из корзины админам
            svc_lines = []
            for idx, item in enumerate(cart, start=1):
                svc_lines.append(f"{idx}. {svc_title(item['service'], lang)}, {item['duration_min']} {TEXT[lang]['minutes']}, €{item['price']}, {item['date']} {item['time']}")
            notify_text = f"📋 New bookings from @{call.from_user.username}\nContact: {contact_value}\n\n" + "\n".join(svc_lines)
        else:
            # Отправляем одиночную заявку
            svc = data.get("service")
            duration = int(data.get("duration_min", 60))
            price = calc_price(svc, duration)
            notify_text = (
                f"📋 New booking\n"
                f"👤 @{call.from_user.username}\n"
                f"💆‍♀️ {svc_title(svc, lang)}\n"
                f"⏰ {duration} {TEXT[lang]['minutes']}, €{price}\n"
                f"📅 {data['date']} {data['time']}\n"
                f"📞 {contact_value}"
            )
        
        for admin in ADMIN_IDS:
            try:
                await bot.send_message(admin, notify_text)
            except Exception:
                logger.exception("Failed to notify admin")
    except Exception:
        saved_ok = False
        logger.exception("Error sending bookings to admins")
    
    await call.answer()
    if saved_ok:
        # показать картинку подтверждения, если есть
        if os.path.exists(CONFIRM_IMG):
            try:
                await call.message.answer_photo(photo=FSInputFile(CONFIRM_IMG), caption=TEXT[lang]["booking_confirmed"], reply_markup=service_list_kb(lang))
            except Exception:
                logger.exception("Failed sending confirmation image")
                await call.message.answer(TEXT[lang]["booking_confirmed"], reply_markup=service_list_kb(lang))
        else:
            await call.message.answer(TEXT[lang]["booking_confirmed"], reply_markup=service_list_kb(lang))
        await call.message.answer(TEXT[lang]["booking_saved"])
        # очистка корзины
        await state.update_data(cart=[])
    else:
        await call.message.answer("Ошибка при отправке. Попробуйте позже.")
    await state.clear()

@dp.message(Flow.entering_contact)
async def entering_contact_message(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    raw = message.text or ""
    contact = sanitize_contact_input(raw)
    if not contact:
        contact = data.get("username", "")
    cart = data.get("cart") or []
    if cart:
        # Отправляем все позиции админам
        try:
            svc_lines = []
            for idx, item in enumerate(cart, start=1):
                svc_lines.append(f"{idx}. {svc_title(item['service'], lang)}, {item['duration_min']} {TEXT[lang]['minutes']}, €{item['price']}, {item['date']} {item['time']}")
            notify_text = f"📋 New bookings from @{message.from_user.username}\nContact: {contact}\n\n" + "\n".join(svc_lines)
            for admin in ADMIN_IDS:
                try:
                    await bot.send_message(admin, notify_text)
                except Exception:
                    logger.exception("Failed send admin (manual contact, cart)")
            # подтверждение пользователю
            if os.path.exists(CONFIRM_IMG):
                try:
                    await message.answer_photo(photo=FSInputFile(CONFIRM_IMG), caption=TEXT[lang]["booking_confirmed"])
                except Exception:
                    logger.exception("Failed to send confirmation image (manual cart)")
                    await message.answer(TEXT[lang]["booking_confirmed"])
            else:
                await message.answer(TEXT[lang]["booking_confirmed"])
            await message.answer(TEXT[lang]["booking_saved"])
            await state.update_data(cart=[])
        except Exception:
            logger.exception("Error processing cart checkout (manual contact)")
            await message.answer("Ошибка при отправке. Попробуйте позже.")
        await state.clear()
        return
    # Если cart пуст — одиночная заявка (Book now)
    svc = data.get("service")
    if not svc or not data.get("date") or not data.get("time"):
        await message.answer(TEXT[lang]["need_date_time"])
        await state.clear()
        return
    duration = int(data.get("duration_min", 60))
    price = calc_price(svc, duration)
    # Отправляем админам уведомление
    try:
        notify_text = (
            f"📋 New booking\n"
            f"👤 @{message.from_user.username}\n"
            f"💆‍♀️ {svc_title(svc, lang)}\n"
            f"⏰ {duration} {TEXT['en']['minutes']}, €{price}\n"
            f"📅 {data['date']} {data['time']}\n"
            f"📞 {contact}"
        )
        for admin in ADMIN_IDS:
            try:
                await bot.send_message(admin, notify_text)
            except Exception:
                logger.exception("Failed to send admin notification (single manual contact)")
        # подтверждение пользователю
        if os.path.exists(CONFIRM_IMG):
            try:
                await message.answer_photo(photo=FSInputFile(CONFIRM_IMG), caption=TEXT[lang]["booking_confirmed"], reply_markup=service_list_kb(lang))
            except Exception:
                logger.exception("Failed to send confirmation image (single manual contact)")
                await message.answer(TEXT[lang]["booking_confirmed"], reply_markup=service_list_kb(lang))
        else:
            await message.answer(TEXT[lang]["booking_confirmed"], reply_markup=service_list_kb(lang))
        await message.answer(TEXT[lang]["booking_saved"])
    except Exception:
        logger.exception("Error saving single booking (manual contact)")
        await message.answer("Ошибка при отправке. Попробуйте позже.")
    await state.clear()

@dp.callback_query(F.data == "submit:now", Flow.summary)
async def submit_now(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    if not data.get("date") or not data.get("time"):
        await call.answer(TEXT[lang]["need_date_time"], show_alert=True)
        return
    username = call.from_user.username or ""
    await state.update_data(username=username)
    await state.set_state(Flow.entering_contact)
    kb = InlineKeyboardBuilder()
    if username:
        kb.button(text=TEXT[lang]["use_username"].format(username=username), callback_data=f"use_contact:@{username}")
    kb.button(text=TEXT[lang]["enter_contact"], callback_data="enter_contact_manual")
    kb.button(text=TEXT[lang]["cancel_back"], callback_data="nav:back")
    kb.adjust(1)
    await call.answer()
    await call.message.answer(TEXT[lang]["choose_contact"], reply_markup=kb.as_markup())

@dp.callback_query(F.data == "nav:back")
async def nav_back(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_lang_from_state(data)
    await state.set_state(Flow.choosing_service)
    await call.answer()
    await call.message.answer(TEXT[lang]["choose_service"], reply_markup=service_list_kb(lang))

@dp.message(F.text.in_({"Мои заявки", "/my", "My bookings", "/mybookings"}))
async def my_bookings(message: Message):
    # БД отключена: сообщаем пользователю, что просмотр заявок недоступен
    await message.answer("📝 Ведение истории заявок локально отключено. Все заявки отправлены администраторам.")

# -----------------------------------------------------------------------------
# Запуск поллинга
# -----------------------------------------------------------------------------
async def main():
    # Никакой инициализации БД — она отсутствует
    logger.info("Starting bot (no DB). Admins: %s", ADMIN_IDS)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down bot")
