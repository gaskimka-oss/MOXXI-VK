"""💳 Модуль монетизации и реальных платежей MOXXI (ЮKassa + ЮMoney).

Поддерживает:
- Приём оплаты в рублях через СБП, Банковские карты РФ (МИР, Visa, Mastercard), SberPay, Т-Банк и кошельки ЮMoney.
- Автоматическую проверку статусов платежей через YooKassa REST API v3.
- Мгновенное начисление монет, кристаллов и VIP-статусов.
- Оповещение покупателя в ВК и создателя бота в Telegram / VK.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import aiosqlite
from dotenv import load_dotenv

import db

load_dotenv()

log = logging.getLogger("moxxibot.vk.payments")

SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "1475484").strip()
SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "live_R-Njww4kRciNS-0nNsViJz7Vn7JaRnLDvnJxtz90mLA").strip()
YOOMONEY_RECEIVER = os.getenv("YOOMONEY_RECEIVER", "4100118949581720").strip()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_OWNER_ID = int(os.getenv("TG_OWNER_ID", "8036974481"))
TG_OWNERS = [int(x.strip()) for x in os.getenv("TG_OWNERS", "8036974481,8412527198").split(",") if x.strip().isdigit()]

API_URL = "https://api.yookassa.ru/v3/payments"

# Каталог донатных товаров
DONATE_PRODUCTS: dict[str, dict] = {
    "1": {
        "key": "coins_50k",
        "title": "🍬 50 000 🌑 монет",
        "price_rub": 5.0,
        "type": "coins",
        "amount": 50_000,
        "desc": "Стартовый набор монет для игр и шахты",
    },
    "2": {
        "key": "coins_250k",
        "title": "🎁 250 000 🌑 монет",
        "price_rub": 10.0,
        "type": "coins",
        "amount": 250_000,
        "desc": "Солидный куш для открытия кейсов и казино",
    },
    "3": {
        "key": "coins_1m",
        "title": "💰 1 000 000 🌑 монет (1кк)",
        "price_rub": 15.0,
        "type": "coins",
        "amount": 1_000_000,
        "desc": "Миллион монет: хватит на покупку бизнеса и машины",
    },
    "4": {
        "key": "coins_3m",
        "title": "💎 3 000 000 🌑 монет (3кк)",
        "price_rub": 35.0,
        "type": "coins",
        "amount": 3_000_000,
        "desc": "Пакет инвестора: развитие клана и предприятий",
    },
    "5": {
        "key": "coins_7m",
        "title": "🚀 7 000 000 🌑 монет (7кк)",
        "price_rub": 75.0,
        "type": "coins",
        "amount": 7_000_000,
        "desc": "Огромный капитал для суперкаров и побед в аукционе",
    },
    "6": {
        "key": "coins_20m",
        "title": "👑 20 000 000 🌑 монет (20кк)",
        "price_rub": 199.0,
        "type": "coins",
        "amount": 20_000_000,
        "desc": "Куш олигарха: вы станете богатейшим игроком бесед",
    },
    "7": {
        "key": "vip_30",
        "title": "⭐️ VIP-статус (30 дней)",
        "price_rub": 39.0,
        "type": "vip",
        "level": 1,
        "days": 30,
        "desc": "+50% доход с шахты, крит x3.0 по боссу, 1 несгораемый щит от варна",
    },
    "8": {
        "key": "vipplus_30",
        "title": "🌟 VIP+ Diamond (30 дней)",
        "price_rub": 79.0,
        "type": "vip",
        "level": 2,
        "days": 30,
        "desc": "+150% доход, суперкрит x3.5, еженедельный кейс, золотой префикс в чате",
    },
    "9": {
        "key": "crystals_100",
        "title": "💎 100 Кристаллов",
        "price_rub": 49.0,
        "type": "crystals",
        "amount": 100,
        "desc": "Премиальная валюта для прокачки питомцев и уникальных авто",
    },
}

def _auth_header() -> str:
    raw = f"{SHOP_ID}:{SECRET_KEY}".encode("utf-8")
    return f"Basic {base64.b64encode(raw).decode('utf-8')}"

def is_configured() -> bool:
    return bool(SHOP_ID and SECRET_KEY)

async def notify_owner_telegram(message_text: str) -> None:
    """Отправляет уведомление владельцу бота в Telegram."""
    if not TG_BOT_TOKEN or not TG_OWNERS:
        return
    for owner_id in TG_OWNERS:
        try:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": owner_id,
                "text": message_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=5)
        except Exception as e:
            log.warning("Ошибка уведомления Telegram владельца %d: %s", owner_id, e)

async def create_rub_payment(db_uid: int, vk_user_id: int, item_key: str) -> tuple[str | None, str | None, str | None, dict | None]:
    """Создаёт платёж и возвращает (yookassa_url, yoomoney_url, payment_id, product_info)."""
    prod = None
    for p in DONATE_PRODUCTS.values():
        if p["key"] == item_key:
            prod = p
            break
    if not prod:
        return None, None, None, None

    price = prod["price_rub"]
    amount_val = f"{price:.2f}"
    payment_id = str(uuid.uuid4())

    yoomoney_quickpay_url = (
        f"https://yoomoney.ru/quickpay/confirm.xml?"
        f"receiver={YOOMONEY_RECEIVER}&quickpay-form=shop&targets={urllib.parse.quote(prod['title'])}"
        f"&paymentType=SB&sum={amount_val}&label={payment_id}"
    )

    pay_url = None
    if is_configured():
        payload = {
            "amount": {"value": amount_val, "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://vk.com/club243066051"
            },
            "capture": True,
            "description": f"MOXXI VK: {prod['title']} (VK ID {vk_user_id})",
            "metadata": {
                "db_uid": db_uid,
                "vk_user_id": vk_user_id,
                "item_key": item_key,
                "platform": "vk"
            }
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": payment_id,
            "Authorization": _auth_header(),
        }
        req = urllib.request.Request(API_URL, data=body, headers=headers)

        def _req():
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err = e.read().decode("utf-8", errors="ignore")
                log.error("YooKassa HTTP %s: %s", e.code, err)
                return None
            except Exception as e:
                log.error("YooKassa net err: %s", e)
                return None

        res = await asyncio.to_thread(_req)
        if res:
            remote_id = res.get("id")
            conf = res.get("confirmation", {})
            pay_url = conf.get("confirmation_url")
            if remote_id:
                payment_id = remote_id

    # Сохраняем в таблицу yookassa_payments
    now = int(time.time())
    await db.conn().execute(
        """INSERT INTO yookassa_payments (id, user_id, item_key, amount_rub, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'pending', ?, ?)
           ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at""",
        (payment_id, db_uid, item_key, price, now, now)
    )
    await db.conn().commit()

    return pay_url, yoomoney_quickpay_url, payment_id, prod

async def get_payment_status(payment_id: str) -> str | None:
    """Запрашивает статус платежа из API ЮKassa."""
    if not is_configured():
        return None
    url = f"{API_URL}/{payment_id}"
    headers = {"Authorization": _auth_header()}
    req = urllib.request.Request(url, headers=headers)

    def _req():
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            log.warning("Ошибка проверки платежа %s: %s", payment_id, e)
            return None

    res = await asyncio.to_thread(_req)
    if res and "status" in res:
        return res["status"]
    return None

async def fulfill_payment(payment_id: str) -> tuple[bool, str, dict]:
    """Выдаёт товар покупателю после успешной оплаты."""
    async with db.conn().execute("SELECT * FROM yookassa_payments WHERE id = ?", (payment_id,)) as cur:
        row = await cur.fetchone()
        if not row:
            return False, "Платёж не найден в базе данных.", {}
        if row["status"] == "succeeded":
            return False, "Этот платёж уже был успешно активирован ранее!", {}

    db_uid = row["user_id"]
    item_key = row["item_key"]
    prod = None
    for p in DONATE_PRODUCTS.values():
        if p["key"] == item_key:
            prod = p
            break
    if not prod:
        return False, "Неизвестный тип товара.", {}

    now = int(time.time())
    await db.conn().execute(
        "UPDATE yookassa_payments SET status = 'succeeded', updated_at = ? WHERE id = ?",
        (now, payment_id)
    )
    await db.conn().commit()

    p_type = prod.get("type")
    reward_desc = ""

    if p_type == "coins":
        amt = prod["amount"]
        await db.add_balance(db_uid, amt)
        await db.add_xp(db_uid, int(prod["price_rub"] * 10))
        reward_desc = f"+{amt:,} 🌑 монет"
    elif p_type == "crystals":
        amt = prod["amount"]
        await db.add_crystals(db_uid, amt)
        await db.add_xp(db_uid, int(prod["price_rub"] * 10))
        reward_desc = f"+{amt:,} 💎 кристаллов"
    elif p_type == "vip":
        lvl = prod.get("level", 1)
        days = prod.get("days", 30)
        # Сохраняем VIP статус в users
        await db.conn().execute(
            """UPDATE users SET verified = MAX(verified, ?),
               bank_ts = CASE WHEN bank_ts = 0 THEN ? ELSE bank_ts END
               WHERE user_id = ?""",
            (lvl, now, db_uid)
        )
        await db.conn().commit()
        await db.add_xp(db_uid, 500)
        reward_desc = f"Премиум статус: {prod['title']}"

    # Оповещаем владельца проекта в Telegram
    vk_uid = db_uid - 70_000_000_000 if db_uid >= 70_000_000_000 else db_uid
    tg_alert = (
        f"💸 <b>НОВЫЙ ДОНАТ В VK-БОТЕ MOXXI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Покупатель: VK ID <code>{vk_uid}</code> (https://vk.com/id{vk_uid})\n"
        f"📦 Товар: <b>{prod['title']}</b>\n"
        f"💰 Оплачено: <b>{prod['price_rub']} ₽</b>\n"
        f"💳 Платёж: <code>{payment_id}</code>\n"
        f"🎉 Начислено: <b>{reward_desc}</b>"
    )
    asyncio.create_task(notify_owner_telegram(tg_alert))

    return True, reward_desc, prod
