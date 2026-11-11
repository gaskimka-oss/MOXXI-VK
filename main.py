"""🌟 MOXXI 3.0 — Полнофункциональный кроссплатформенный бот для ВКонтакте.
Папка: C:\\Users\\eiema\\OneDrive\\Desktop\\moxxivk

Все топовые системы перенесены и синхронизированы с единой базой SQLite (moxxi_vk.db):
1. 👑 10 Рангов администрации (Лидер [10], Зам [9] ... Стажёр [1]) + иммунитет иерархии
2. ⚔️ PvP Дуэли и Кости между игроками на монеты в беседах
3. 💘 Шипперинг (Пара дня) с подсчётом совместимости и пророчеством
4. 🏰 Кланы и Банды: создание, казна, топ кланов, вступление/выход
5. 💍 Браки, Семьи и Дети: свадьба, развод, завести ребёнка, уход и кормление
6. 🐉 Рейдовые Боссы беседы: спавн босса на 50 000 HP, совместная атака, распределение награды
7. 🏢 Бизнесы и Пассивный доход: кофейня, пиццерия, АЗС, IT-гигант, космодром
8. 🚗 Автопарк и Гараж: покупка авто от Lada Vesta до Bugatti Chiron
9. 🐾 Питомцы: зоомагазин, покупка, прокачка и кормление
10. 🃏 Азартные игры: 21 Очко (Блэкджек), Краш (Crash), Казино (Слоты), Рулетка, Монетка
11. ⛏ Интерактивный фарм: Шахта/Копать и Рыбалка с редким лутом
12. 🔮 Утилиты MOXXI: «инфа», «кто», «характеристика», «выбери», кастомные ники
13. 🛡 Модерация беседы: кик, варны (3/3 автокик), правила, автоприветствие, триггеры
14. 🆘 Омниканальный мост Техподдержки в Telegram
15. 🧠 Умный ИИ-собеседник Moxxi (ответы на вопросы при обращении)
16. 🥷 Ограбления и Тюрьма/КПЗ: воровство монет, поимка полицией, побеги через вентиляцию, залог
17. 📦 Лутбоксы и Кейсы: 4 уровня кейсов с анимацией открытия рулетки и дропом суперкаров
18. 🍾 Бутылочка в беседе: вращение, выбор двух участников беседы и смешные романтичные задания
19. 🎁 Система Подарков: каталог подарков, романтичные записки, персональная полка подарков в профиле
20. 🧠 Чат-Викторина (Квиз): 35+ вопросов на эрудицию, награды за скорость и первый верный ответ
21. 🏦 Государственный Банк: пополнение вклада, снятие, начисление 5% суточных процентов
"""
from __future__ import annotations

import asyncio
import datetime
import html
import json
import logging
import os
import random
import re
import sys
import time
import urllib.request
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from vkbottle import API, Keyboard, KeyboardButtonColor, Text, OpenLink
from vkbottle.bot import Bot, Message

import db
import payments
import extended

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir:
    os.chdir(current_dir)
load_dotenv(os.path.join(current_dir, ".env"))

# Настройка UTF-8 кодировки консоли
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] (MOXXI-VK) %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
if False:
    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (MOXXI-VK) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("moxxibot.vk")

VK_BOT_TOKEN = os.getenv("VK_BOT_TOKEN", "").strip()
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID", "243066051"))
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_OWNER_ID = int(os.getenv("TG_OWNER_ID", "8036974481"))
raw_owners = os.getenv("TG_OWNERS", "8036974481,8412527198")
TG_OWNERS = [int(x.strip()) for x in raw_owners.split(",") if x.strip().isdigit()]
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()

if not VK_BOT_TOKEN:
    raise ValueError("VK_BOT_TOKEN не задан в moxxivk/.env файле!")

bot = Bot(token=VK_BOT_TOKEN)

# 🛡 Автоматический фильтр HTML-тегов для ВКонтакте (ВК не поддерживает <b>, <i>, <code>)
_orig_messages_send = bot.api.messages.send

async def _clean_vk_messages_send(*args, **kwargs):
    if "message" in kwargs and isinstance(kwargs["message"], str):
        kwargs["message"] = re.sub(r"</?(?:b|i|code|u|s|pre|a|span|div)[^>]*>", "", kwargs["message"])
    return await _orig_messages_send(*args, **kwargs)

bot.api.messages.send = _clean_vk_messages_send

_orig_message_answer = Message.answer

async def _clean_message_answer(self, message=None, *args, **kwargs):
    if message and isinstance(message, str):
        message = re.sub(r"</?(?:b|i|code|u|s|pre|a|span|div)[^>]*>", "", message)
    return await _orig_message_answer(self, message, *args, **kwargs)

Message.answer = _clean_message_answer

# Изолированная база данных ВКонтакте (moxxi_vk.db)
VK_USER_OFFSET = 0

def to_db_uid(vk_id: int) -> int:
    return int(vk_id)

def from_db_uid(db_id: int) -> int:
    return int(db_id)

def to_db_cid(peer_id: int) -> int:
    return int(peer_id)


# ═══════════════════════════════════════════════════════════════
# 👑 СИСТЕМА РАНГОВ И ИЕРАРХИЯ БЕСЕДЫ (1–10)
# ═══════════════════════════════════════════════════════════════

RANK_NAMES = {
    0: "Участник",
    1: "Стажёр",
    2: "Младший модератор",
    3: "Старший модератор",
    4: "Главный модератор",
    5: "Младший админ",
    6: "Старший админ",
    7: "Главный админ",
    8: "Тех. администратор",
    9: "Заместитель",
    10: "Владелец чата",
}

RANK_ICONS = {
    10: "👑",
    9: "⚜️",
    8: "💻",
    7: "🏛",
    6: "🛡",
    5: "⚔️",
    4: "🔮",
    3: "🎖",
    2: "🔰",
    1: "🍃",
    0: "👤",
}

async def get_effective_rank(peer_id: int, user_id: int) -> int:
    if user_id in TG_OWNERS:
        return 10
    if peer_id < 2000000000:
        return 10

    db_cid = to_db_cid(peer_id)
    db_uid = to_db_uid(user_id)
    saved_rank = await db.get_user_rank(db_cid, db_uid)
    if saved_rank > 0:
        return saved_rank

    try:
        members = await bot.api.messages.get_conversation_members(peer_id=peer_id)
        for m in members.items:
            if m.member_id == user_id:
                if getattr(m, "is_owner", False):
                    return 10
                if getattr(m, "is_admin", False):
                    return 5
    except Exception:
        pass
    return 0

# Временные хранилища предложений и интерактивных систем
active_duels: dict[str, dict] = {}
active_marriages: dict[str, dict] = {}
ACTIVE_QUIZZES: dict[int, dict] = {}

CASES_CATALOG = {
    1: {
        "name": "📦 Бронзовый кейс",
        "price": 5000,
        "desc": "Начальный сундук с монетами и опытом",
        "drops": [
            {"type": "coins", "min": 1500, "max": 15000, "chance": 0.65},
            {"type": "coins", "min": 15000, "max": 30000, "chance": 0.25},
            {"type": "jackpot", "amount": 45000, "xp": 100, "chance": 0.10},
        ],
    },
    2: {
        "name": "🥈 Серебряный кейс",
        "price": 25000,
        "desc": "Ценный сундук с солидными кушами и шансом выиграть авто Lada Vesta",
        "drops": [
            {"type": "coins", "min": 10000, "max": 50000, "chance": 0.60},
            {"type": "coins", "min": 50000, "max": 120000, "chance": 0.25},
            {"type": "car", "car_id": "vesta", "car_name": "🚗 Lada Vesta Sport", "fallback_coins": 100000, "chance": 0.15},
        ],
    },
    3: {
        "name": "🥇 Золотой кейс",
        "price": 100000,
        "desc": "Элитный ларец с огромными суммами монет и спорткаром BMW M5",
        "drops": [
            {"type": "coins", "min": 60000, "max": 250000, "chance": 0.55},
            {"type": "coins", "min": 250000, "max": 600000, "chance": 0.25},
            {"type": "car", "car_id": "bmw", "car_name": "🏎 BMW M5 F90 Competition", "fallback_coins": 600000, "chance": 0.20},
        ],
    },
    4: {
        "name": "💎 Алмазный кейс",
        "price": 500000,
        "desc": "Легендарный сундук олигарха: гиперкары Porsche / Bugatti и до 3,000,000 🌑",
        "drops": [
            {"type": "coins", "min": 300000, "max": 1200000, "chance": 0.50},
            {"type": "coins", "min": 1200000, "max": 3000000, "chance": 0.30},
            {"type": "car", "car_id": "porsche", "car_name": "🚀 Porsche 911 Turbo S", "fallback_coins": 2000000, "chance": 0.12},
            {"type": "car", "car_id": "bugatti", "car_name": "👑 Bugatti Chiron Super Sport", "fallback_coins": 5000000, "chance": 0.08},
        ],
    },
}

QUIZ_QUESTIONS = [
    {"q": "В какой стране изобрели бумагу и порох?", "answers": ["китай", "в китае", "поднебесная"]},
    {"q": "Какая планета Солнечной системы ближе всего к Солнцу?", "answers": ["меркурий"]},
    {"q": "Сколько цветов в радуге?", "answers": ["7", "семь"]},
    {"q": "Какая столица у Австралии?", "answers": ["канберра"]},
    {"q": "Какой химический элемент обозначается символом Au?", "answers": ["золото", "аурум", "aurum"]},
    {"q": "Как зовут главного героя вселенной Ведьмак (The Witcher)?", "answers": ["геральт", "геральт из ривии"]},
    {"q": "Какая самая глубокая впадина в Мировом океане?", "answers": ["марианская", "марианская впадина"]},
    {"q": "Кто написал роман «Война и мир»?", "answers": ["толстой", "лев толстой"]},
    {"q": "Сколько граней у классического куба?", "answers": ["6", "шесть"]},
    {"q": "Какой единственный металл является жидким при комнатной температуре?", "answers": ["ртуть"]},
    {"q": "В каком году произошла авария на Чернобыльской АЭС?", "answers": ["1986", "1986 год"]},
    {"q": "Какое животное считается самым быстрым на суше?", "answers": ["гепард"]},
    {"q": "Столица Японии?", "answers": ["токио"]},
    {"q": "Какая река самая полноводная и длинная в мире?", "answers": ["амазонка", "нил"]},
    {"q": "Сколько секунд в одном часе?", "answers": ["3600"]},
    {"q": "В какой стране находятся великие пирамиды Гизы?", "answers": ["египет", "в египте"]},
    {"q": "Как называется естественный спутник Земли?", "answers": ["луна"]},
    {"q": "Сколько полос изображено на государственном флаге США?", "answers": ["13", "тринадцать"]},
    {"q": "Как зовут скандинавского бога грома с молотом Мьёльнир?", "answers": ["тор"]},
    {"q": "Какое животное изображено на логотипе суперкаров Ferrari и Porsche?", "answers": ["лошадь", "конь", "жеребец"]},
    {"q": "Какой газ преобладает в атмосфере Земли?", "answers": ["азот"]},
    {"q": "Сколько хромосом у здорового человека?", "answers": ["46", "сорок шесть"]},
    {"q": "В какой стране зародились Олимпийские игры?", "answers": ["греция", "в греции", "древняя греция"]},
    {"q": "Какая самая большая планета в Солнечной системе?", "answers": ["юпитер"]},
    {"q": "Как фамилия создателя Telegram и социальной сети ВКонтакте?", "answers": ["дуров", "павел дуров"]},
    {"q": "Сколько континентов на планете Земля?", "answers": ["6", "шесть"]},
    {"q": "Какой орган человека очищает кровь и производит желчь?", "answers": ["печень"]},
    {"q": "Как называется единица измерения электрического сопротивления?", "answers": ["ом"]},
    {"q": "Какой самый твёрдый природный минерал на Земле?", "answers": ["алмаз"]},
    {"q": "В каком году человек впервые полетел в космос?", "answers": ["1961", "1961 год"]},
    {"q": "Кто был первым человеком в космосе?", "answers": ["гагарин", "юрий гагарин"]},
    {"q": "Какая птица не умеет летать, но отлично плавает во льдах?", "answers": ["пингвин"]},
    {"q": "Как называется самая сильная шахматная фигура?", "answers": ["ферзь", "королева"]},
    {"q": "Какое море самое солёное на планете?", "answers": ["мёртвое", "мертвое", "мёртвое море"]},
    {"q": "Какое число получится, если возвести 2 в 10-ю степень?", "answers": ["1024"]},
]

BOTTLE_ACTIONS = [
    "Страстно поцеловать друг друга в щёчку 💋",
    "Обняться так крепко, чтобы захрустели рёбра 🤗",
    "Сказать самый безумный и романтичный комплимент в голосовом сообщении 🎙️",
    "Поставить парные аватарки в профиле на 24 часа 📸",
    "Перевести 2 500 🌑 монет на шоколадку («передать @юзер 2500») 🍫",
    "Признаться в тайной симпатии перед всей беседой 💖",
    "Придумать смешное милое прозвище и называть так целый день 🥰",
    "Станцевать победный танец и отправить кружочек или стикер в чат 💃",
    "Написать 3 факта, за что вы искренне уважаете этого человека ✨",
    "Сделать совместное предложение пожениться в боте («брак @юзер») 💍",
    "Подарить букет алых роз или мишку в боте («подарить 1 @юзер») 🌹",
    "Сыграть дружескую дуэль в кости на символические 500 монет 🎲",
]


# ═══════════════════════════════════════════════════════════════
# 🎹 КЛАВИАТУРА ВКОНТАКТЕ
# ═══════════════════════════════════════════════════════════════

def get_main_keyboard(is_chat: bool = False) -> str:
    kb = Keyboard(one_time=False, inline=False)
    if not is_chat:
        # 👑 РЯД 1: ЛИЧНЫЙ КАБИНЕТ И ЕЖЕДНЕВКА (Гармоничный изумрудный дуэт)
        kb.add(Text("👑 Профиль"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("🎁 Бонус"), color=KeyboardButtonColor.POSITIVE)
        kb.row()
        # 🏢 РЯД 2: ФИНАНСЫ И БИЗНЕС-ИМПЕРИЯ (Чистый контрастный белый/синий)
        kb.add(Text("🏦 Банк"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("🏢 Бизнесы"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("💼 Работы"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        # 🎰 РЯД 3: АЗАРТ, ЛУТ И СРАЖЕНИЯ (Энергичный рубиновый ряд адреналина)
        kb.add(Text("🎰 Казино"), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text("⚔️ Данжи"), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text("🐉 Босс"), color=KeyboardButtonColor.NEGATIVE)
        kb.row()
        # 🚗 РЯД 4: ФАРМ, КЕЙСЫ И АВТОСАЛОН (Чистый контрастный белый/синий)
        kb.add(Text("⛏ Шахта"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("📦 Кейсы"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("🚗 Гараж"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        # 📚 РЯД 5: НАВИГАЦИЯ И СООБЩЕСТВО (Меню + Главный CTA)
        kb.add(Text("📖 Все команды"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("➕ В беседу"), color=KeyboardButtonColor.POSITIVE)
    else:
        # 👑 ДЛЯ БЕСЕД (ЧАТОВ):
        # Ряд 1: Личный статус
        kb.add(Text("👑 Профиль"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("🎁 Бонус"), color=KeyboardButtonColor.POSITIVE)
        kb.row()
        # Ряд 2: Битвы и Азарт беседы (Рубиновый блок)
        kb.add(Text("🐉 Босс"), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text("⚔️ Дуэль"), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text("🎰 Казино"), color=KeyboardButtonColor.NEGATIVE)
        kb.row()
        # Ряд 3: Социальный интерактив беседы (Контрастный блок)
        kb.add(Text("💘 Пара дня"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("🍾 Бутылочка"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("🧠 Викторина"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        # Ряд 4: Кланы, Торги и Донат
        kb.add(Text("🏰 Клан"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("🔨 Аукцион"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("💎 Донат"), color=KeyboardButtonColor.POSITIVE)
        kb.row()
        # Ряд 5: Управление и Справка
        kb.add(Text("📖 Все команды"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("🛡 Модерация"), color=KeyboardButtonColor.POSITIVE)

    return kb.get_json()


# ═══════════════════════════════════════════════════════════════
# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

async def get_vk_user_info(user_id: int) -> tuple[str, str]:
    try:
        users = await bot.api.users.get(user_ids=[user_id])
        if users:
            u = users[0]
            return u.first_name, u.last_name
    except Exception as e:
        log.warning("Ошибка получения инфо о VK user %d: %s", user_id, e)
    return "Пользователь", ""

async def get_display_name(user_id: int) -> str:
    db_uid = to_db_uid(user_id)
    u_data = await db.get_user(db_uid)
    if u_data and u_data.get("nick"):
        return f"[id{user_id}|{u_data['nick']}]"
    fn, ln = await get_vk_user_info(user_id)
    return f"[id{user_id}|{fn}]"

async def sync_vk_user(user_id: int) -> dict:
    db_uid = to_db_uid(user_id)
    first_name, last_name = await get_vk_user_info(user_id)
    full_name = f"{first_name} {last_name}".strip()
    await db.ensure_user(db_uid, username=f"id{user_id}", first_name=full_name)
    user = await db.get_user(db_uid)
    return user or {}

def parse_amount(raw: str, max_val: int = 100_000_000) -> Optional[int]:
    s = (raw or "").strip().lower()
    if s in ("все", "всё", "all", "вабанк", "ва-банк"):
        return max_val
    s = s.replace(" ", "").replace(",", "").replace(".", "").replace("_", "")
    s = s.replace("k", "000").replace("к", "000").replace("m", "000000").replace("м", "000000").replace("кк", "000000")
    if s.isdigit():
        val = int(s)
        return val if val > 0 else None
    return None

def extract_target_vk_id(message: Message, text: str) -> Optional[int]:
    if message.reply_message and message.reply_message.from_id:
        return message.reply_message.from_id
    m = re.search(r"\[(?:id|club)(\d+)\|[^\]]+\]", text)
    if m:
        return int(m.group(1))
    m2 = re.search(r"@id(\d+)", text)
    if m2:
        return int(m2.group(1))
    return None

def clean_command_text(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^\[(?:club|public)\d+\|[^\]]+\][,:]?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^@(?:club|public)\d+[,:]?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^[/!]\s*", "", t)
    return t.strip()


# ═══════════════════════════════════════════════════════════════
# 🧠 ИИ-ОТВЕТЫ MOXXI (GEMINI AI + FALLBACK)
# ═══════════════════════════════════════════════════════════════

async def generate_moxxi_ai_reply(prompt: str, user_name: str) -> str:
    if AI_API_KEY:
        keys = [k.strip() for k in re.split(r"[,;\s]+", AI_API_KEY) if k.strip()]
        for k in keys:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={k}"
                sys_prompt = (
                    "Ты — Мокси (Moxxi), дерзкая, харизматичная, остроумная и заботливая девушка-маскот игрового бота ВКонтакте. "
                    "Тебя зовут ТОЛЬКО Мокси (Moxxi)! Категорически запрещено называть себя 'Фокси' или 'Foxxy' — ты именно МОКСИ! "
                    "Отвечай кратко (1-3 предложения), живо, с эмодзи и огоньком, поддерживай тему диалога, шути и будь дружелюбной к игроку. "
                    "ВКонтакте не поддерживает HTML-теги, поэтому категорически запрещено использовать теги, используй только обычный текст и эмодзи."
                )
                payload = {
                    "contents": [
                        {"role": "user", "parts": [{"text": f"{sys_prompt}\n\nПользователь {user_name} говорит: {prompt}"}]}
                    ]
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            ans = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                            if ans:
                                ans = re.sub(r"(?i)\bfoxxy\b", "Moxxi", ans)
                                ans = re.sub(r"(?i)\bфокси\b", "Мокси", ans)
                                ans = re.sub(r"</?[a-zA-Z0-9]+[^>]*>", "", ans).strip()
                                return ans
            except Exception:
                continue

    # Остроумный fallback
    fallbacks = [
        f"Хм, {user_name}, звучит интригующе! 😉 А что если проверить удачу в казино или пойти копать в шахту?",
        f"Ого, {user_name}! С такими вопросами тебе точно нужно ко мне в банду! 💖",
        f"Я тебя внимательно слушаю, {user_name}! Сегодня звёзды говорят, что нам обоим повезёт. ✨",
        f"Ахах, ну ты даёшь! За такое рассуждение держи виртуальный бокал в нашем баре Moxxi! 🍸"
    ]
    return random.choice(fallbacks)


# ═══════════════════════════════════════════════════════════════
# 🌉 ОМНИКАНАЛЬНЫЙ МОСТ В TELEGRAM
# ═══════════════════════════════════════════════════════════════

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not DISCORD_TOKEN:
    for p in [r"C:\Users\eiema\OneDrive\Desktop\MOXXI Support\.env", r"C:\Users\eiema\OneDrive\Desktop\moxxidc\.env"]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for l in f:
                        if l.startswith("DISCORD_BOT_TOKEN="):
                            DISCORD_TOKEN = l.split("=", 1)[1].strip()
                            break
            except Exception:
                pass


async def notify_telegram_about_ticket(ticket_id: int, user_id: int, user_name: str, question: str, category: str = "Общее"):
    if not TG_BOT_TOKEN:
        return
    admin_text = (
        f"🆘 🔔 <b>НОВОЕ ОБРАЩЕНИЕ ИЗ ВКОНТАКТЕ #{ticket_id}</b>\n"
        f"🌐 <b>Платформа:</b> 🔷 ВКонтакте\n"
        f"📂 <b>Категория:</b> {html.escape(category)}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"👤 <b>Пользователь:</b> {html.escape(user_name)}\n"
        f"🔗 <b>Ссылка:</b> https://vk.com/id{user_id}\n"
        f"🆔 <b>VK ID:</b> <code>{user_id}</code>\n\n"
        f"📝 <b>Вопрос / Суть:</b>\n«{html.escape(question)}»\n\n"
        f"💡 <b>Для ответа пользователю прямо из Telegram:</b>\n"
        f"• <code>+ответ {ticket_id} [текст вашего ответа]</code>\n"
        f"• <code>автоответ тикет {ticket_id} [1-5]</code>\n"
        f"• <code>закрыть тикет {ticket_id}</code>"
    )
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    hq_chat_id = None
    log_topic_id = None
    try:
        iris_db_path = os.path.join(os.path.dirname(_curr_dir), "бот2.0", "data", "iris.db")
        if os.path.exists(iris_db_path):
            import aiosqlite
            async with aiosqlite.connect(iris_db_path) as idb:
                async with idb.execute("SELECT key, value FROM staff_hq_settings WHERE key IN ('staff_hq_chat_id', 'staff_log_topic_id')") as cur:
                    for k, v in await cur.fetchall():
                        if k == 'staff_hq_chat_id' and v:
                            hq_chat_id = int(v)
                        elif k == 'staff_log_topic_id' and v:
                            log_topic_id = int(v)
    except Exception:
        pass

    targets = []
    if hq_chat_id:
        targets.append((hq_chat_id, log_topic_id))
    else:
        for rid in TG_OWNERS:
            targets.append((rid, None))

    async with aiohttp.ClientSession() as session:
        for cid, tid in targets:
            try:
                payload = {"chat_id": cid, "text": admin_text, "parse_mode": "HTML"}
                if tid:
                    payload["message_thread_id"] = tid
                await session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5))
            except Exception as e:
                log.warning("Ошибка отправки в Telegram: %s", e)


async def notify_discord_about_ticket(ticket_id: int, user_id: int, user_name: str, question: str, category: str = "Общее"):
    if not DISCORD_TOKEN:
        return
    queue_ch_id = 1569227215160221797
    payload = {
        "embeds": [
            {
                "title": f"🎫 ОБРАЩЕНИЕ ИЗ VK • #{ticket_id} [{category}]",
                "description": (
                    f"👤 **Пользователь:** `{user_name}` (VK ID: `{user_id}`)\n"
                    f"🔗 **Профиль VK:** https://vk.com/id{user_id}\n"
                    f"📱 **Платформа:** `🔷 ВКонтакте`\n"
                    f"📂 **Категория:** `{category}`\n"
                    f"⏱ **Время:** <t:{int(time.time())}:R>\n\n"
                    f"───────────────────────────────\n"
                    f"📝 **Вопрос / Суть обращения:**\n{question[:1500]}\n"
                    f"───────────────────────────────"
                ),
                "color": 298495,
                "footer": {"text": "MOXXI Omnichannel Desk • ВКонтакте ⇄ Discord"}
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 3,
                        "label": "✋ Взять тикет",
                        "custom_id": f"st_omni_claim:{ticket_id}",
                        "emoji": {"name": "💬"}
                    }
                ]
            }
        ]
    }
    url = f"https://discord.com/api/v10/channels/{queue_ch_id}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5))
        except Exception as e:
            log.warning("Ошибка отправки тикета VK в Discord: %s", e)


# ═══════════════════════════════════════════════════════════════
# 🎮 ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ВКОНТАКТЕ
# ═══════════════════════════════════════════════════════════════

@bot.on.message()
async def vk_message_handler(message: Message):
    # Приветствие при входе в беседу
    if message.action:
        act = message.action
        if act.type in ("chat_invite_user", "chat_invite_user_by_link"):
            chat_id = message.peer_id
            custom_welcome = await db.get_chat_setting(chat_id, "welcome_text", "")
            if custom_welcome:
                return await message.answer(custom_welcome)
            inv_name, _ = await get_vk_user_info(act.member_id or message.from_id)
            return await message.answer(
                f"👋 Приветствуем, [id{act.member_id or message.from_id}|{inv_name}], в нашей беседе!\n"
                f"🌟 Здесь живёт бот MOXXI 3.0. Напиши «помощь», чтобы узнать все команды!"
            )

    if not message.text:
        return

    user_id = message.from_id
    if user_id <= 0:
        return

    is_chat = message.peer_id > 2000000000
    clean_txt = clean_command_text(message.text)
    if not clean_txt:
        return

    # Локальные триггеры беседы
    if is_chat:
        trigger_reply = await db.find_chat_trigger_answer(message.peer_id, clean_txt)
        if trigger_reply:
            return await message.answer(trigger_reply)

    # ИИ-собеседник при явном обращении к Мокси
    ai_match = re.match(r"^(?:мокси|moxxi|бот)[,:]?\s*(.+)$", clean_txt, flags=re.IGNORECASE)
    parts = clean_txt.split()
    first_token = parts[0]
    if not re.search(r"[a-zA-Zа-яА-ЯёЁ0-9]", first_token) and not first_token.startswith(("+", "-", "!")) and len(parts) > 1:
        cmd = parts[1].lower()
        args = clean_txt[len(parts[0]):].strip()[len(parts[1]):].strip()
    else:
        clean_no_emoji = re.sub(r"^[^\w\s\+\-]+", "", clean_txt).strip()
        p = clean_no_emoji.split()
        cmd = p[0].lower() if p else ""
        args = clean_no_emoji[len(cmd):].strip()

    # Снимаем префикс бот, если это команда
    if cmd in ("бот", "мокси", "moxxi") and args:
        sub_p = args.split()
        cmd = sub_p[0].lower()
        args = args[len(sub_p[0]):].strip()

    log.info("Входящее сообщение: user_id=%d, peer_id=%d, raw='%s' -> cmd='%s', args='%s'", user_id, message.peer_id, message.text, cmd, args)

    user_db = await sync_vk_user(user_id)
    db_uid = to_db_uid(user_id)
    db_cid = to_db_cid(message.peer_id)
    user_display = await get_display_name(user_id)
    my_rank = await get_effective_rank(message.peer_id, user_id)

    # Чат-викторина: проверка правильного ответа в беседе
    if is_chat and message.peer_id in ACTIVE_QUIZZES:
        quiz = ACTIVE_QUIZZES[message.peer_id]
        if time.time() - quiz["ts"] <= 90:
            user_ans = clean_txt.strip().lower()
            if any(user_ans == a or user_ans.endswith(a) for a in quiz["answers"]):
                del ACTIVE_QUIZZES[message.peer_id]
                q_reward = quiz.get("reward", 5000)
                await db.add_balance(db_uid, q_reward)
                await db.add_xp(db_uid, 40)
                ans_display = quiz["answers"][0].capitalize()
                return await message.answer(
                    f"🎉 ВЕРНО! {user_display} первым дал правильный ответ: «{ans_display}»!\n"
                    f"💰 Награда: +{q_reward:,} 🌑 и +40 XP зачислены на баланс!"
                )
        else:
            del ACTIVE_QUIZZES[message.peer_id]

    # Ограничение КПЗ: арестованные не могут грабить, играть в казино и фармить
    jail_left = await db.is_in_jail(db_uid)
    if jail_left > 0 and cmd in (
        "казино", "слоты", "рулетка", "21", "блэкджек", "краш",
        "шахта", "копать", "рыбалка", "дуэль", "кости", "ограбить", "украсть"
    ):
        jm = jail_left // 60
        js = jail_left % 60
        return await message.answer(
            f"🚨 ВЫ НАХОДИТЕСЬ В КПЗ!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👮 Вы арестованы полицией за преступную деятельность!\n"
            f"⏳ До окончания срока: {jm} мин {js} сек\n\n"
            f"🔓 Доступные действия:\n"
            f"• «побег» — попытка скрыться через вентиляцию (шанс 30%)\n"
            f"• «залог @юзер» — друг на свободе может внести выкуп 10 000 🌑"
        )

    # 🌟 ОБРАБОТЧИК РАСШИРЕННЫХ СИСТЕМ (400+ КОМАНД)
    ext_handled = await extended.handle_extended_command(
        message=message,
        cmd=cmd,
        args=args,
        user_id=user_id,
        db_uid=db_uid,
        db_cid=db_cid,
        is_chat=is_chat,
        user_display=user_display,
        my_rank=my_rank,
        get_vk_user_info_func=get_vk_user_info,
        extract_target_func=extract_target_vk_id
    )
    if ext_handled:
        return

    # ═══════════════════════════════════════════════════════════
    # 1. ❓ МЕНЮ, СПРАВКА И ПОМОЩЬ (415+ КОМАНД, 12 РАЗДЕЛОВ)
    # ═══════════════════════════════════════════════════════════
    import commands_catalog
    _c_low = clean_txt.lower()
    _a_low = args.lower().strip()

    _is_help_cmd = cmd in ("старт", "начать", "помощь", "меню", "хелп", "команды", "help", "команда")
    _is_nav_num = cmd in [f"{i}." for i in range(1, 13)] or cmd in [str(i) for i in range(1, 13)]
    _is_section_word = cmd in ("раздел", "разделы")
    _is_all_sections = (cmd in ("все", "всё") and ("раздел" in _a_low or "команд" in _a_low))
    _is_search = cmd in ("найти", "поиск", "искать", "поиск_команд", "search")
    _is_nav_text = any(phrase in _c_low for phrase in (
        "модерация", "баны/варны", "настройки", "экономика", "бизнесы/дома",
        "казино/игры", "данжи/фарм", "квесты/vip", "кланы/боссы", "семья/кпз",
        "рп романтика", "рп боевые", "все разделы"
    ))

    if _is_help_cmd or _is_nav_num or _is_section_word or _is_all_sections or _is_search or _is_nav_text:
        # Поиск по каталогу всех 415+ команд
        if _is_search or (cmd in ("команды", "помощь") and (_a_low.startswith("найти ") or _a_low.startswith("поиск "))):
            search_query = args
            if _a_low.startswith("найти ") or _a_low.startswith("поиск "):
                search_query = _a_low.split(maxsplit=1)[1]
            sq_clean = search_query.strip().lower()
            if not sq_clean or sq_clean in ("команд", "команда", "команды"):
                guide_txt = (
                    "🔍 ПОИСК ПО БАЗЕ ВСЕХ 414+ КОМАНД MOXXI 3.0:\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💡 Напишите в чат: «найти [слово]»\n\n"
                    "Например:\n"
                    "• «найти брак» — свадьбы, разводы, семья\n"
                    "• «найти бизнес» — предприятия и доход\n"
                    "• «найти босс» — рейдовые боссы и атаки\n"
                    "• «найти бан» — наказания и модерация\n"
                    "• «найти казино» — рулетка, 21, краш, слоты\n"
                    "• «найти клан» — кланы, казна, войны"
                )
                return await message.answer(guide_txt, keyboard=commands_catalog.get_hub_keyboard())
            return await message.answer(commands_catalog.search_commands(search_query), keyboard=commands_catalog.get_hub_keyboard())

        # Нажатие на "Все разделы" / "Все команды" или возврат в главное меню
        elif "все разделы" in _c_low or "все_разделы" in _c_low or "все команды" in _c_low or (cmd in ("все", "всё") and ("раздел" in _a_low or "команд" in _a_low)):
            return await message.answer(commands_catalog.get_hub_text(), keyboard=commands_catalog.get_hub_keyboard())

        # Полный дамп всех 12 разделов сразу
        elif _a_low in ("все", "всё", "all") or _a_low.startswith("все ") or _a_low.startswith("всё "):
            for s_idx in range(1, 12):
                await message.answer(commands_catalog.get_section_text(s_idx))
                await asyncio.sleep(0.3)
            return await message.answer(commands_catalog.get_section_text(12), keyboard=commands_catalog.get_hub_keyboard())

        else:
            # Определение номера раздела 1..12
            sec_found = None
            for num in range(1, 13):
                if cmd in (f"{num}.", str(num)):
                    sec_found = num
                    break
                if _a_low.startswith(str(num)):
                    sec_found = num
                    break

            if not sec_found:
                if "модерация" in _c_low: sec_found = 1
                elif "бан" in _c_low or "варн" in _c_low: sec_found = 2
                elif "настройк" in _c_low or "чистк" in _c_low: sec_found = 3
                elif "эконом" in _c_low or "банк" in _c_low: sec_found = 4
                elif "бизнес" in _c_low or "дом" in _c_low: sec_found = 5
                elif "казино" in _c_low or "игр" in _c_low: sec_found = 6
                elif "данж" in _c_low or "фарм" in _c_low or "шахт" in _c_low: sec_found = 7
                elif "квест" in _c_low or "ачив" in _c_low or "vip" in _c_low: sec_found = 8
                elif "клан" in _c_low or "босс" in _c_low: sec_found = 9
                elif "семь" in _c_low or "кпз" in _c_low or "брак" in _c_low: sec_found = 10
                elif "романтик" in _c_low: sec_found = 11
                elif "боев" in _c_low or "дерзк" in _c_low: sec_found = 12

            if sec_found:
                return await message.answer(commands_catalog.get_section_text(sec_found), keyboard=commands_catalog.get_section_keyboard(sec_found))
            else:
                return await message.answer(commands_catalog.get_hub_text(), keyboard=commands_catalog.get_hub_keyboard())

    # ➕ ДОБАВЛЕНИЕ В БЕСЕДУ
    if (cmd == "в" and args in ("беседу", "беседы", "группу", "чат")) or cmd in ("добавить", "инвайт", "invite", "беседа", "беседу", "пригласить", "в_беседу", "вбеседу"):
        invite_kb = Keyboard(inline=True)
        invite_kb.add(OpenLink("https://vk.com/club243066051", "➕ Добавить в беседу"))
        return await message.answer(
            "🌟 КАК ДОБАВИТЬ MOXXI 3.0 В СВОЮ БЕСЕДУ:\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1. Нажмите на кнопку «➕ Добавить в беседу» ниже или перейдите по ссылке: vk.com/club243066051\n"
            "2. В меню сообщества выберите «Добавить в беседу» и укажите нужный чат\n"
            "3. Выдайте боту права Администратора, чтобы работали игры, ранги (1-10) и автокик нарушителей!\n\n"
            "🎮 После добавления напишите в беседе «старт» или «команды»!",
            keyboard=invite_kb.get_json()
        )

    # ═══════════════════════════════════════════════════════════
    # 2. 👑 СИСТЕМА РАНГОВ (1–10)
    # ═══════════════════════════════════════════════════════════
    if cmd in ("состав", "стафф", "админы", "модераторы", "staff", "admins", "сетка"):
        if not is_chat:
            return await message.answer("Состав администрации доступен только в беседах!")
        staff_rows = await db.get_chat_staff_list(db_cid)
        staff_by_rank: dict[int, list[str]] = {r: [] for r in range(10, 0, -1)}
        seen_users = set()
        for sr in staff_rows:
            uid = from_db_uid(sr["user_id"])
            rnk = sr["rank"]
            if rnk in staff_by_rank:
                tag = await get_display_name(uid)
                staff_by_rank[rnk].append(tag)
                seen_users.add(uid)

        try:
            conv_members = await bot.api.messages.get_conversation_members(peer_id=message.peer_id)
            for m in conv_members.items:
                mid = m.member_id
                if mid > 0 and mid not in seen_users:
                    if getattr(m, "is_owner", False):
                        tag = await get_display_name(mid)
                        staff_by_rank[10].append(tag)
                        seen_users.add(mid)
                    elif getattr(m, "is_admin", False):
                        tag = await get_display_name(mid)
                        staff_by_rank[5].append(tag)
                        seen_users.add(mid)
        except Exception:
            pass

        lines = ["👥 СОСТАВ АДМИНИСТРАЦИИ БЕСЕДЫ 👥", "━━━━━━━━━━━━━━━━━━━━"]
        total_staff = sum(len(v) for v in staff_by_rank.values())
        if total_staff == 0:
            lines.append("В этой беседе пока нет назначенных модераторов.")
        else:
            for r in range(10, 0, -1):
                m_list = staff_by_rank[r]
                if m_list:
                    icon = RANK_ICONS.get(r, "⭐")
                    title = RANK_NAMES.get(r, f"Ранг {r}")
                    lines.append(f"{icon} {title} [{r}]:")
                    for m_tag in m_list:
                        lines.append(f"  • {m_tag}")
                    lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 Всего сотрудников: {total_staff}")
        return await message.answer("\n".join(lines))

    if cmd in ("ранг", "мойранг", "мой_ранг", "rank"):
        target_id = extract_target_vk_id(message, args) or user_id
        t_rank = await get_effective_rank(message.peer_id, target_id)
        tg_name = await get_display_name(target_id)
        icon = RANK_ICONS.get(t_rank, "👤")
        title = RANK_NAMES.get(t_rank, "Участник")
        return await message.answer(f"{icon} Ранг {tg_name} в этой беседе: [{t_rank}] {title}.")

    if cmd in ("повысить", "+ранг", "ранг+", "up"):
        if not is_chat:
            return await message.answer("Команда доступна только в беседах!")
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите пользователя ответом или через @упоминание!")
        target_rank = await get_effective_rank(message.peer_id, target_id)
        if my_rank <= target_rank:
            return await message.answer(f"⛔️ Вы не можете повысить пользователя с рангом [{target_rank}], равным или выше вашего ([{my_rank}])!")
        if target_rank + 1 >= my_rank:
            return await message.answer(f"⛔️ Вы не можете повысить пользователя до своего ранга [{my_rank}] или выше!")
        if target_rank >= 10:
            return await message.answer("⚠️ У пользователя уже максимальный ранг (10)!")
        new_rank = target_rank + 1
        await db.set_user_rank(db_cid, to_db_uid(target_id), new_rank, granted_by=db_uid)
        tg_name = await get_display_name(target_id)
        return await message.answer(f"🎉 {tg_name} повышен(а) до ранга [{new_rank}] {RANK_NAMES[new_rank]} {RANK_ICONS[new_rank]}!\n👨‍💻 Назначил: {user_display}")

    if cmd in ("понизить", "-ранг", "ранг-", "down"):
        if not is_chat:
            return await message.answer("Команда доступна только в беседах!")
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите пользователя ответом или через @упоминание!")
        target_rank = await get_effective_rank(message.peer_id, target_id)
        if my_rank <= target_rank:
            return await message.answer(f"⛔️ Вы не можете понизить пользователя с рангом [{target_rank}], равным или выше вашего ([{my_rank}])!")
        if target_rank <= 0:
            return await message.answer("⚠️ У пользователя уже минимальный ранг (0 - Участник)!")
        new_rank = target_rank - 1
        await db.set_user_rank(db_cid, to_db_uid(target_id), new_rank, granted_by=db_uid)
        tg_name = await get_display_name(target_id)
        return await message.answer(f"🔻 {tg_name} понижен(а) до ранга [{new_rank}] {RANK_NAMES[new_rank]} {RANK_ICONS[new_rank]}!\n👨‍💻 Изменил: {user_display}")

    if cmd in ("назначить", "setrank"):
        if not is_chat:
            return await message.answer("Команда доступна только в беседах!")
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Формат: «назначить @юзер [1-10]»")
        clean_args = re.sub(r"\[(?:id|club)\d+\|[^\]]+\]", "", args).strip()
        num_m = re.search(r"\b(\d+)\b", clean_args)
        if not num_m:
            return await message.answer("Укажите ранг от 0 до 10! Пример: «назначить @юзер 3»")
        req_rank = int(num_m.group(1))
        if req_rank < 0 or req_rank > 10:
            return await message.answer("Номер ранга должен быть от 0 до 10!")
        target_rank = await get_effective_rank(message.peer_id, target_id)
        if my_rank <= target_rank:
            return await message.answer("⛔️ Вы не можете изменять ранг равного или старшего!")
        if req_rank >= my_rank:
            return await message.answer(f"⛔️ Вы можете назначать ранги строго ниже своего (максимум [{my_rank - 1}])!")
        await db.set_user_rank(db_cid, to_db_uid(target_id), req_rank, granted_by=db_uid)
        tg_name = await get_display_name(target_id)
        return await message.answer(f"✅ Пользователю {tg_name} установлен ранг: [{req_rank}] {RANK_NAMES[req_rank]} {RANK_ICONS[req_rank]}!\n👨‍💻 Назначил: {user_display}")

    if cmd in ("снять", "разжаловать", "демоут"):
        if not is_chat:
            return await message.answer("Команда доступна только в беседах!")
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите пользователя ответом или через @упоминание!")
        target_rank = await get_effective_rank(message.peer_id, target_id)
        if my_rank <= target_rank:
            return await message.answer("⛔️ Вы не можете снять пользователя равного или старшего по рангу!")
        await db.set_user_rank(db_cid, to_db_uid(target_id), 0, granted_by=db_uid)
        tg_name = await get_display_name(target_id)
        return await message.answer(f"🚫 {tg_name} снят(а) со всех должностей администрации беседы.")

    # ═══════════════════════════════════════════════════════════
    # 3. 🏰 КЛАНЫ И БАНДЫ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("создать_клан", "создатьклан"):
        if not args:
            return await message.answer("Укажите название клана! Пример: «создать_клан Семья» (Стоимость: 50 000 🌑).")
        cur_bal = user_db.get("balance", 0)
        if cur_bal < 50000:
            return await message.answer(f"❌ Создание клана стоит 50 000 🌑! У вас: {cur_bal:,} 🌑.")
        existing_clan = await db.get_user_clan(db_uid)
        if existing_clan:
            return await message.answer("❌ Вы уже состоите в клане! Сначала покиньте старый.")
        await db.add_balance(db_uid, -50000)
        c_id = await db.create_clan(args.strip()[:30], db_uid)
        return await message.answer(f"👑 Поздравляем! Вы создали клан «{args.strip()[:30]}» (ID: {c_id})!")

    if cmd in ("клан", "clan"):
        u_clan = await db.get_user_clan(db_uid)
        if not u_clan:
            return await message.answer("Вы пока не состоите в клане. Создайте свой: «создать_клан [название]» или вступите в существующий: «вступить [id]»!")
        m_count = await db.get_clan_members_count(u_clan["id"])
        owner_name = await get_display_name(from_db_uid(u_clan["owner_id"]))
        ans = (
            f"🏰 КЛАН: {u_clan['name']} (ID: {u_clan['id']})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 Лидер клана: {owner_name}\n"
            f"👥 Участников: {m_count}\n"
            f"💰 Казна клана: {u_clan.get('balance', 0):,} 🌑\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Пополнить казну: «казна [сумма]»\n"
            f"🚪 Покинуть клан: «покинуть_клан»"
        )
        return await message.answer(ans)

    if cmd in ("вступить", "вступить_в_клан", "join_clan"):
        if not args or not args.isdigit():
            return await message.answer("Укажите ID клана! Пример: «вступить 1» (Список кланов: «кланы»).")
        target_cid = int(args)
        clan = await db.get_clan(target_cid)
        if not clan:
            return await message.answer("❌ Клан с таким ID не найден!")
        existing_clan = await db.get_user_clan(db_uid)
        if existing_clan:
            return await message.answer("❌ Вы уже состоите в клане! Сначала напишите: «покинуть_клан».")
        await db.join_clan(target_cid, db_uid)
        return await message.answer(f"🎉 Вы успешно вступили в клан «{clan['name']}»!")

    if cmd in ("покинуть_клан", "выйти_из_клана"):
        u_clan = await db.get_user_clan(db_uid)
        if not u_clan:
            return await message.answer("Вы не состоите в клане.")
        await db.leave_clan(db_uid)
        return await message.answer(f"🚪 Вы покинули клан «{u_clan['name']}».")

    if cmd in ("казна", "пополнить_казну"):
        u_clan = await db.get_user_clan(db_uid)
        if not u_clan:
            return await message.answer("Вы не состоите в клане.")
        amount = parse_amount(args, max_val=user_db.get("balance", 0))
        if not amount or amount <= 0:
            return await message.answer("Укажите сумму для пополнения казны! Пример: «казна 5000»")
        if user_db.get("balance", 0) < amount:
            return await message.answer("❌ Недостаточно монет на балансе!")
        await db.add_balance(db_uid, -amount)
        await db.add_clan_balance(u_clan["id"], amount)
        return await message.answer(f"💰 {user_display} пополнил(а) казну клана «{u_clan['name']}» на +{amount:,} 🌑!")

    if cmd in ("кланы", "топ_кланов"):
        top_c = await db.get_top_clans(10)
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = ["🏰 ТОП КЛАНОВ ПО КАЗНЕ 🏰", "━━━━━━━━━━━━━━━━━━━━"]
        if not top_c:
            lines.append("Кланы ещё не созданы. Станьте первым!")
        for idx, c in enumerate(top_c):
            m = medals[idx] if idx < len(medals) else f"{idx+1}."
            lines.append(f"{m} {c['name']} (ID: {c['id']}) — {c['balance']:,} 🌑 (👥 {c['members_count']})")
        return await message.answer("\n".join(lines))

    # ═══════════════════════════════════════════════════════════
    # 4. 💍 СВАДЬБЫ, БРАКИ И ДЕТИ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("брак", "свадьба", "семья"):
        sub = args.lower().strip()
        marry_key = f"{user_id}"

        if sub in ("согласиться", "принять", "да", "yes"):
            req = active_marriages.get(marry_key)
            if not req:
                return await message.answer("❌ У вас нет активных предложений руки и сердца!")
            partner_id = req["proposer_id"]
            active_marriages.pop(marry_key, None)
            rel_id = await db.create_marriage(to_db_uid(partner_id), db_uid)
            p_name = await get_display_name(partner_id)
            ans = (
                f"💍 💖 ГОРЬКО! СВАДЬБА СОСТОЯЛАСЬ! 💖 💍\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"В нашей беседе родилась новая прекрасная семья:\n"
                f"{p_name} 👰+🤵 {user_display}!\n\n"
                f"🎉 Поздравляем молодожёнов! Теперь вы можете завести ребёнка: «завести_ребенка [имя] мальчик/девочка»!"
            )
            return await message.answer(ans)

        if sub in ("отказаться", "отклонить", "нет"):
            if marry_key in active_marriages:
                active_marriages.pop(marry_key, None)
                return await message.answer("💔 Вы отклонили предложение руки и сердца.")
            return await message.answer("У вас нет предложений.")

        # Просмотр своего брака
        m_info = await db.get_marriage(db_uid)
        if not args or args in ("статус", "инфо", "профиль"):
            if not m_info:
                return await message.answer("Вы пока не в браке. Сделать предложение: «брак @юзер»!")
            partner_db_uid = m_info["user2_id"] if m_info["user1_id"] == db_uid else m_info["user1_id"]
            p_vk_id = from_db_uid(partner_db_uid)
            p_name = await get_display_name(p_vk_id)
            days = (int(time.time()) - m_info["created_at"]) // 86400
            child = await db.get_child(m_info["id"])
            child_str = f"\n🍼 Ребёнок: {child['name']} ({'мальчик' if child['gender']=='m' else 'девочка'}, сытость {child['satiety']}%)" if child else "\n🍼 Детей пока нет."
            ans = (
                f"💖 СЕМЕЙНЫЙ СОЮЗ 💖\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💑 Супруги: {user_display} 💕 {p_name}\n"
                f"⏳ В браке: {days} дн.\n"
                f"⭐ Уровень любви: {m_info.get('level', 1)} ({m_info.get('xp', 0)} XP)"
                f"{child_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Чтобы развестись: «развод»"
            )
            return await message.answer(ans)

        # Отправка предложения
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите избранника(цу) ответом или через @упоминание!")
        if m_info:
            return await message.answer("❌ Вы уже состоите в браке! Сначала оформите развод.")
        t_marriage = await db.get_marriage(to_db_uid(target_id))
        if t_marriage:
            return await message.answer("❌ Этот человек уже состоит в браке!")

        active_marriages[str(target_id)] = {"proposer_id": user_id, "expire_ts": time.time() + 120}
        tg_name = await get_display_name(target_id)
        msg_prop = (
            f"💍 {user_display} встаёт на одно колено и делает предложение руки и сердца {tg_name}!\n\n"
            f"👉 Чтобы согласиться: «брак согласиться» (или «брак отказаться»)."
        )
        return await message.answer(msg_prop)

    if cmd in ("развод", "развестись"):
        ok = await db.divorce(db_uid)
        if ok:
            return await message.answer(f"💔 {user_display} официально оформил(а) развод. Вы снова свободны.")
        return await message.answer("Вы не состоите в браке.")

    if cmd in ("завести_ребенка", "завестиребенка"):
        m_info = await db.get_marriage(db_uid)
        if not m_info:
            return await message.answer("❌ Завести ребёнка можно только находясь в браке!")
        existing_child = await db.get_child(m_info["id"])
        if existing_child:
            return await message.answer(f"У вас уже есть ребёнок по имени {existing_child['name']}!")
        p = args.split()
        if len(p) < 2:
            return await message.answer("Формат: «завести_ребенка [Имя] [мальчик/девочка]»\nПример: «завести_ребенка Максим мальчик»")
        c_name = p[0].strip()
        gender = "m" if "мал" in p[1].lower() else "f"
        await db.create_child(m_info["id"], c_name, gender)
        icon = "👦" if gender == "m" else "👧"
        return await message.answer(f"🍼 Чудо произошло! У вашей пары родился {icon} {c_name}!\nЗаботьтесь о нём: «покормить_ребенка», «поиграть_с_ребенком».")

    if cmd in ("покормить_ребенка", "покормитьребенка"):
        m_info = await db.get_marriage(db_uid)
        if not m_info:
            return await message.answer("Вы не в браке.")
        child = await db.get_child(m_info["id"])
        if not child:
            return await message.answer("У вашей пары ещё нет ребёнка.")
        await db.feed_child(child["id"])
        return await message.answer(f"🍼 {user_display} покормил(а) малыша {child['name']} вкусной кашей! Сытость восстановлена (+20 XP).")

    if cmd in ("поиграть_с_ребенком", "поигратьсребенком"):
        m_info = await db.get_marriage(db_uid)
        if not m_info:
            return await message.answer("Вы не в браке.")
        child = await db.get_child(m_info["id"])
        if not child:
            return await message.answer("У вашей пары ещё нет ребёнка.")
        await db.play_child(child["id"])
        return await message.answer(f"🧸 {user_display} весело поиграл(а) с {child['name']}! Настроение малыша на максимуме (+25 XP).")

    # ═══════════════════════════════════════════════════════════
    # 5. 🐉 РЕЙДОВЫЕ БОССЫ БЕСЕДЫ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("босс", "boss"):
        if not is_chat:
            return await message.answer("Рейдовые боссы доступны только в беседах!")
        boss = await db.get_chat_boss(db_cid)
        if not boss:
            return await message.answer(
                "😴 В этой беседе сейчас нет активного босса!\n"
                "Вы можете призвать его командой: «призвать босса»!"
            )
        percent = int((boss["current_hp"] / boss["max_hp"]) * 100)
        ans = (
            f"{boss['boss_icon']} РЕЙДОВЫЙ БОСС: {boss['boss_name']} (Ур. {boss['boss_level']})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Здоровье: {boss['current_hp']:,} / {boss['max_hp']:,} HP ({percent}%)\n"
            f"💰 Награда за победу: {boss['reward_pool']:,} 🌑\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ Чтобы нанести удар, напишите: «атака» (или «ударить босса»)\n"
            f"🏆 Топ урона: «топ урона»"
        )
        return await message.answer(ans)

    if cmd in ("призвать_босса", "призватьбосса", "спавн_босса"):
        if not is_chat:
            return await message.answer("Боссов можно призывать только в беседах!")
        existing_b = await db.get_chat_boss(db_cid)
        if existing_b:
            return await message.answer(f"Босс {existing_b['boss_name']} уже в беседе! Напишите «босс» или «атака».")
        bosses = [
            ("Древний Дракон Пустоты", "🐲", 1, 50000, 150000),
            ("Кибернетический Голем", "🤖", 2, 80000, 250000),
            ("Владыка Тьмы и Хаоса", "👿", 3, 120000, 400000),
        ]
        b_name, b_icon, b_lvl, b_hp, b_pool = random.choice(bosses)
        await db.spawn_chat_boss(db_cid, b_name, b_icon, b_lvl, b_hp, b_pool)
        ans = (
            f"🚨 ⚠️ В БЕСЕДЕ ПОЯВИЛСЯ РЕЙДОВЫЙ БОСС! ⚠️ 🚨\n\n"
            f"{b_icon} {b_name} пробудился с {b_hp:,} HP!\n"
            f"💰 Общий призовой фонд победы: {b_pool:,} 🌑!\n\n"
            f"⚔️ Объединяйтесь с участниками и бейте его: «атака»!"
        )
        return await message.answer(ans)

    if cmd in ("атака", "ударить", "ударить_босса", "hit"):
        if not is_chat:
            return await message.answer("Атака босса доступна только в беседах!")
        boss = await db.get_chat_boss(db_cid)
        if not boss:
            return await message.answer("Босса сейчас нет. Напишите «призвать босса»!")

        cd = await db.cooldown_left(db_uid, f"boss_hit_{db_cid}", 25)
        if cd > 0:
            return await message.answer(f"⏳ Оружие перезаряжается! Следующий удар через {cd} сек.")

        await db.set_cooldown(db_uid, f"boss_hit_{db_cid}", 25)
        dmg = random.randint(400, 1600)
        is_crit = random.random() < 0.20
        if is_crit:
            dmg = int(dmg * 2.2)

        new_hp, is_dead, dmg_dealt = await db.attack_chat_boss(db_cid, db_uid, dmg)
        crit_str = " 🔥 КРИТИЧЕСКИЙ УДАР x2.2!" if is_crit else ""

        if is_dead:
            # Награждение участников рейда
            ranking = await db.get_boss_ranking(db_cid)
            pool = boss["reward_pool"]
            total_dmg = sum(r["damage"] for r in ranking) or 1
            reward_lines = []
            for r in ranking[:5]:
                share = r["damage"] / total_dmg
                payout = max(1000, int(pool * share))
                await db.add_balance(r["user_id"], payout)
                u_tag = await get_display_name(from_db_uid(r["user_id"]))
                reward_lines.append(f"• {u_tag}: нанёс {r['damage']:,} урона ➔ +{payout:,} 🌑")

            ans_dead = (
                f"🎉 💀 БОСС {boss['boss_name']} ПОВЕРЖЕН! 💀 🎉\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Решающий добивающий удар нанёс {user_display}!\n\n"
                f"💰 РАСПРЕДЕЛЕНИЕ НАГРАДЫ ({pool:,} 🌑):\n"
                + "\n".join(reward_lines)
            )
            return await message.answer(ans_dead)

        ans_hit = (
            f"⚔️ {user_display} нанёс {dmg_dealt:,} урона боссу!{crit_str}\n"
            f"❤️ У босса осталось: {new_hp:,} / {boss['max_hp']:,} HP."
        )
        return await message.answer(ans_hit)

    # ═══════════════════════════════════════════════════════════
    # 6. 🏢 БИЗНЕСЫ И ПАССИВНЫЙ ДОХОД
    # ═══════════════════════════════════════════════════════════
    if cmd in ("бизнесы", "бизнес", "предприятия"):
        sub = args.lower().strip()
        if sub in ("собрать", "прибыль", "доход"):
            profit = await db.collect_business_profit(db_uid)
            if profit > 0:
                return await message.answer(f"💰 {user_display}, вы собрали накопившуюся прибыль с предприятий: +{profit:,} 🌑!")
            return await message.answer("Прибыль ещё не накопилась (начисления производятся раз в час, до 24ч).")

        user_xp = user_db.get("xp", 0)
        user_level = max(1, user_xp // 100)

        # Парсим номер страницы
        page = 1
        page_m = re.search(r"\b([1-5])\b", args)
        if page_m:
            page = int(page_m.group(1))

        u_biz = await db.get_user_businesses(db_uid)
        lines = [
            f"🏢 ИМПЕРИЯ ПРЕДПРИЯТИЙ MOXXI 🏢",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"👤 Владелец: {user_display}",
            f"⭐ Ваш уровень: {user_level} Lvl ({user_xp} XP)",
        ]

        if u_biz:
            total_daily = 0
            lines.append("━━━━━━━━━━━━━━━━━━━━")
            lines.append("💼 Ваши предприятия во владении:")
            for b in u_biz:
                k = b["biz_key"]
                real_k = db.BIZ_ALIASES.get(k, k)
                if real_k in db.BIZ_CATALOG:
                    b_info = db.BIZ_CATALOG[real_k]
                    inc = b_info["daily_income"] * b["count"]
                    total_daily += inc
                    lines.append(f"• {b_info['name']} (x{b['count']}) ➔ доход: +{inc:,} 🌑/день")
            lines.append(f"📈 Суммарная прибыль: +{total_daily:,} 🌑/день")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📦 Каталог предприятий (Стр. {page}/5):")

        # 40 бизнесов делим по 8 на страницу
        all_items = list(db.BIZ_CATALOG.items())
        start_idx = (page - 1) * 8
        end_idx = min(len(all_items), start_idx + 8)

        for idx in range(start_idx, end_idx):
            k, info = all_items[idx]
            num = idx + 1
            status_ico = "✅" if user_level >= info["req_lvl"] else f"🔒 Требуется Lvl {info['req_lvl']}"
            lines.append(f"{num}. {info['name']} — {info['cost']:,} 🌑 (доход: +{info['daily_income']:,} 🌑/день | {status_ico})")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💡 Команды:")
        lines.append(f"• «бизнесы [1-5]» — переключение страниц каталога")
        lines.append(f"• «купить_бизнес [1-40]» — покупка предприятия")
        lines.append(f"• «прибыль» — забрать накопленный доход")
        return await message.answer("\n".join(lines))

    if cmd in ("купить_бизнес", "купитьбизнес"):
        keys = list(db.BIZ_CATALOG.keys())
        idx_match = re.search(r"\b(\d+)\b", args)
        b_key = None
        if idx_match:
            idx_val = int(idx_match.group(1))
            if 1 <= idx_val <= len(keys):
                b_key = keys[idx_val - 1]
        else:
            clean_arg = args.lower().strip()
            for k, info in db.BIZ_CATALOG.items():
                if clean_arg in info["name"].lower() or clean_arg == k:
                    b_key = k
                    break

        if not b_key or b_key not in db.BIZ_CATALOG:
            return await message.answer("Укажите номер предприятия от 1 до 40! Пример: «купить_бизнес 1» (Каталог: «бизнесы»).")

        biz_data = db.BIZ_CATALOG[b_key]
        user_xp = user_db.get("xp", 0)
        user_level = max(1, user_xp // 100)

        if user_level < biz_data["req_lvl"]:
            return await message.answer(
                f"🔒 НЕДОСТАТОЧНЫЙ УРОВЕНЬ!\n"
                f"Предприятие {biz_data['name']} требует {biz_data['req_lvl']} уровень!\n"
                f"Ваш текущий уровень: {user_level} Lvl.\n\n"
                f"💡 Повышайте уровень, играя в игры, шахту, открывая кейсы и участвуя в викторинах!"
            )

        cost = biz_data["cost"]
        cur_bal = user_db.get("balance", 0)
        if cur_bal < cost:
            return await message.answer(
                f"❌ Недостаточно средств! Стоимость: {cost:,} 🌑 (у вас {cur_bal:,} 🌑)."
            )

        await db.add_balance(db_uid, -cost)
        await db.buy_business(db_uid, b_key)
        xp_gain = max(50, biz_data["req_lvl"] * 10)
        await db.add_xp(db_uid, xp_gain)

        return await message.answer(
            f"🎉 ПОЗДРАВЛЯЕМ С ПРИОБРЕТЕНИЕМ!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Вы приобрели {biz_data['name']}!\n"
            f"💰 Пассивный доход: +{biz_data['daily_income']:,} 🌑/день\n"
            f"⭐ Награда за развитие империи: +{xp_gain} XP!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Собирайте накопившуюся прибыль командой «прибыль»!"
        )

    if cmd in ("прибыль", "доход", "собрать_прибыль"):
        profit = await db.collect_business_profit(db_uid)
        if profit > 0:
            return await message.answer(f"💰 {user_display}, вы успешно собрали прибыль со своих предприятий: +{profit:,} 🌑!")
        return await message.answer("Прибыль ещё не накопилась (начисления производятся раз в час, максимум за 24 часа).")

    # ═══════════════════════════════════════════════════════════
    # 7. 🚗 АВТОСАЛОН И ГАРАЖ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("автосалон", "машины"):
        lines = ["🚗 ЭЛИТНЫЙ АВТОСАЛОН MOXXI 🚗", "━━━━━━━━━━━━━━━━━━━━"]
        for idx, (k, info) in enumerate(db.CAR_CATALOG.items(), start=1):
            lines.append(f"{idx}. {info['name']} — {info['cost']:,} 🌑")
        lines.append("━━━━━━━━━━━━━━━━━━━━\n💡 Покупка: «купить_машину [1-5]»\nВаш гараж: «гараж»")
        return await message.answer("\n".join(lines))

    if cmd in ("купить_машину", "купитьмашину"):
        keys = list(db.CAR_CATALOG.keys())
        idx_m = re.search(r"\b([1-5])\b", args)
        if not idx_m:
            return await message.answer("Укажите номер машины от 1 до 5! Пример: «купить_машину 2»")
        c_key = keys[int(idx_m.group(1)) - 1]
        cost = db.CAR_CATALOG[c_key]["cost"]
        if user_db.get("balance", 0) < cost:
            return await message.answer(f"❌ Недостаточно средств! Стоимость: {cost:,} 🌑.")
        await db.add_balance(db_uid, -cost)
        await db.buy_car(db_uid, c_key)
        return await message.answer(f"🎉 Поздравляем! В ваш гараж доставлен новенький {db.CAR_CATALOG[c_key]['name']}!")

    if cmd in ("гараж", "моя_машина", "авто"):
        cars = await db.get_user_cars(db_uid)
        if not cars:
            return await message.answer("В вашем гараже пусто. Посетите «автосалон» для покупки авто!")
        lines = [f"🏎 ГАРАЖ ИГРОКА {user_display} 🏎", "━━━━━━━━━━━━━━━━━━━━"]
        for c in cars:
            k = c["car_key"]
            if k in db.CAR_CATALOG:
                lines.append(f"• {db.CAR_CATALOG[k]['name']}")
        return await message.answer("\n".join(lines))

    # ═══════════════════════════════════════════════════════════
    # 8. 🐾 ПИТОМЦЫ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("зоомагазин", "питомцы"):
        lines = ["🐾 ВОЛШЕБНЫЙ ЗООМАГАЗИН 🐾", "━━━━━━━━━━━━━━━━━━━━"]
        for idx, (k, info) in enumerate(db.PET_CATALOG.items(), start=1):
            lines.append(f"{idx}. {info['icon']} {info['name']} — {info['cost']:,} 🌑")
        lines.append("━━━━━━━━━━━━━━━━━━━━\n💡 Покупка: «купить_питомца [1-4] [кличка]»\nСтатус: «питомец»")
        return await message.answer("\n".join(lines))

    if cmd in ("купить_питомца", "купитьпитомца"):
        p = args.split()
        if len(p) < 2 or not p[0].isdigit() or not (1 <= int(p[0]) <= 4):
            return await message.answer("Формат: «купить_питомца [1-4] [кличка]»\nПример: «купить_питомца 1 Барсик»")
        keys = list(db.PET_CATALOG.keys())
        p_key = keys[int(p[0]) - 1]
        cost = db.PET_CATALOG[p_key]["cost"]
        p_name = p[1].strip()[:20]
        if user_db.get("balance", 0) < cost:
            return await message.answer(f"❌ Недостаточно монет! Стоимость: {cost:,} 🌑.")
        await db.add_balance(db_uid, -cost)
        await db.buy_pet(db_uid, p_key, p_name)
        icon = db.PET_CATALOG[p_key]["icon"]
        return await message.answer(f"🎉 Вы завели питомца: {icon} {p_name}! Кормите его: «покормить_питомца».")

    if cmd in ("питомец", "мой_питомец"):
        pet = await db.get_user_pet(db_uid)
        if not pet:
            return await message.answer("У вас пока нет питомца. Купите в «зоомагазин»!")
        info = db.PET_CATALOG.get(pet["pet_type"], {"name": "Питомец", "icon": "🐾"})
        ans = (
            f"{info['icon']} ВАШ ПИТОМЕЦ: {pet['pet_name']} ({info['name']})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⭐ Уровень: {pet['level']} ({pet['xp']} XP)\n"
            f"🍖 Сытость: {pet['hunger']}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Покормить: «покормить_питомца»"
        )
        return await message.answer(ans)

    if cmd in ("покормить_питомца", "покормитьпитомца"):
        pet = await db.get_user_pet(db_uid)
        if not pet:
            return await message.answer("У вас нет питомца.")
        await db.feed_pet(db_uid)
        return await message.answer(f"🍖 {user_display} покормил(а) {pet['pet_name']}! Сытость 100% (+30 XP питомцу).")

    # ═══════════════════════════════════════════════════════════
    # 9. 🃏 БЛЭКДЖЕК (21 ОЧКО) И КРАШ (CRASH)
    # ═══════════════════════════════════════════════════════════
    if cmd in ("21", "блэкджек", "blackjack"):
        cur_bal = user_db.get("balance", 0)
        amount = parse_amount(args, max_val=cur_bal)
        if not amount or amount <= 0:
            return await message.answer("Укажите ставку! Пример: «21 1000»")
        if cur_bal < amount:
            return await message.answer("❌ Недостаточно средств!")

        # Быстрый честный блэкджек
        p_c1, p_c2 = random.randint(2, 11), random.randint(2, 11)
        d_c1, d_c2 = random.randint(2, 11), random.randint(2, 11)
        p_sum = p_c1 + p_c2
        d_sum = d_c1 + d_c2

        if p_sum == 21:
            win = int(amount * 1.5)
            await db.add_balance(db_uid, win)
            res = f"🔥 БЛЭКДЖЕК 21! Вы выиграли +{int(amount * 2.5):,} 🌑!"
        elif p_sum > 21:
            await db.add_balance(db_uid, -amount)
            res = f"💨 Перебор ({p_sum})! Вы потеряли {amount:,} 🌑."
        elif d_sum > 21 or p_sum > d_sum:
            await db.add_balance(db_uid, amount)
            res = f"🎉 ПОБЕДА! Вы выиграли +{amount * 2:,} 🌑!"
        elif p_sum < d_sum:
            await db.add_balance(db_uid, -amount)
            res = f"💨 Дилер победил ({d_sum} против {p_sum})! -{amount:,} 🌑."
        else:
            res = f"🤝 Ничья ({p_sum} = {d_sum})! Ставка возвращена."

        ans = (
            f"🃏 КАРТОЧНАЯ ИГРА 21 (БЛЭКДЖЕК) 🃏\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Ваши карты: [{p_c1}] + [{p_c2}] = {p_sum}\n"
            f"Карты дилера: [{d_c1}] + [{d_c2}] = {d_sum}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{res}"
        )
        return await message.answer(ans)

    if cmd in ("краш", "crash"):
        cur_bal = user_db.get("balance", 0)
        p_args = args.split()
        if not p_args:
            return await message.answer("Формат: «краш [ставка] [коэффициент_автовывода]»\nПример: «краш 500 2.5»")
        amount = parse_amount(p_args[0], max_val=cur_bal)
        if not amount or amount <= 0:
            return await message.answer("Неверная ставка!")
        if cur_bal < amount:
            return await message.answer("❌ Недостаточно средств!")

        target_mult = float(p_args[1].replace(",", ".")) if len(p_args) > 1 else 2.0
        target_mult = max(1.1, min(10.0, target_mult))

        # Генерация краша
        crash_point = round(random.uniform(1.0, 5.0) if random.random() < 0.75 else random.uniform(5.0, 15.0), 2)
        if crash_point >= target_mult:
            profit = int(amount * target_mult) - amount
            await db.add_balance(db_uid, profit)
            res = f"🚀 РАКЕТА ДОЛЕТЕЛА ДО x{target_mult} (Краш на x{crash_point})!\nВы выиграли +{int(amount * target_mult):,} 🌑!"
        else:
            await db.add_balance(db_uid, -amount)
            res = f"💥 ВЗРЫВ НА x{crash_point}! Ракета взорвалась раньше вашей цели x{target_mult}.\nВы потеряли {amount:,} 🌑."

        ans = f"🚀 ИГРА КРАШ (CRASH)\n━━━━━━━━━━━━━━━━━━━━\n{res}"
        return await message.answer(ans)

    # ═══════════════════════════════════════════════════════════
    # 10. ⛏ ШАХТА И РЫБАЛКА
    # ═══════════════════════════════════════════════════════════
    if cmd in ("шахта", "копать", "рудокоп", "кирка", "mine"):
        cd = await db.cooldown_left(db_uid, "mine_vk", 1200)
        if cd > 0:
            m = cd // 60
            s = cd % 60
            return await message.answer(f"⏳ Ваша кирка остывает! Снова в шахту через {m} мин {s} сек.")

        await db.set_cooldown(db_uid, "mine_vk", 1200)
        roll = random.random()
        if roll < 0.05:
            reward = random.randint(15000, 30000)
            loot = f"💎 АЛМАЗНЫЙ КУШ! Найдена жила редких алмазов: +{reward:,} 🌑!"
        elif roll < 0.25:
            reward = random.randint(3000, 6000)
            loot = f"🪙 ЗОЛОТАЯ ЖИЛА! Добыто золото: +{reward:,} 🌑!"
        elif roll < 0.70:
            reward = random.randint(800, 2000)
            loot = f"⛏ ЖЕЛЕЗО! Добыта руда: +{reward:,} 🌑!"
        elif roll < 0.92:
            reward = random.randint(200, 500)
            loot = f"🪨 Обычный булыжник: +{reward:,} 🌑."
        else:
            reward = -min(user_db.get("balance", 0), 300)
            loot = f"💥 ОБВАЛ! Поломка кирки: {reward:,} 🌑."

        await db.add_balance(db_uid, reward)
        await db.add_xp(db_uid, 20)
        return await message.answer(f"⛏ ШАХТА\n{loot}\n💰 Баланс: {user_db.get('balance', 0) + reward:,} 🌑")

    if cmd in ("рыбалка", "рыбачить", "удочка", "fish"):
        cd = await db.cooldown_left(db_uid, "fish_vk", 900)
        if cd > 0:
            m = cd // 60
            s = cd % 60
            return await message.answer(f"⏳ Рыба напугана! Закинуть удочку можно через {m} мин {s} сек.")

        await db.set_cooldown(db_uid, "fish_vk", 900)
        roll = random.random()
        if roll < 0.04:
            catch, g = "👑 ЗОЛОТАЯ РЫБКА", 15000
        elif roll < 0.20:
            catch, g = "🦈 Королевский осётр", 4500
        elif roll < 0.60:
            catch, g = "🐠 Радужная форель", 1200
        elif roll < 0.90:
            catch, g = "🐟 Речной карась", 400
        else:
            catch, g = "👟 Дырявый сапог", 0

        await db.add_balance(db_uid, g)
        await db.add_xp(db_uid, 15)
        return await message.answer(f"🎣 РЫБАЛКА\nУлов {user_display}: {catch}!\n💰 Продано за +{g:,} 🌑.")

    # ═══════════════════════════════════════════════════════════
    # 11. 💘 ШИППЕРИНГ / ПАРА ДНЯ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("шип", "шипперить", "пара", "парадня", "пара_дня", "пейринг"):
        if not is_chat:
            return await message.answer("Шипперинг доступен только в беседах!")
        today_str = datetime.date.today().isoformat()
        current_pair = await db.get_pair_of_day(message.peer_id, today_str)
        if current_pair:
            u1_tag = f"[id{current_pair['user1_id']}|{current_pair['user1_name']}]"
            u2_tag = f"[id{current_pair['user2_id']}|{current_pair['user2_name']}]"
            return await message.answer(
                f"💘 ПАРА ДНЯ В БЕСЕДЕ 💘\n━━━━━━━━━━━━━━━━━━━━\n"
                f"💑 {u1_tag} 💕 {u2_tag}\n"
                f"💖 Совместимость: {current_pair['compatibility']}%\n"
                f"📜 {current_pair['story']}"
            )
        try:
            conv_members = await bot.api.messages.get_conversation_members(peer_id=message.peer_id)
            valid_ids = [m.member_id for m in conv_members.items if m.member_id > 0]
        except Exception:
            valid_ids = []
        if len(valid_ids) < 2:
            return await message.answer("Слишком мало участников для пары.")
        p1_id, p2_id = random.sample(valid_ids, 2)
        p1_fn, _ = await get_vk_user_info(p1_id)
        p2_fn, _ = await get_vk_user_info(p2_id)
        comp = random.randint(70, 100)
        story = "Звёзды шепчут: эти двое созданы друг для друга, срочно зовите их на свидание!"
        await db.save_pair_of_day(message.peer_id, today_str, p1_id, p2_id, p1_fn, p2_fn, comp, story)
        return await message.answer(
            f"💘 КУПИДОН СДЕЛАЛ ВЫБОР! 💘\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💑 [id{p1_id}|{p1_fn}] 💕 [id{p2_id}|{p2_fn}]\n"
            f"💖 Совместимость: {comp}%!\n"
            f"📜 {story}"
        )

    # ═══════════════════════════════════════════════════════════
    # 12. ⚔️ PVP ДУЭЛИ И КОСТИ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("дуэль", "duel"):
        sub = args.lower().strip()
        duel_key = f"{message.peer_id}:{user_id}"
        if sub in ("принять", "да", "yes"):
            duel = active_duels.get(duel_key)
            if not duel or time.time() > duel["expire_ts"]:
                active_duels.pop(duel_key, None)
                return await message.answer("❌ У вас нет активных вызовов!")
            challenger_id, amount = duel["challenger_id"], duel["amount"]
            c_db_uid = to_db_uid(challenger_id)
            c_data = await db.get_user(c_db_uid) or {}
            if c_data.get("balance", 0) < amount or user_db.get("balance", 0) < amount:
                active_duels.pop(duel_key, None)
                return await message.answer("❌ Недостаточно монет для дуэли!")
            await db.add_balance(c_db_uid, -amount)
            await db.add_balance(db_uid, -amount)
            active_duels.pop(duel_key, None)
            total = amount * 2
            ch_name = await get_display_name(challenger_id)
            winner_id, winner_name = random.choice([(challenger_id, ch_name), (user_id, user_display)])
            await db.add_balance(to_db_uid(winner_id), total)
            return await message.answer(f"⚔️ ДУЭЛЬ! 💥 Выстрел... Победитель: {winner_name} забирает +{total:,} 🌑!")

        if sub in ("отклонить", "нет"):
            active_duels.pop(duel_key, None)
            return await message.answer("🏳️ Дуэль отклонена.")

        if not is_chat:
            return await message.answer("Дуэли доступны только в беседах!")
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите соперника! Пример: «дуэль @юзер 1000»")
        clean_args = re.sub(r"\[(?:id|club)\d+\|[^\]]+\]", "", args).strip()
        amount = parse_amount(clean_args, max_val=user_db.get("balance", 0))
        if not amount or amount <= 0:
            return await message.answer("Укажите ставку! Пример: «дуэль 1000»")
        if user_db.get("balance", 0) < amount:
            return await message.answer("Недостаточно средств!")
        active_duels[f"{message.peer_id}:{target_id}"] = {"challenger_id": user_id, "amount": amount, "expire_ts": time.time() + 60}
        tg_name = await get_display_name(target_id)
        return await message.answer(f"⚔️ {user_display} бросил(а) вызов на дуэль игроку {tg_name} на {amount:,} 🌑!\nПринять: «дуэль принять».")

    if cmd in ("кости", "dice_pvp"):
        if not is_chat:
            return await message.answer("Кости доступны только в беседах!")
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите соперника! Пример: «кости @юзер 500»")
        amount = parse_amount(re.sub(r"\[(?:id|club)\d+\|[^\]]+\]", "", args).strip(), max_val=user_db.get("balance", 0))
        if not amount or amount <= 0:
            return await message.answer("Укажите ставку!")
        t_data = await db.get_user(to_db_uid(target_id)) or {}
        if user_db.get("balance", 0) < amount or t_data.get("balance", 0) < amount:
            return await message.answer("❌ Недостаточно средств для игры!")
        s1, s2 = random.randint(2, 12), random.randint(2, 12)
        tg_name = await get_display_name(target_id)
        if s1 > s2:
            await db.add_balance(db_uid, amount)
            await db.add_balance(to_db_uid(target_id), -amount)
            res = f"🏆 Победил {user_display} (+{amount:,} 🌑)!"
        elif s2 > s1:
            await db.add_balance(to_db_uid(target_id), amount)
            await db.add_balance(db_uid, -amount)
            res = f"🏆 Победил {tg_name} (+{amount:,} 🌑)!"
        else:
            res = "🤝 Ничья!"
        return await message.answer(f"🎲 КОСТИ: {user_display} [{s1}] vs {tg_name} [{s2}]\n{res}")

    # ═══════════════════════════════════════════════════════════
    # 13. 💰 КЛАССИЧЕСКАЯ ЭКОНОМИКА (Профиль, Бонус, Казино, Топ)
    # ═══════════════════════════════════════════════════════════
    if cmd in ("профиль", "баланс", "я", "стата"):
        interest = await db.apply_bank_interest(db_uid)
        u_fresh = await db.get_user(db_uid) or user_db
        balance = u_fresh.get("balance", 0)
        bank = u_fresh.get("bank", 0)
        xp = u_fresh.get("xp", 0)
        rep = u_fresh.get("rep", 0)
        level = max(1, xp // 100)
        nick_val = u_fresh.get("nick")
        nick_line = f"🏷 Позывной: {nick_val}\n" if nick_val else ""
        u_clan = await db.get_user_clan(db_uid)
        clan_str = f"🏰 Клан: {u_clan['name']}\n" if u_clan else ""
        pet = await db.get_user_pet(db_uid)
        pet_str = f"🐾 Питомец: {pet['pet_name']}\n" if pet else ""
        
        j_left = await db.is_in_jail(db_uid)
        jail_line = f"🚨 Статус: 🔒 В КПЗ ({j_left // 60} мин осталось)\n" if j_left > 0 else "🕊 Статус: На свободе\n"

        user_gifts = await db.get_user_gifts(db_uid, limit=3)
        if user_gifts:
            gifts_display = ", ".join(g["gift_name"] for g in user_gifts)
            gifts_str = f"🎁 Подарки: {gifts_display}\n"
        else:
            gifts_str = ""

        interest_str = f"\n📈 Начислены проценты по вкладу: +{interest:,} 🌑!\n" if interest > 0 else ""

        profile_text = (
            f"👤 КАРТОЧКА ИГРОКА\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Имя: {user_display}\n"
            f"{nick_line}"
            f"👑 Ранг в чате: [{my_rank}] {RANK_NAMES[my_rank]} {RANK_ICONS[my_rank]}\n"
            f"{jail_line}"
            f"{clan_str}"
            f"{pet_str}"
            f"{gifts_str}"
            f"💰 На руках: {balance:,} 🌑\n"
            f"🏦 В банке: {bank:,} 🌑\n"
            f"⭐ Уровень: {level} ({xp} XP)\n"
            f"🏆 Репутация: {rep:+d}\n"
            f"{interest_str}"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Введите «бонус» для ежедневной награды или «банк» для депозитов!"
        )
        return await message.answer(profile_text, keyboard=get_main_keyboard(is_chat=is_chat))

    if cmd in ("бонус", "ежедневный", "daily"):
        cd_left = await db.cooldown_left(db_uid, "daily_bonus", 86400)
        if cd_left > 0:
            h = cd_left // 3600
            m = (cd_left % 3600) // 60
            s = cd_left % 60
            return await message.answer(f"⏳ Следующий бонус через {h} ч {m} мин {s} сек.")
        reward = random.randint(2500, 7500)
        await db.set_cooldown(db_uid, "daily_bonus", 86400)
        await db.add_balance(db_uid, reward)
        await db.add_xp(db_uid, 50)
        return await message.answer(
            f"🎁 ЕЖЕДНЕВНЫЙ БОНУС ПОЛУЧЕН! 🎁\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Игрок: {user_display}\n"
            f"💰 Начислено: +{reward:,} 🌑\n"
            f"⭐ Получено опыта: +50 XP\n\n"
            f"⏳ Следующий бонус будет доступен через 24 часа!",
            keyboard=get_main_keyboard(is_chat=is_chat)
        )

    if cmd in ("казино", "слоты"):
        cur_balance = user_db.get("balance", 0)
        amount = parse_amount(args, max_val=cur_balance)
        if not amount or amount <= 0:
            kb_casino = Keyboard(inline=True)
            kb_casino.add(Text("🎰 Казино 500"), color=KeyboardButtonColor.PRIMARY)
            kb_casino.add(Text("🎰 Казино 1000"), color=KeyboardButtonColor.PRIMARY)
            kb_casino.add(Text("🎰 Казино 5000"), color=KeyboardButtonColor.PRIMARY)
            kb_casino.row()
            kb_casino.add(Text("💥 Казино все"), color=KeyboardButtonColor.NEGATIVE)
            kb_casino.add(Text("📖 Все команды"), color=KeyboardButtonColor.SECONDARY)
            return await message.answer(
                f"🎰 ИГРОВОЙ АВТОМАТ «777 SLOTS» 🎰\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Ваш баланс: {cur_balance:,} 🌑\n\n"
                f"💎 Множители выигрыша:\n"
                f"• 7️⃣ 7️⃣ 7️⃣ — СУПЕР ДЖЕКПОТ x10!\n"
                f"• 💎 💎 💎 — Алмазный ряд x5!\n"
                f"• Любые три в ряд — x3!\n"
                f"• Любые два совпадения — x1.5!\n\n"
                f"👇 Выберите быструю ставку кнопкой ниже или напишите «казино [сумма]»:",
                keyboard=kb_casino.get_json()
            )
        if cur_balance < amount:
            return await message.answer(f"❌ Недостаточно средств!")
        symbols = ["🍒", "🍋", "🍇", "💎", "7️⃣"]
        s1, s2, s3 = random.choice(symbols), random.choice(symbols), random.choice(symbols)
        mult = 10.0 if s1 == s2 == s3 == "7️⃣" else (5.0 if s1 == s2 == s3 == "💎" else (3.0 if s1 == s2 == s3 else (1.5 if s1 == s2 or s2 == s3 or s1 == s3 else 0.0)))
        if mult > 0:
            win = int(amount * mult) - amount
            await db.add_balance(db_uid, win)
            res_str = f"➕ Выигрыш: +{int(amount * mult):,} 🌑"
        else:
            await db.add_balance(db_uid, -amount)
            res_str = f"➖ Проигрыш: -{amount:,} 🌑"
        return await message.answer(f"🎰 СЛОТЫ: [ {s1} | {s2} | {s3} ]\n{res_str}")

    if cmd in ("рулетка", "roulette"):
        p_args = args.split()
        if len(p_args) < 2:
            return await message.answer("Пример: «рулетка 500 красное»")
        amount = parse_amount(p_args[0], max_val=user_db.get("balance", 0))
        choice = p_args[1].lower()
        if not amount or user_db.get("balance", 0) < amount:
            return await message.answer("Недостаточно средств!")
        red_nums = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        roll = random.randint(0, 36)
        r_col = "зеленое" if roll == 0 else ("красное" if roll in red_nums else "черное")
        won = (choice in ("красное", "к", "red") and r_col == "красное") or (choice in ("черное", "ч", "black") and r_col == "черное") or (choice in ("зеленое", "0") and roll == 0)
        mult = 14.0 if roll == 0 else 2.0
        if won:
            profit = int(amount * mult) - amount
            await db.add_balance(db_uid, profit)
            res = f"🎉 ПОБЕДА! +{int(amount * mult):,} 🌑!"
        else:
            await db.add_balance(db_uid, -amount)
            res = f"💨 Мимо: -{amount:,} 🌑."
        return await message.answer(f"🎡 Рулетка: выпало {roll} ({r_col})!\n{res}")

    if cmd in ("топ", "top"):
        rows = await db.fetchall("SELECT username, first_name, balance, nick FROM users ORDER BY balance DESC LIMIT 10")
        lines = ["👑 ТОП 10 ИГРОКОВ MOXXI 👑", "━━━━━━━━━━━━━━━━━━━━"]
        for idx, r in enumerate(rows, start=1):
            name = r.get("nick") or r.get("first_name") or r.get("username") or "Игрок"
            lines.append(f"{idx}. {name} — {r.get('balance', 0):,} 🌑")
        return await message.answer("\n".join(lines))

    if cmd in ("передать", "перевод", "pay"):
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id:
            return await message.answer("Укажите получателя!")
        amount = parse_amount(re.sub(r"\[(?:id|club)\d+\|[^\]]+\]", "", args).strip(), max_val=user_db.get("balance", 0))
        if not amount or user_db.get("balance", 0) < amount:
            return await message.answer("Недостаточно монет!")
        await db.ensure_user(to_db_uid(target_id), username=f"id{target_id}")
        await db.add_balance(db_uid, -amount)
        await db.add_balance(to_db_uid(target_id), amount)
        t_name = await get_display_name(target_id)
        return await message.answer(f"💸 {user_display} перевёл(а) {amount:,} 🌑 игроку {t_name}!")

    # ═══════════════════════════════════════════════════════════
    # 14. 🔮 УТИЛИТЫ MOXXI, МОДЕРАЦИЯ И ТИКЕТЫ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("инфа", "вероятность"):
        return await message.answer(f"📊 Вероятность «{args}»: {random.randint(0, 100)}%! 🔮")

    if cmd in ("кто", "кого"):
        if not is_chat:
            return await message.answer("Только в беседах!")
        try:
            mems = await bot.api.messages.get_conversation_members(peer_id=message.peer_id)
            v_ids = [m.member_id for m in mems.items if m.member_id > 0]
        except Exception:
            v_ids = []
        if not v_ids:
            return await message.answer("Не удалось определить участников.")
        ch_name = await get_display_name(random.choice(v_ids))
        return await message.answer(f"🎯 По моим данным, {args} — это {ch_name}!")

    if cmd in ("ник", "+ник"):
        if not args:
            return await message.answer("Пример: «ник Самурай»")
        await db.set_nick(db_uid, args.strip()[:20])
        return await message.answer(f"✅ Ник изменён на: {args.strip()[:20]}!")

    if cmd in ("-ник", "снятьник"):
        await db.set_nick(db_uid, "")
        return await message.answer("✅ Ник сброшен.")

    if cmd in ("кик", "kick"):
        if not is_chat:
            return await message.answer("Только в беседах!")
        if my_rank < 2:
            return await message.answer("⛔️ Кикать можно с ранга [2] (Младший модератор)!")
        target_id = extract_target_vk_id(message, args)
        if not target_id:
            return await message.answer("Укажите нарушителя!")
        t_rank = await get_effective_rank(message.peer_id, target_id)
        if t_rank >= my_rank:
            return await message.answer(f"⛔️ Иммунитет! Ранг цели [{t_rank}] равен или выше вашего!")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.peer_id - 2000000000, member_id=target_id)
            t_name = await get_display_name(target_id)
            return await message.answer(f"🚪 {t_name} исключён(а) из беседы.")
        except Exception as e:
            return await message.answer(f"⚠️ Ошибка кика (проверьте права бота): {e}")

    if cmd in ("варн", "warn"):
        if not is_chat:
            return await message.answer("Только в беседах!")
        if my_rank < 1:
            return await message.answer("⛔️ Варны доступны с ранга [1] (Стажёр)!")
        target_id = extract_target_vk_id(message, args)
        if not target_id:
            return await message.answer("Укажите нарушителя!")
        t_rank = await get_effective_rank(message.peer_id, target_id)
        if t_rank >= my_rank:
            return await message.answer(f"⛔️ Иммунитет! Ранг цели [{t_rank}] равен или выше вашего!")
        w_c = await db.add_warn(message.peer_id, target_id, user_id, "Нарушение правил")
        t_name = await get_display_name(target_id)
        if w_c >= 3:
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.peer_id - 2000000000, member_id=target_id)
                await db.reset_warns(message.peer_id, target_id)
                return await message.answer(f"🚫 {t_name} получил(а) 3/3 варнов и был(а) исключён(а)!")
            except Exception:
                pass
        return await message.answer(f"⚠️ {t_name} получил(а) варн ({w_c}/3).")

    # ═══════════════════════════════════════════════════════════
    # 16. 🥷 КРИМИНАЛ: ОГРАБЛЕНИЯ, КПЗ И ПОБЕГИ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("ограбить", "украсть", "обчистить", "вор", "rob"):
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id or target_id < 0:
            return await message.answer(
                "🥷 Укажите жертву для ограбления через @упоминание или ответом на сообщение:\n"
                "Пример: «ограбить @id»"
            )
        t_db_uid = to_db_uid(target_id)
        if await db.is_in_jail(t_db_uid) > 0:
            return await message.answer("❌ Жертва уже находится в КПЗ! Там нечего красть.")

        cd = await db.cooldown_left(db_uid, "robbery_cd", 1200)
        if cd > 0:
            m = cd // 60
            s = cd % 60
            return await message.answer(f"⏳ Полиция патрулирует улицы! Новая вылазка через {m} мин {s} сек.")

        await db.set_cooldown(db_uid, "robbery_cd", 1200)
        t_user = await sync_vk_user(target_id)
        t_bal = t_user.get("balance", 0)
        t_name = await get_display_name(target_id)

        if t_bal < 300:
            return await message.answer(f"💨 В карманах {t_name} гуляет ветер (меньше 300 🌑)! Нечего красть.")

        if random.random() < 0.45:
            percent = random.uniform(0.10, 0.25)
            stolen = max(100, min(50_000, int(t_bal * percent)))
            await db.add_balance(t_db_uid, -stolen)
            await db.add_balance(db_uid, stolen)
            await db.add_xp(db_uid, 35)
            return await message.answer(
                f"🥷 ДЕРЗКОЕ ОГРАБЛЕНИЕ!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{user_display} ловко вытащил кошелёк из кармана {t_name}!\n"
                f"💰 Добыча: +{stolen:,} 🌑\n"
                f"⭐ Опыт: +35 XP"
            )
        else:
            jail_sec = 900
            await db.send_to_jail(db_uid, jail_sec)
            fine = min(user_db.get("balance", 0), 1000)
            if fine > 0:
                await db.add_balance(db_uid, -fine)
            return await message.answer(
                f"🚨 ПОЛИЦЕЙСКАЯ ОБЛАВА!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{t_name} заметил вора и поднял тревогу!\n"
                f"🚔 Патруль задержал {user_display} с поличным!\n"
                f"⛓ Вы отправлены в КПЗ на 15 минут!\n"
                f"💸 Изъято штрафом: -{fine:,} 🌑\n\n"
                f"💡 Напишите «побег» для попытки сбежать или попросите друзей внести «залог @юзер»!"
            )

    if cmd in ("тюрьма", "кпз", "jail", "камера"):
        j_left = await db.is_in_jail(db_uid)
        if j_left > 0:
            jm = j_left // 60
            js = j_left % 60
            return await message.answer(
                f"🚨 КПЗ УВД MOXXI\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Заключённый: {user_display}\n"
                f"Статус: 🔒 За решёткой\n"
                f"⏳ До свободы: {jm} мин {js} сек\n\n"
                f"🔓 Доступные действия:\n"
                f"• «побег» — попытка взлома решётки (шанс 30%)\n"
                f"• Друг может выкупить вас: «залог @юзер» (10 000 🌑)"
            )
        return await message.answer(
            f"🕊 КПЗ УВД MOXXI\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Гражданин {user_display} чист перед законом!\n"
            f"Вы на свободе. Можете пойти на дело: «ограбить @юзер»."
        )

    if cmd in ("побег", "сбежать", "escape"):
        j_left = await db.is_in_jail(db_uid)
        if j_left <= 0:
            return await message.answer("Вы не находитесь в КПЗ!")

        esc_cd = await db.cooldown_left(db_uid, "escape_attempt", 300)
        if esc_cd > 0:
            m = esc_cd // 60
            s = esc_cd % 60
            return await message.answer(f"⏳ Охрана не сводит глаз с вашей камеры! Попробуйте снова через {m} мин {s} сек.")

        await db.set_cooldown(db_uid, "escape_attempt", 300)
        if random.random() < 0.30:
            await db.release_from_jail(db_uid)
            await db.add_xp(db_uid, 50)
            return await message.answer(
                f"🏃💨 УСПЕШНЫЙ ПОБЕГ!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{user_display} пробил вентиляционную решётку ложкой и скрылся в темноте!\n"
                f"🕊 Двери камер позади — вы на свободе! (+50 XP)"
            )
        else:
            new_dur = j_left + 600
            await db.send_to_jail(db_uid, new_dur)
            return await message.answer(
                f"🐕🚨 ПОБЕГ ПРОВАЛЕН!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Охрана с собаками перехватила {user_display} на крыше тюрьмы!\n"
                f"⛓ Наказание за попытку побега: +10 минут к сроку в КПЗ!"
            )

    if cmd in ("залог", "выкуп", "bail"):
        target_id = extract_target_vk_id(message, args)
        if not target_id:
            return await message.answer("Укажите заключённого для внесения залога: «залог @юзер»")
        t_db_uid = to_db_uid(target_id)
        t_jail = await db.is_in_jail(t_db_uid)
        if t_jail <= 0:
            return await message.answer("Этот игрок не находится в КПЗ!")
        bail_cost = 10_000
        cur_bal = user_db.get("balance", 0)
        if cur_bal < bail_cost:
            return await message.answer(f"❌ Недостаточно средств для залога! Требуется {bail_cost:,} 🌑.")
        await db.add_balance(db_uid, -bail_cost)
        await db.release_from_jail(t_db_uid)
        await db.add_rep(db_uid, 1)
        t_name = await get_display_name(target_id)
        return await message.answer(
            f"🤝 ЗАЛОГ ВНЕСЁН!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{user_display} внёс залог {bail_cost:,} 🌑 за {t_name}!\n"
            f"🔓 Конвой открыл камеру — заключённый на свободе!\n"
            f"⭐ Ваша репутация: +1"
        )

    # ═══════════════════════════════════════════════════════════
    # 17. 📦 ЛУТБОКСЫ И КЕЙСЫ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("кейсы", "сундуки", "боксы", "cases", "лутбоксы"):
        catalog_lines = []
        for cid, cinfo in CASES_CATALOG.items():
            catalog_lines.append(
                f"{cid}. {cinfo['name']} — {cinfo['price']:,} 🌑\n"
                f"   📝 {cinfo['desc']}"
            )
        text = (
            f"📦 МАГАЗИН КЕЙСОВ И ЛУТБОКСОВ\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            + "\n\n".join(catalog_lines) +
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Чтобы открыть кейс, напишите:\n"
            f"«открыть кейс [номер]» или «кейс [1-4]»"
        )
        return await message.answer(text)

    if cmd in ("открыть_кейс", "открытькейс", "открыть", "кейс"):
        c_num = None
        for p in args.split():
            clean_p = p.replace("кейс", "").strip()
            if clean_p.isdigit() and int(clean_p) in CASES_CATALOG:
                c_num = int(clean_p)
                break
        if not c_num:
            return await message.answer("Укажите номер кейса (1–4)! Пример: «открыть кейс 1» или «кейсы».")

        cdata = CASES_CATALOG[c_num]
        price = cdata["price"]
        cur_bal = user_db.get("balance", 0)
        if cur_bal < price:
            return await message.answer(f"❌ Недостаточно средств! Кейс стоит {price:,} 🌑 (у вас {cur_bal:,} 🌑).")

        await db.add_balance(db_uid, -price)

        r = random.random()
        cumulative = 0.0
        chosen_drop = cdata["drops"][0]
        for drop in cdata["drops"]:
            cumulative += drop["chance"]
            if r <= cumulative:
                chosen_drop = drop
                break

        dtype = chosen_drop.get("type")
        win_coins = 0
        j_amt = 0
        if dtype == "car":
            car_id = chosen_drop["car_id"]
            car_name = chosen_drop["car_name"]
            user_cars = await db.get_user_cars(db_uid)
            has_car = any(c["car_id"] == car_id for c in user_cars)
            if not has_car:
                await db.buy_car(db_uid, car_id, 0)
                prize_str = f"🏎 АВТОМОБИЛЬ: {car_name}! (добавлен в «гараж»)"
            else:
                comp = chosen_drop.get("fallback_coins", 100000)
                await db.add_balance(db_uid, comp)
                prize_str = f"🏎 {car_name} (уже есть в гараже!)\n💰 Компенсация: +{comp:,} 🌑"
        elif dtype == "jackpot":
            j_amt = chosen_drop["amount"]
            j_xp = chosen_drop.get("xp", 100)
            await db.add_balance(db_uid, j_amt)
            await db.add_xp(db_uid, j_xp)
            prize_str = f"💎 ДЖЕКПОТ КЕЙСА: +{j_amt:,} 🌑 и +{j_xp} XP!"
        else:
            win_coins = random.randint(chosen_drop["min"], chosen_drop["max"])
            await db.add_balance(db_uid, win_coins)
            await db.add_xp(db_uid, 20)
            diff = win_coins - price
            diff_str = f"(+{diff:,} 🌑)" if diff >= 0 else f"({diff:,} 🌑)"
            prize_str = f"💰 {win_coins:,} 🌑 {diff_str} + 20 XP"

        roulette_items = ["🪙 1000", "💰 КУШ", "💎 ДЖЕКПОТ", "🚗 АВТО", "⭐ ОПЫТ"]
        random.shuffle(roulette_items)
        drum = " | ".join(roulette_items[:3])

        final_bal = user_db.get("balance", 0) - price + (win_coins if dtype == "coins" else (j_amt if dtype == "jackpot" else 0))
        spin_text = (
            f"🎰 ОТКРЫТИЕ: {cdata['name']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Вращение барабана лутбокса...\n"
            f"➔ [ {drum} ] ➔\n"
            f"✨ Барабан остановился!\n\n"
            f"🎉 ВАШ ВЫИГРЫШ:\n"
            f"{prize_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👛 Ваш баланс: {final_bal:,} 🌑"
        )
        return await message.answer(spin_text)

    # ═══════════════════════════════════════════════════════════
    # 18. 🍾 БУТЫЛОЧКА В БЕСЕДЕ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("бутылочка", "бутылка", "spin"):
        if not is_chat:
            return await message.answer("🍾 Бутылочка доступна только в беседах!")

        member_ids: list[int] = []
        try:
            conv = await bot.api.messages.get_conversation_members(peer_id=message.peer_id)
            if conv and conv.profiles:
                member_ids = [p.id for p in conv.profiles if p.id > 0]
        except Exception:
            pass

        if len(member_ids) < 2:
            staff = await db.get_chat_staff_list(db_cid)
            member_ids = [from_db_uid(s["user_id"]) for s in staff if s["user_id"] > 0]
            if user_id not in member_ids:
                member_ids.append(user_id)

        if len(member_ids) < 2:
            return await message.answer(
                "🍾 Для игры в бутылочку в беседе должно быть как минимум 2 активных участника!"
            )

        p1_id = user_id
        other_members = [uid for uid in member_ids if uid != p1_id]
        p2_id = random.choice(other_members) if other_members else p1_id

        p1_name = await get_display_name(p1_id)
        p2_name = await get_display_name(p2_id)
        action = random.choice(BOTTLE_ACTIONS)

        bottle_text = (
            f"🍾 БУТЫЛОЧКА КРУТИТСЯ... 💫\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Горлышко бутылочки указало на:\n"
            f"👉 {p1_name}  ❤️  {p2_name} 👈\n\n"
            f"🎲 ЗАДАНИЕ ОТ MOXXI:\n"
            f"«{action}»\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Выполняйте задание перед всей беседой! 😉"
        )
        return await message.answer(bottle_text)

    # ═══════════════════════════════════════════════════════════
    # 19. 🧠 ЧАТ-ВИКТОРИНА (КВИЗ НА СКОРОСТЬ)
    # ═══════════════════════════════════════════════════════════
    if cmd in ("викторина", "квиз", "quiz"):
        if not is_chat:
            return await message.answer("Викторина проводится только в беседах!")

        if message.peer_id in ACTIVE_QUIZZES:
            existing = ACTIVE_QUIZZES[message.peer_id]
            if time.time() - existing["ts"] <= 90:
                return await message.answer(
                    f"🧠 В беседе уже идёт викторина!\n"
                    f"❓ Вопрос: {existing['q']}\n"
                    f"🏆 Награда: {existing['reward']:,} 🌑. Напишите ответ прямо в чат!"
                )

        q_item = random.choice(QUIZ_QUESTIONS)
        ACTIVE_QUIZZES[message.peer_id] = {
            "q": q_item["q"],
            "answers": [a.lower().strip() for a in q_item["answers"]],
            "reward": 5000,
            "ts": time.time(),
        }

        quiz_text = (
            f"🧠 БЛИЦ-ВИКТОРИНА MOXXI!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"❓ Вопрос: {q_item['q']}\n\n"
            f"🏆 Награда за скорость: +5 000 🌑 и +40 XP!\n"
            f"⏱ У вас есть 90 секунд. Первый, кто напишет правильный ответ в чат — побеждает!"
        )
        return await message.answer(quiz_text)

    # ═══════════════════════════════════════════════════════════
    # 20. 🎁 МАГАЗИН И ОТПРАВКА ПОДАРКОВ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("подарки", "магазин_подарков", "gifts", "витрина"):
        gift_lines = []
        for gid, ginfo in db.GIFT_CATALOG.items():
            gift_lines.append(f"{gid}. {ginfo['name']} — {ginfo['cost']:,} 🌑")
        text = (
            f"🎁 МАГАЗИН ПОДАРКОВ MOXXI\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(gift_lines) +
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💌 Подарить: «подарить [номер 1-5] @юзер [записка]»\n"
            f"Пример: «подарить 1 @durov Ты лучший!»"
        )
        return await message.answer(text)

    if cmd in ("подарить", "отправить_подарок", "gift"):
        target_id = extract_target_vk_id(message, args)
        if not target_id or target_id == user_id or target_id < 0:
            return await message.answer("Укажите получателя подарка: «подарить [номер 1-5] @юзер [записка]»")

        p_args = args.split()
        g_num = None
        for a in p_args:
            if a in db.GIFT_CATALOG:
                g_num = a
                break

        if not g_num:
            return await message.answer("Укажите номер подарка (1–5)! Напишите «подарки» для просмотра каталога.")

        gdata = db.GIFT_CATALOG[g_num]
        cost = gdata["cost"]
        cur_bal = user_db.get("balance", 0)
        if cur_bal < cost:
            return await message.answer(f"❌ Недостаточно средств! Подарок стоит {cost:,} 🌑.")

        note = re.sub(r"\[(?:id|club)\d+\|[^\]]+\]", "", args)
        note = re.sub(r"@id\d+", "", note)
        note = note.replace(g_num, "", 1).strip()
        if not note:
            note = "С наилучшими пожеланиями от MOXXI!"

        t_db_uid = to_db_uid(target_id)
        await db.add_balance(db_uid, -cost)
        await db.send_gift(db_uid, t_db_uid, gdata["id"], gdata["name"], note)
        await db.add_rep(db_uid, 1)

        t_name = await get_display_name(target_id)
        return await message.answer(
            f"🎁 ПРЕКРАСНЫЙ ПОДАРОК!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"От: {user_display}\n"
            f"Кому: {t_name}\n"
            f"Подарок: {gdata['name']}\n"
            f"💌 Записка: «{note}»\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Подарок бережно выставлен на полку получателя в «профиль»!"
        )

    # ═══════════════════════════════════════════════════════════
    # 21. 🏦 ГОСУДАРСТВЕННЫЙ БАНК MOXXI
    # ═══════════════════════════════════════════════════════════
    if cmd in ("банк", "вклад", "депозит"):
        sub_parts = args.split()
        sub_cmd = sub_parts[0].lower() if sub_parts else ""

        if sub_cmd in ("положить", "внести", "деп", "+"):
            amount_str = sub_parts[1] if len(sub_parts) > 1 else ""
            cur_bal = user_db.get("balance", 0)
            amount = parse_amount(amount_str, max_val=cur_bal)
            if not amount or amount <= 0:
                return await message.answer("Пример: «банк положить 5000» или «банк положить все».")
            if cur_bal < amount:
                return await message.answer("❌ Недостаточно средств на руках!")

            ok = await db.deposit_to_bank(db_uid, amount)
            if ok:
                return await message.answer(
                    f"🏦 ВКЛАД ПОПОЛНЕН!\n"
                    f"Внесено на депозит: +{amount:,} 🌑\n"
                    f"🏛 В банке: {user_db.get('bank', 0) + amount:,} 🌑\n"
                    f"💰 На руках: {cur_bal - amount:,} 🌑\n"
                    f"📈 Доход: 5% в сутки начисляется автоматически!"
                )
            return await message.answer("Ошибка внесения вклада.")

        elif sub_cmd in ("снять", "вывести", "забрать", "-"):
            amount_str = sub_parts[1] if len(sub_parts) > 1 else ""
            cur_bank = user_db.get("bank", 0)
            amount = parse_amount(amount_str, max_val=cur_bank)
            if not amount or amount <= 0:
                return await message.answer("Пример: «банк снять 5000» или «банк снять все».")
            if cur_bank < amount:
                return await message.answer("❌ Недостаточно средств на банковском счёте!")

            ok = await db.withdraw_from_bank(db_uid, amount)
            if ok:
                return await message.answer(
                    f"🏦 ВЫВОД ИЗ БАНКА!\n"
                    f"Снято со счёта: -{amount:,} 🌑\n"
                    f"💰 На руках: {user_db.get('balance', 0) + amount:,} 🌑\n"
                    f"🏛 В банке: {cur_bank - amount:,} 🌑"
                )
            return await message.answer("Ошибка снятия вклада.")

        else:
            interest = await db.apply_bank_interest(db_uid)
            u_fresh = await db.get_user(db_uid) or user_db
            bal = u_fresh.get("balance", 0)
            bnk = u_fresh.get("bank", 0)
            int_str = f"🎉 Начислены суточные проценты: +{interest:,} 🌑!\n" if interest > 0 else ""

            kb_bank = Keyboard(inline=True)
            kb_bank.add(Text("📥 Банк положить 10000"), color=KeyboardButtonColor.POSITIVE)
            kb_bank.add(Text("📥 Банк положить все"), color=KeyboardButtonColor.POSITIVE)
            kb_bank.row()
            kb_bank.add(Text("📤 Банк снять 10000"), color=KeyboardButtonColor.PRIMARY)
            kb_bank.add(Text("📤 Банк снять все"), color=KeyboardButtonColor.PRIMARY)

            bank_text = (
                f"🏦 ГОСУДАРСТВЕННЫЙ БАНК MOXXI 🏦\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Клиент: {user_display}\n"
                f"💰 Наличные на руках: {bal:,} 🌑\n"
                f"🏛 На вкладе в банке: {bnk:,} 🌑\n"
                f"📈 Доходность вклада: 5% в сутки (до 100,000 🌑/день)\n"
                f"{int_str}"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 Управляйте счетом кнопками ниже или напишите «банк положить/снять [сумма]»:"
            )
            return await message.answer(bank_text, keyboard=kb_bank.get_json())

    # ═══════════════════════════════════════════════════════════
    # 22. 💳 ДОНАТ, ПОПОЛНЕНИЕ И РЕАЛЬНЫЕ ДЕНЬГИ (ЮMONEY / ЮKASSA)
    # ═══════════════════════════════════════════════════════════
    if cmd in ("донат", "пополнить", "купить_монеты", "магазин_монет", "donate", "вип", "випы"):
        # Если указан номер товара
        p_arg = args.strip()
        num_m = re.search(r"\b([1-9])\b", p_arg)

        if num_m:
            prod_num = num_m.group(1)
            prod_info = payments.DONATE_PRODUCTS[prod_num]
            pkey = prod_info["key"]

            pay_url, yoomoney_url, pid, prod = await payments.create_rub_payment(db_uid, user_id, pkey)
            if not prod:
                return await message.answer("Ошибка создания платежа.")

            # Формируем ссылки
            links_str = ""
            if pay_url:
                links_str += f"💳 Оплата по СБП / Карте РФ (МИР, Visa, Mastercard):\n👉 {pay_url}\n\n"
            if yoomoney_url:
                links_str += f"🟣 Оплата через кошелёк ЮMoney:\n👉 {yoomoney_url}\n"

            card_text = (
                f"💳 СЧЁТ НА ОПЛАТУ ЗАКАЗА #{pid[:8]}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Товар: {prod['title']}\n"
                f"💵 Сумма к оплате: {prod['price_rub']} ₽\n"
                f"📝 {prod['desc']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{links_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ После завершения оплаты нажмите «проверить_оплату {pid}» (или бот выдаст товар автоматически в течение 10 секунд)!"
            )
            return await message.answer(card_text)

        # Вывод каталога доната
        lines = [
            f"💎 ОФИЦИАЛЬНЫЙ ДОНАТ-МАГАЗИН MOXXI 💎",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"Принимаем: 🇷🇺 СБП (любые банки без комиссии), Карты РФ (МИР), ЮMoney, SberPay, Т-Банк.",
            f"━━━━━━━━━━━━━━━━━━━━",
        ]
        for num, p in payments.DONATE_PRODUCTS.items():
            lines.append(f"{num}. {p['title']} — {p['price_rub']} ₽ ({p['desc']})")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 Чтобы купить товар, напишите:")
        lines.append("«донат [номер 1-9]» (например: «донат 3» для 1 000 000 🌑)")
        lines.append("• Проверить платёж: «проверить_оплату [код]»")
        return await message.answer("\n".join(lines))

    if cmd in ("проверить_оплату", "проверить", "check_pay"):
        pid = args.strip()
        if not pid:
            return await message.answer("Укажите ID платежа! Пример: «проверить_оплату 2f4b...»")

        st = await payments.get_payment_status(pid)
        if st == "succeeded":
            ok, reward_desc, prod = await payments.fulfill_payment(pid)
            if ok:
                return await message.answer(
                    f"🎉 ✨ ОПЛАТА УСПЕШНО ЗАВЕРШЕНА! ✨ 🎉\n"
                    f"Товар «{prod['title']}» успешно активирован на вашем аккаунте!\n"
                    f"Начислено: {reward_desc}.\n"
                    f"Спасибо за поддержку проекта!"
                )
            return await message.answer("Этот платёж уже был успешно активирован ранее!")
        elif st in ("pending", "waiting_for_capture"):
            return await message.answer(
                f"⏳ Платёж #{pid[:8]} ещё в процессе обработки банком. Завершите оплату по ссылке и попробуйте снова через минуту!"
            )
        return await message.answer(f"❌ Платёж #{pid[:8]} не найден или был отменён.")

    # ═══════════════════════════════════════════════════════════
    # 23. 🔨 АУКЦИОН В БЕСЕДЕ (VK AUCTIONS)
    # ═══════════════════════════════════════════════════════════
    if cmd in ("аукцион", "лоты", "аук", "рынок"):
        sub_p = args.split()
        sub_c = sub_p[0].lower() if sub_p else ""

        if sub_c in ("выставить", "создать", "+лот"):
            # Выставление лота
            p_args = sub_p[1:]
            if len(p_args) < 2:
                return await message.answer(
                    "Формат: «аукцион выставить [название] [цена] [мин_шаг] [минуты]»\n"
                    "Пример: «аукцион выставить BMW_M5 100000 10000 15»"
                )

            item_title = p_args[0].replace("_", " ")
            start_price = parse_amount(p_args[1])
            min_step = parse_amount(p_args[2]) if len(p_args) > 2 else 500
            dur_mins = int(p_args[3]) if len(p_args) > 3 and p_args[3].isdigit() else 15
            dur_mins = max(3, min(120, dur_mins))

            if not start_price or start_price < 500:
                return await message.answer("Минимальная начальная цена: 500 🌑!")
            if not min_step or min_step < 100:
                min_step = 500

            lot_id = await db.create_vk_auction(
                chat_id=message.peer_id,
                seller_id=db_uid,
                seller_name=user_display,
                item_name=item_title,
                start_price=start_price,
                min_step=min_step,
                duration_sec=dur_mins * 60,
                item_type="custom"
            )

            ann_text = (
                f"📢 🔨 НОВЫЙ ЛОТ НА АУКЦИОНЕ! 🔨 📢\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Лот #{lot_id}: {item_title}\n"
                f"👤 Продавец: {user_display}\n"
                f"💰 Начальная ставка: {start_price:,} 🌑\n"
                f"📈 Минимальный шаг: +{min_step:,} 🌑\n"
                f"⏳ Длительность: {dur_mins} минут\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Чтобы сделать ставку, напишите в этот чат:\n"
                f"«ставка {lot_id} [сумма]» (например: «ставка {lot_id} {start_price + min_step}»)"
            )
            return await message.answer(ann_text)

        # Вывод активных лотов в этом чате
        active_lots = await db.get_active_vk_auctions(chat_id=message.peer_id)
        if not active_lots:
            # Если в этом чате нет, показываем глобальные
            active_lots = await db.get_active_vk_auctions()

        if not active_lots:
            return await message.answer(
                f"🔨 АУКЦИОН В БЕСЕДЕ\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"В данный момент нет активных торгов!\n\n"
                f"💡 Вы можете выставить свой лот:\n"
                f"«аукцион выставить [название] [цена] [шаг] [минуты]»\n"
                f"Пример: «аукцион выставить Счастливый_Талисман 5000 500 15»"
            )

        lines = [
            f"🔨 АКТИВНЫЕ ЛОТЫ АУКЦИОНА 🔨",
            f"━━━━━━━━━━━━━━━━━━━━",
        ]
        now = int(time.time())
        for lot in active_lots:
            rem = max(0, lot["ends_at"] - now)
            rm = rem // 60
            rs = rem % 60
            leader_str = lot["leader_name"] if lot["leader_id"] > 0 else "Нет ставок"
            lines.append(
                f"📦 Лот #{lot['id']}: {lot['item_name']}\n"
                f"👤 Продавец: {lot['seller_name']}\n"
                f"💰 Текущая ставка: {lot['current_bid']:,} 🌑\n"
                f"👑 Лидер: {leader_str}\n"
                f"📈 Мин. шаг: +{lot['min_step']:,} 🌑 | ⏳ Осталось: {rm} мин {rs} сек\n"
            )

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 Сделать ставку: «ставка [номер_лота] [сумма]»")
        lines.append("💡 Создать лот: «аукцион выставить [товар] [цена] [шаг] [мин]»")
        return await message.answer("\n".join(lines))

    if cmd in ("ставка", "поставить", "bid"):
        sub_p = args.split()
        if len(sub_p) < 2:
            return await message.answer("Формат ставки: «ставка [номер_лота] [сумма]»\nПример: «ставка 1 25000»")

        if not sub_p[0].isdigit():
            return await message.answer("Укажите номер лота! Пример: «ставка 1 25000»")

        lot_id = int(sub_p[0])
        amount = parse_amount(sub_p[1])
        if not amount or amount <= 0:
            return await message.answer("Укажите корректную сумму ставки!")

        ok, msg, updated_lot, prev_leader = await db.place_vk_bid(
            auction_id=lot_id,
            bidder_id=db_uid,
            bidder_name=user_display,
            bid_amount=amount
        )

        if not ok:
            return await message.answer(f"❌ {msg}")

        prev_refund_msg = ""
        if prev_leader:
            prev_refund_msg = f"\n💸 Предыдущему лидеру {prev_leader['name']} возвращена ставка {prev_leader['amount']:,} 🌑 на баланс."

        bid_ann = (
            f"🔨 СТАВКА ПОВЫШЕНА! 🔨\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Лот #{lot_id}: {updated_lot['item_name']}\n"
            f"👑 Новый лидер: {user_display}\n"
            f"💰 Сумма ставки: {amount:,} 🌑\n"
            f"⏳ Время продлено (антиснайпер): аукцион продолжается!{prev_refund_msg}"
        )
        return await message.answer(bid_ann)

    if cmd in ("поддержка", "тикет", "ticket", "баг", "ошибка", "репорт", "жалоба", "идея", "предложение"):
        if not args:
            return await message.answer(
                "🆘 Служба заботы и поддержки MOXXI (ВКонтакте):\n\n"
                "• Чтобы сообщить о проблеме или баге:\n"
                "  👉 Напишите: «поддержка [описание]» или «баг [описание]»\n\n"
                "• Чтобы предложить крутую идею или улучшение:\n"
                "  👉 Напишите: «идея [текст идеи]»\n\n"
                "• Наш Discord сервер: https://discord.gg/7hDq4R2q\n"
                "• Telegram сообщество: https://t.me/moxxi_chat"
            )
        fn, ln = await get_vk_user_info(user_id)
        user_name = f"{fn} {ln}".strip()
        is_idea = cmd in ("идея", "предложение")
        is_bug = cmd in ("баг", "ошибка", "репорт", "жалоба")
        cat = "💡 Идея / Предложение" if is_idea else ("🛠 Баг / Ошибка" if is_bug else "Общее")

        t_id = await db.create_support_ticket(db_uid, user_name, args, status="open", platform="vk", platform_peer_id=message.peer_id)
        await notify_telegram_about_ticket(t_id, user_id, user_name, args, category=cat)
        await notify_discord_about_ticket(t_id, user_id, user_name, args, category=cat)

        icon = "💡" if is_idea else ("🛠" if is_bug else "🆘")
        label = "Идея" if is_idea else ("Багрепорт" if is_bug else "Тикет")
        return await message.answer(
            f"{icon} {label} #{t_id} успешно принят!\n\n"
            f"📝 Обращение передано дежурной администрации в Telegram и Discord. "
            f"Ответ придёт вам прямо в этот диалог!"
        )

    # Если обращение адресовано Мокси как ИИ
    if ai_match:
        question = ai_match.group(1).strip()
        fn, _ = await get_vk_user_info(user_id)
        ai_resp = await generate_moxxi_ai_reply(question, fn)
        return await message.answer(ai_resp)

    # Если в ЛС боту написали обычное сообщение (не команду) — отвечаем через ИИ Мокси с клавиатурой
    if not is_chat:
        fn, _ = await get_vk_user_info(user_id)
        ai_resp = await generate_moxxi_ai_reply(clean_txt, fn)
        return await message.answer(ai_resp, keyboard=get_main_keyboard(is_chat=False))


# ═══════════════════════════════════════════════════════════════
# 🚀 ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# 📢 АВТОСООБЩЕНИЯ О ПОДДЕРЖКЕ И ИДЕЯХ В VK (КАЖДЫЕ 3 ЧАСА)
# ═══════════════════════════════════════════════════════════════

async def vk_support_broadcast_loop():
    """Фоновая рассылка каждые 8 часов во все активные беседы ВКонтакте."""
    log.info("Запущен воркер автосообщений техподдержки и идей ВКонтакте (интервал: 8 часов)...")
    await asyncio.sleep(60)
    while True:
        try:
            now = int(time.time())
            interval = 8 * 3600  # 8 часов = 28800 секунд
            chats = await db.get_all_vk_chats()

            broadcast_text = (
                "💜✨ СЛУЖБА ЗАБОТЫ И ПОДДЕРЖКИ MOXXI ✨💜\n"
                "──────────────────────────────────\n"
                "Нашли баг, ошибку или хотите предложить крутую идею для обновления?\n"
                "Мы всегда на связи и ценим каждого игрока нашего сообщества!\n\n"
                "📝 Как обратиться к разработчикам и администрации:\n"
                "• 🆘 Сообщить о баге или проблеме:\n"
                "  👉 Напишите в беседу: поддержка [описание проблемы / бага]\n"
                "  (или: баг [описание] / репорт [текст])\n\n"
                "• 💡 Предложить новую идею или фичу:\n"
                "  👉 Напишите в беседу: идея [текст вашей идеи]\n\n"
                "🌐 Официальные каналы связи:\n"
                "• 🎮 Discord Сервер Поддержки: https://discord.gg/7hDq4R2q\n"
                "• ✈️ Telegram Чат Игроков: https://t.me/moxxi_chat\n"
                "• 🎫 ЛС Сообщества: напишите «поддержка» прямо сюда!\n\n"
                "⚡️ Все ваши обращения мгновенно отправляются дежурной команде модераторов в Telegram и Discord! ❤️"
            )

            for ch in chats:
                peer_id = ch["peer_id"]
                last_ts = ch.get("last_broadcast_ts") or 0
                if (now - last_ts) >= interval:
                    try:
                        await bot.api.messages.send(
                            peer_id=peer_id,
                            message=broadcast_text,
                            random_id=random.randint(1, 100000000)
                        )
                        await db.update_vk_chat_broadcast_ts(peer_id, now)
                        await asyncio.sleep(1.0)
                    except Exception as e:
                        log.debug("Ошибка авторассылки в беседу VK %d: %s", peer_id, e)

        except Exception as e:
            log.warning("Исключение в vk_support_broadcast_loop: %s", e)
        await asyncio.sleep(60)


async def yookassa_payment_poller():
    """Фоновый воркер: каждые 10 секунд проверяет статус ожидающих платежей и выдаёт заказы."""
    log.info("Запуск фонового поллера платежей ЮKassa/ЮMoney...")
    while True:
        try:
            await asyncio.sleep(10)
            async with db.conn().execute(
                "SELECT id, user_id FROM yookassa_payments WHERE status = 'pending' ORDER BY created_at DESC LIMIT 10"
            ) as cur:
                rows = await cur.fetchall()

            for r in rows:
                pid = r["id"]
                st = await payments.get_payment_status(pid)
                if st == "succeeded":
                    ok, reward_desc, prod = await payments.fulfill_payment(pid)
                    if ok:
                        vk_uid = from_db_uid(r["user_id"])
                        try:
                            await bot.api.messages.send(
                                user_id=vk_uid,
                                random_id=random.randint(1, 2_000_000_000),
                                message=(
                                    f"🎉 ✨ ОПЛАТА УСПЕШНО ЗАВЕРШЕНА! ✨ 🎉\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"📦 Товар: {prod['title']}\n"
                                    f"💰 Начислено: {reward_desc}\n\n"
                                    f"👑 Спасибо за поддержку MOXXI! Приятной игры!"
                                )
                            )
                        except Exception as ex:
                            log.warning("Не удалось отправить сообщение об оплате пользователю VK %d: %s", vk_uid, ex)
                elif st in ("canceled", "failed"):
                    await db.conn().execute("UPDATE yookassa_payments SET status = ? WHERE id = ?", (st, pid))
                    await db.conn().commit()
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.warning("Ошибка в yookassa_payment_poller: %s", e)
            await asyncio.sleep(5)


async def auction_tick_worker():
    """Фоновый воркер аукциона: завершает истекшие лоты и отправляет уведомление в чат."""
    log.info("Запуск фонового таймера аукционов беседы...")
    while True:
        try:
            await asyncio.sleep(5)
            now = int(time.time())
            async with db.conn().execute(
                "SELECT * FROM vk_auctions WHERE status = 'active' AND ends_at <= ?",
                (now,)
            ) as cur:
                exp_lots = await cur.fetchall()

            for lot_row in exp_lots:
                lot = dict(lot_row)
                lid = lot["id"]
                cid = lot["chat_id"]
                fin_lot = await db.finish_vk_auction(lid)
                if not fin_lot:
                    continue

                item_name = fin_lot["item_name"]
                leader_id = fin_lot["leader_id"]
                leader_name = fin_lot["leader_name"]
                seller_id = fin_lot["seller_id"]
                seller_name = fin_lot["seller_name"]
                final_bid = fin_lot["current_bid"]

                if leader_id > 0:
                    win_text = (
                        f"🏆 АУКЦИОН ЗАВЕРШЁН! 🔨\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📦 Лот #{lid}: {item_name}\n"
                        f"👑 Победитель: {leader_name}\n"
                        f"💰 Финальная ставка: {final_bid:,} 🌑\n"
                        f"👤 Продавец: {seller_name} (получил выплату с комиссией 5%)\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎉 Поздравляем победителя аукциона!"
                    )
                else:
                    win_text = (
                        f"⌛️ АУКЦИОН ЗАВЕРШЁН 🔨\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📦 Лот #{lid}: {item_name}\n"
                        f"Ставок не поступило. Лот снят с торгов и возвращён продавцу {seller_name}."
                    )

                try:
                    await bot.api.messages.send(
                        peer_id=cid,
                        random_id=random.randint(1, 2_000_000_000),
                        message=win_text
                    )
                except Exception as ex:
                    log.warning("Не удалось отправить завершение аукциона в peer_id %d: %s", cid, ex)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.warning("Ошибка в auction_tick_worker: %s", e)
            await asyncio.sleep(5)


async def main():
    print("""
=====================================================
  🌟 MOXXI 3.0 — ULTIMATE MULTI-FEATURE VK BOT 🌟
  10 Ranks • Clans • Bosses • Marriages • Cars • Biz
=====================================================
    """)
    await db.init()
    log.info("Подключение к единой базе данных SQLite успешно.")

    try:
        group_info = await bot.api.groups.get_by_id(group_id=VK_GROUP_ID)
        g_name = group_info.groups[0].name
        log.info("Успешное подключение к группе VK: %s (ID: %d)", g_name, VK_GROUP_ID)
    except Exception as e:
        log.error("Ошибка проверки группы VK: %s", e)

    asyncio.create_task(yookassa_payment_poller())
    asyncio.create_task(vk_support_broadcast_loop())
    asyncio.create_task(auction_tick_worker())
    log.info("Запуск фоновых воркеров (ЮКасса платежи + Аукционы) успешен.")

    while True:
        try:
            log.info("Запуск LongPoll прослушивания сообщений ВКонтакте...")
            await bot.run_polling()
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("LongPoll ВКонтакте временно отключился (%s). Переподключение через 5 сек...", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("VK бот остановлен.")
