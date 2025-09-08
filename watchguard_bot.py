import json
import logging
import re
import asyncio
import os
from datetime import datetime
from typing import Dict, Tuple, Optional, List
import pytz
from dateutil.parser import parse as parse_date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update, BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    ApplicationHandlerStop,
)
from data_manager import get_shared_data_manager, DataChangeEvent


def load_config() -> Dict:
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("config.json not found! Please configure the bot first.")
        return {}


def load_bot_config():
    try:
        config = load_config()
        return config.get("TOKEN"), config.get("CHAT_IDS", [])
    except Exception as e:
        print(f"Error loading bot config: {e}")
        return None, []


TOKEN, CHAT_ID = load_bot_config()
SERVERS_FILE = "servers.json"
DOMAINS_FILE = "domains.json"
SETTINGS_FILE = "settings.json"
TIMEZONE = "Asia/Tehran"

shared_dm = get_shared_data_manager()

STATUS_INDICATORS = {
    "expired": "🔴",
    "warning": "🟡",
    "safe": "🟢",
    "unknown": "⚪",
}

EMOJI_OPTIONS = [
    "🇺🇸",
    "🇬🇧",
    "🇩🇪",
    "🇫🇷",
    "🇨🇦",
    "🇦🇺",
    "🇮🇹",
    "🇪🇸",
    "🇳🇱",
    "🇸🇪",
    "🇷🇺",
    "🇨🇳",
    "🇯🇵",
    "🇰🇷",
    "🇧🇷",
    "🇮🇳",
    "🇹🇷",
    "🇫🇮",
    "🇳🇴",
    "🇩🇰",
]

LABEL_OPTIONS = []

(
    SELECT_REMOVE,
    SELECT_EDIT,
    EDIT_NAME,
    EDIT_DATE,
    EDIT_PRICE,
    EDIT_CURRENCY,
    EDIT_EMOJI,
    EDIT_CUSTOM_EMOJI,
    EDIT_LABEL,
    EDIT_CUSTOM_LABEL,
    EDIT_DATACENTER,
    ADD_NAME,
    ADD_DATE,
    ADD_PRICE,
    ADD_CURRENCY,
    ADD_EMOJI,
    ADD_CUSTOM_EMOJI,
    ADD_LABEL,
    ADD_CUSTOM_LABEL,
    ADD_DATACENTER,
    SETTINGS_MENU,
    SETTINGS_WARNING_DAYS,
    SETTINGS_NOTIFICATION_TIME,
    FILTER_STATUS,
    DOMAIN_SELECT_REMOVE,
    DOMAIN_SELECT_EDIT,
    DOMAIN_EDIT_NAME,
    DOMAIN_EDIT_DATE,
    DOMAIN_EDIT_PRICE,
    DOMAIN_EDIT_CURRENCY,
    DOMAIN_EDIT_REGISTRAR,
    DOMAIN_ADD_NAME,
    DOMAIN_ADD_DATE,
    DOMAIN_ADD_PRICE,
    DOMAIN_ADD_CURRENCY,
    DOMAIN_ADD_REGISTRAR,
    DOMAIN_ADD_LABEL,
    DOMAIN_ADD_CUSTOM_LABEL,
    EXPIRED_SERVER_ACTION,
    EXPIRED_DOMAIN_ACTION,
    MANAGE_LABELS,
    ADD_LABEL_NAME,
) = range(42)


def load_settings() -> Dict:
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}

    defaults = {
        "warning_days": 5,
        "notification_hour": 9,
        "notification_minute": 0,
        "daily_notifications": True,
        "labels": ["WatchGuard"],
        "version": "v1.0.0",
    }

    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value

    try:
        from version_util import read_version

        settings["version"] = read_version(settings.get("version", "v1.0.0"))
    except Exception:
        pass

    return settings


def save_settings(settings: Dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def load_labels() -> List[str]:
    try:

        if os.path.exists("labels.json"):
            with open("labels.json", "r", encoding="utf-8") as f:
                labels_data = json.load(f)

                if isinstance(labels_data, dict) and "labels" in labels_data:

                    labels = labels_data["labels"]
                elif isinstance(labels_data, list):

                    labels = labels_data
                else:
                    labels = []

                unique_labels = list(
                    set([label.strip() for label in labels if label and label.strip()])
                )
                unique_labels.sort()
                return unique_labels

        settings = load_settings()
        settings_labels = settings.get("labels", [])
        if isinstance(settings_labels, list) and settings_labels:
            return settings_labels

        return ["WatchGuard"]

    except Exception as e:
        logging.error(f"Error loading labels: {e}")

        return ["WatchGuard"]


def load_servers() -> Dict:
    return shared_dm.load_servers()


def save_servers(servers: Dict) -> None:
    shared_dm.save_servers(servers)


def load_domains() -> Dict:
    return shared_dm.load_domains()


def save_domains(domains: Dict) -> None:
    shared_dm.save_domains(domains)


def extract_price_and_currency(price_str: str) -> Tuple[float, str]:
    if not price_str or not isinstance(price_str, str):
        return 0.0, "USD"

    price_str = price_str.strip()
    currency_map = {"$": "USD", "€": "EUR"}
    currency = "USD"
    amount_str = price_str

    for symbol, code in currency_map.items():
        if price_str.startswith(symbol):
            currency = code
            amount_str = price_str[len(symbol) :]
            break

    number_match = re.search(r"[\d.]+", amount_str)
    if number_match:
        try:
            return float(number_match.group()), currency
        except ValueError:
            logging.warning(f"Invalid price format: {price_str}")
            return 0.0, currency
    return 0.0, currency


def calculate_total_costs(servers: Dict, domains: Dict) -> Dict[str, float]:
    totals = {
        "server_usd": 0.0,
        "server_eur": 0.0,
        "domain_usd": 0.0,
        "domain_eur": 0.0,
        "total_usd": 0.0,
        "total_eur": 0.0,
    }

    settings = load_settings()
    warning_days = settings.get("warning_days", 5)

    for info in servers.values():
        status, _ = get_server_status(info["date"], warning_days)
        if status == "expired":
            continue

        amount, currency = extract_price_and_currency(info.get("price", "0"))
        if currency == "USD":
            totals["server_usd"] += amount
        elif currency == "EUR":
            totals["server_eur"] += amount

    for info in domains.values():
        status, _ = get_server_status(info["date"], warning_days)
        if status == "expired":
            continue

        amount, currency = extract_price_and_currency(info.get("price", "0"))
        if currency == "USD":
            totals["domain_usd"] += amount
        elif currency == "EUR":
            totals["domain_eur"] += amount

    totals["total_usd"] = totals["server_usd"] + totals["domain_usd"]
    totals["total_eur"] = totals["server_eur"] + totals["domain_eur"]

    return totals


def format_status_text(days_diff: int) -> str:
    if days_diff < 0:
        return f"Expired ({abs(days_diff)} days ago)"
    elif days_diff == 0:
        return "⚠️ Expires today!"
    elif days_diff == 1:
        return "Expires tomorrow"
    return f"{days_diff} days remaining"


def get_server_status(renewal_date_str: str, warning_days: int = 5) -> Tuple[str, int]:
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            renew_dt = parse_date(renewal_date_str, dayfirst=False, yearfirst=True)
        except ValueError:
            logging.warning(f"Invalid date format: {renewal_date_str}")
            return "unknown", 0

        if renew_dt.tzinfo is None:
            renew_dt = tz.localize(renew_dt)

        days_diff = (renew_dt.date() - now.date()).days

        if days_diff < 0:
            return "expired", days_diff
        elif days_diff <= warning_days:
            return "warning", days_diff
        else:
            return "safe", days_diff

    except Exception as e:
        logging.error(f"Error in get_server_status: {e}")
        return "unknown", 0


def format_server_list(
    servers: Dict[str, Dict], filter_status: Optional[str] = None
) -> str:
    if not servers:
        return "⚠️ No servers defined"

    settings = load_settings()
    warning_days = settings.get("warning_days", 5)

    status_groups = {"expired": [], "warning": [], "safe": []}

    for key, info in servers.items():
        status, days_diff = get_server_status(info["date"], warning_days)

        if filter_status and status != filter_status:
            continue

        emoji = info.get("emoji", "")
        days_text = format_status_text(days_diff)
        label = info.get("label", "")

        if emoji and emoji.strip():
            server_name_display = f"{emoji} {key}"
        else:
            server_name_display = f"- {key}"

        server_info = (
            f"{server_name_display}\n"
            f"• **Renewal Date:** `{info['date']}`\n"
            f"• **Status:** `{days_text}`\n"
            f"• **Price:** `{info['price']}`\n"
            f"• **Datacenter:** `{info['datacenter']}`\n"
        )
        if label:
            server_info += f"• **Label:** `{label}`\n"

        if status in status_groups:
            status_groups[status].append((days_diff, server_info))

    lines = []
    for status, header_text in [
        ("warning", "🟡 Servers Near Expiration:"),
        ("safe", "🟢 Active Servers:"),
        ("expired", "🔴 Expired Servers:"),
    ]:
        if status_groups[status]:
            lines.append(f"**{header_text}**")
            lines.append("")

            sorted_servers = sorted(status_groups[status], key=lambda x: x[0])
            for _, server_text in sorted_servers:
                lines.append(server_text)
                lines.append("")

    return (
        "\n".join(lines).rstrip("\n")
        if lines
        else "⚠️ No servers found with this filter"
    )


def format_domain_list(
    domains: Dict[str, Dict], filter_status: Optional[str] = None
) -> str:
    if not domains:
        return "⚠️ No domains defined"

    settings = load_settings()
    warning_days = settings.get("warning_days", 5)

    status_groups = {"expired": [], "warning": [], "safe": []}

    for domain_name, info in domains.items():
        status, days_diff = get_server_status(info["date"], warning_days)

        if filter_status and status != filter_status:
            continue

        days_text = format_status_text(days_diff)
        emoji = info.get("emoji", "")
        label = info.get("label", "")

        if emoji and emoji.strip():
            domain_name_display = f"{emoji} {domain_name}"
        else:
            domain_name_display = f"- {domain_name}"

        domain_info = (
            f"{domain_name_display}\n"
            f"• **Renewal Date:** `{info['date']}`\n"
            f"• **Status:** `{days_text}`\n"
            f"• **Price:** `{info['price']}`\n"
            f"• **Registrar:** `{info['registrar']}`\n"
        )
        if label:
            domain_info += f"• **Label:** `{label}`\n"

        if status in status_groups:
            status_groups[status].append((days_diff, domain_info))

    lines = []
    for status, header_text in [
        ("warning", "🟡 Domains Near Expiration:"),
        ("safe", "🟢 Active Domains:"),
        ("expired", "🔴 Expired Domains:"),
    ]:
        if status_groups[status]:
            lines.append(f"**{header_text}**")
            lines.append("")

            sorted_domains = sorted(status_groups[status], key=lambda x: x[0])
            for _, domain_text in sorted_domains:
                lines.append(domain_text)
                lines.append("")

    return (
        "\n".join(lines).rstrip("\n")
        if lines
        else "⚠️ No domains found with this filter"
    )


def get_allowed_chat_ids() -> List[int]:
    try:
        cfg = load_config()
        ids = cfg.get("CHAT_IDS", []) or []
        cleaned: List[int] = []
        for cid in ids:
            try:
                cleaned.append(int(cid))
            except Exception:

                continue
        return cleaned
    except Exception:
        return []


async def auth_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        chat_id: Optional[int] = None
        if update and update.effective_chat:
            try:
                chat_id = int(update.effective_chat.id)
            except Exception:
                chat_id = None

        allowed = get_allowed_chat_ids()
        if chat_id is None or chat_id not in allowed:

            if chat_id is not None:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id, text="⛔️ Access denied"
                    )
                except Exception:
                    pass

            raise ApplicationHandlerStop
    except ApplicationHandlerStop:
        raise
    except Exception:

        raise ApplicationHandlerStop


async def _send_telegram_message(token: str, chat_ids: List[int], text: str) -> None:
    try:
        if not token or not chat_ids:
            return
        bot = Bot(token=token)
        for chat_id in chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id, text=text, parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Failed to send daily notification to {chat_id}: {e}")
    except Exception as e:
        logging.error(f"Error in _send_telegram_message: {e}")


def _build_daily_digest() -> Optional[str]:
    try:
        settings = load_settings()
        warning_days = settings.get("warning_days", 5)

        servers = load_servers()
        domains = load_domains()

        warning_servers = []
        expired_servers = []
        warning_domains = []
        expired_domains = []

        for name, info in servers.items():
            status, days_diff = get_server_status(info.get("date", ""), warning_days)
            if status == "warning":
                warning_servers.append((days_diff, name))
            elif status == "expired":
                expired_servers.append((days_diff, name))

        for name, info in domains.items():
            status, days_diff = get_server_status(info.get("date", ""), warning_days)
            if status == "warning":
                warning_domains.append((days_diff, name))
            elif status == "expired":
                expired_domains.append((days_diff, name))

        if not (
            warning_servers or expired_servers or warning_domains or expired_domains
        ):
            return None

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)

        lines: List[str] = []
        lines.append("🔔 Daily Expiration Summary")
        lines.append("")
        lines.append(f"Date: `{now.strftime('%Y-%m-%d %H:%M')}`")
        lines.append("")

        def render_section(title: str, items: List[Tuple[int, str]]):
            if not items:
                return
            lines.append(f"**{title}**")
            items_sorted = sorted(items, key=lambda x: x[0])
            for days_diff, name in items_sorted:

                lines.append(f"- {name} → `{format_status_text(days_diff)}`")
            lines.append("")

        render_section("🟡 Near Expiration (Servers)", warning_servers)
        render_section("🔴 Expired (Servers)", expired_servers)
        render_section("🟡 Near Expiration (Domains)", warning_domains)
        render_section("🔴 Expired (Domains)", expired_domains)

        return "\n".join(lines).rstrip("\n")
    except Exception as e:
        logging.error(f"Error building daily digest: {e}")
        return None


async def run_daily_notifications(force: bool = False) -> None:
    try:
        config = load_config()
        token = config.get("TOKEN")
        chat_ids = config.get("CHAT_IDS", [])
        if not token or not chat_ids:
            logging.warning(
                "Daily notifications skipped: missing TOKEN or CHAT_IDS in config.json"
            )
            return

        settings = load_settings()
        if not force and not settings.get("daily_notifications", True):
            logging.info("Daily notifications disabled in settings; skipping send")
            return

        digest = _build_daily_digest()
        if not digest:
            logging.info("No expiring or expired items to notify; skipping send")
            return

        await _send_telegram_message(token, chat_ids, digest)
        logging.info("Daily expiration summary sent")
    except Exception as e:
        logging.error(f"Error in run_daily_notifications: {e}")


async def notify_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await run_daily_notifications(force=True)

        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ Notification triggered",
                parse_mode="Markdown",
            )
    except Exception as e:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Error: {e}",
                parse_mode="Markdown",
            )
        logging.error(f"Error in notify_cmd: {e}")


def get_cost_summary() -> str:
    servers = load_servers()
    domains = load_domains()
    totals = calculate_total_costs(servers, domains)

    header = "──────── Cost Summary ────────"
    summary_lines = [header]

    server_costs = []
    if totals["server_usd"] > 0:
        server_costs.append(f"${totals['server_usd']:.2f}")
    if totals["server_eur"] > 0:
        server_costs.append(f"€{totals['server_eur']:.2f}")

    summary_lines.append(
        f"🖥 Servers: `{' + '.join(server_costs) if server_costs else '$0.00'}`"
    )

    domain_costs = []
    if totals["domain_usd"] > 0:
        domain_costs.append(f"${totals['domain_usd']:.2f}")
    if totals["domain_eur"] > 0:
        domain_costs.append(f"€{totals['domain_eur']:.2f}")

    summary_lines.append(
        f"🌐 Domains: `{' + '.join(domain_costs) if domain_costs else '$0.00'}`"
    )

    total_costs = []
    if totals["total_usd"] > 0:
        total_costs.append(f"${totals['total_usd']:.2f}")
    if totals["total_eur"] > 0:
        total_costs.append(f"€{totals['total_eur']:.2f}")

    if total_costs:
        summary_lines.append(f"📊 Total: `{' + '.join(total_costs)}`")
    else:
        summary_lines.append(f"📊 Total: `$0.00`")

    return "\n".join(summary_lines)


def currency_symbol(code: str) -> str:
    return {"USD": "$", "EUR": "€"}.get(code, "")


def normalize_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def format_date_input(date_str: str) -> str:
    try:

        date_str = date_str.strip()

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        try:
            dt = datetime.strptime(date_str, "%Y/%m/%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        try:
            dt = datetime.strptime(date_str, "%Y.%m.%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        try:
            dt = datetime.strptime(date_str, "%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        return date_str

    except Exception:
        return date_str


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_future_date(date_str: str) -> bool:
    try:
        renew_dt = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().date()
        return renew_dt.date() >= today
    except ValueError:
        return False


def is_valid_price(price_str: str) -> bool:
    try:
        if isinstance(price_str, str):
            price_str = (
                price_str.replace("$", "").replace("€", "").replace(",", "").strip()
            )
        float(price_str)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_name(name: str) -> bool:
    pattern = r"^[a-zA-Z0-9\-_\s]+$"
    return bool(re.match(pattern, name))


def is_valid_domain_name(domain: str) -> bool:
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    return re.match(pattern, domain) is not None and len(domain) <= 253


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    servers = load_servers()
    domains = load_domains()
    settings = load_settings()

    server_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in servers.values():
        status, _ = get_server_status(info["date"], settings.get("warning_days", 5))
        if status in server_status_counts:
            server_status_counts[status] += 1

    domain_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in domains.values():
        status, _ = get_server_status(info["date"], settings.get("warning_days", 5))
        if status in domain_status_counts:
            domain_status_counts[status] += 1

    total_servers = sum(server_status_counts.values())
    total_domains = sum(domain_status_counts.values())

    server_costs = 0
    for info in servers.values():
        price = info.get("price", 0)
        if isinstance(price, str):
            price = price.replace("$", "").replace("€", "").replace(",", "").strip()
        try:
            server_costs += float(price)
        except (ValueError, TypeError):
            server_costs += 0

    domain_costs = 0
    for info in domains.values():
        price = info.get("price", 0)
        if isinstance(price, str):
            price = price.replace("$", "").replace("€", "").replace(",", "").strip()
        try:
            domain_costs += float(price)
        except (ValueError, TypeError):
            domain_costs += 0

    total_costs = server_costs + domain_costs

    overview = (
        f"━━━━ WatchGuard • Version: {settings.get('version', 'v1.0.0')} ━━━━\n\n"
        f"🖥️ Servers ({total_servers})\n"
        f"🟡 {server_status_counts['warning']} Near Expiration\n"
        f"🟢 {server_status_counts['safe']} Active\n\n"
        f"🌐 Domains ({total_domains})\n"
        f"🟡 {domain_status_counts['warning']} Near Expiration\n"
        f"🟢 {domain_status_counts['safe']} Active\n\n"
        f"💰 Total Costs:\n"
        f"• Servers: `${server_costs:.2f}`\n"
        f"• Domains: `${domain_costs:.2f}`\n"
        f"• Total: `${total_costs:.2f}`"
    )

    keyboard = [
        [
            InlineKeyboardButton("🖥️ Manage Servers", callback_data="servers_menu"),
        ],
        [
            InlineKeyboardButton("🌐 Manage Domains", callback_data="domains_menu"),
        ],
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
    ]

    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(
            text=overview,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=overview,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    servers = load_servers()
    domains = load_domains()

    has_items = len(servers) > 0 or len(domains) > 0

    if not has_items:

        welcome_text = (
            "👋 **Welcome to Watch Guard!**\n\n"
            "🎯 Professional Server & Domain Renewal Management\n"
            "⚡️ Stay on top of your expirations – never miss a deadline again!\n\n"
            "**Quick Start:**\n"
            "• Add your servers and domains\n"
            "• Customize your notification preferences\n"
            "• Receive automatic renewal reminders\n\n"
            "**Available Commands:**\n"
            "• /start – Go to the main menu\n"
            "• /servers – Manage your servers\n"
            "• /domains – Manage your domains\n"
            "• /settings – Adjust system settings\n"
            "• /dashboard – View your dashboard\n"
            "• /notify – Show servers and domains nearing expiration"
        )

        keyboard = [
            [
                InlineKeyboardButton("🖥️ Manage Servers", callback_data="servers_menu"),
            ],
            [
                InlineKeyboardButton("🌐 Manage Domains", callback_data="domains_menu"),
            ],
            [
                InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            ],
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:

        await send_main_menu(update, context)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "back_main":
        await send_main_menu(update, context)
    elif query.data == "servers_menu":
        await servers_menu(update, context)
    elif query.data == "domains_menu":
        await domains_menu(update, context)
    elif query.data == "dashboard":
        await dashboard_menu(update, context)
    elif query.data == "settings":
        await settings_menu(update, context)
    elif query.data == "set_warning_days":
        await handle_set_warning_days(update, context)
    elif query.data == "set_notification_time":
        await handle_set_notification_time(update, context)
    elif query.data == "toggle_notifications":
        await handle_toggle_notifications(update, context)
    elif query.data == "manage_labels":
        await handle_manage_labels(update, context)
    elif query.data.startswith("warning_days_"):
        if query.data == "warning_days_custom":
            await handle_warning_days_custom(update, context)
        else:
            await handle_warning_days_selection(update, context)
    elif query.data.startswith("time_"):
        if query.data == "time_custom":
            await handle_time_custom(update, context)
        else:
            await handle_time_selection(update, context)
    elif query.data == "add_label":
        await handle_add_label(update, context)
    elif query.data == "remove_label":
        await handle_remove_label(update, context)
    elif query.data.startswith("remove_label_"):
        await handle_remove_label_confirm(update, context)

    elif query.data == "add_server":
        await handle_add_server(update, context)
    elif query.data == "edit_server":
        await handle_edit_server(update, context)
    elif query.data == "remove_server":
        await handle_remove_server(update, context)
    elif query.data.startswith("remove_server_confirm_"):
        await handle_remove_server_confirm(update, context)
    elif query.data.startswith("remove_server_final_"):
        await handle_remove_server_final(update, context)
    elif query.data == "filter_servers":
        await handle_filter_servers(update, context)

    elif query.data == "add_domain":
        await handle_add_domain(update, context)
    elif query.data == "edit_domain":
        await handle_edit_domain(update, context)
    elif query.data == "remove_domain":
        await handle_remove_domain(update, context)
    elif query.data.startswith("remove_domain_confirm_"):
        await handle_remove_domain_confirm(update, context)
    elif query.data.startswith("remove_domain_final_"):
        await handle_remove_domain_final(update, context)
    elif query.data == "filter_domains":
        await handle_filter_domains(update, context)

    elif query.data.startswith("filter_servers_"):
        await handle_server_filter_selection(update, context)
    elif query.data.startswith("filter_domains_"):
        await handle_domain_filter_selection(update, context)

    elif query.data.startswith("currency_"):
        await handle_currency_selection(update, context)

    elif query.data.startswith("domain_currency_"):
        await handle_domain_currency_selection(update, context)

    elif query.data.startswith("emoji_"):
        await handle_emoji_selection(update, context)

    elif query.data.startswith("domain_emoji_"):
        await handle_domain_emoji_selection(update, context)

    elif query.data.startswith("set_server_label_"):
        await handle_set_server_label(update, context)
    elif query.data == "skip_server_label":
        await handle_skip_server_label(update, context)

    elif query.data.startswith("set_domain_label_"):
        await handle_set_domain_label(update, context)
    elif query.data == "skip_domain_label":
        await handle_skip_domain_label(update, context)

    elif query.data.startswith("server_labels_page_"):
        await handle_server_labels_pagination(update, context)
    elif query.data.startswith("domain_labels_page_"):
        await handle_domain_labels_pagination(update, context)

    elif query.data.startswith("server_label_page_"):
        await handle_edit_server_label_pagination(update, context)
    elif query.data.startswith("domain_label_page_"):
        await handle_edit_domain_label_pagination(update, context)

    elif query.data.startswith("settings_label_page_"):
        await handle_settings_label_pagination(update, context)
    elif query.data.startswith("remove_label_page_"):
        await handle_remove_label_pagination(update, context)

    elif query.data.startswith("edit_currency_"):
        await handle_edit_currency_selection(update, context)

    elif query.data.startswith("edit_server_select_"):
        await handle_edit_server_selected(update, context)
    elif query.data.startswith("edit_field_"):
        await handle_edit_field(update, context)
    elif query.data.startswith("set_label_"):
        await handle_set_label(update, context)
    elif query.data.startswith("set_emoji_"):
        await handle_set_emoji(update, context)
    elif query.data.startswith("edit_emoji_custom_"):
        await handle_edit_emoji_custom(update, context)
    elif query.data.startswith("delete_emoji_"):
        await handle_delete_emoji(update, context)
    elif query.data.startswith("delete_domain_emoji_"):
        await handle_delete_domain_emoji(update, context)

    elif query.data.startswith("edit_domain_select_"):
        await handle_edit_domain_selected(update, context)
    elif query.data.startswith("edit_domain_field_"):
        await handle_edit_domain_field(update, context)


async def servers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id

    servers = load_servers()
    text = format_server_list(servers)

    keyboard = [
        [
            InlineKeyboardButton("➕ Add Server", callback_data="add_server"),
            InlineKeyboardButton("✏️ Edit Server", callback_data="edit_server"),
        ],
        [
            InlineKeyboardButton("🔍 Search & Filter", callback_data="filter_servers"),
        ],
        [
            InlineKeyboardButton("🗑️ Remove Server", callback_data="remove_server"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Main Menu", callback_data="back_main"),
        ],
    ]

    if query:

        await query.answer()
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def domains_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id

    domains = load_domains()
    text = format_domain_list(domains)

    keyboard = [
        [
            InlineKeyboardButton("➕ Add Domain", callback_data="add_domain"),
            InlineKeyboardButton("✏️ Edit Domain", callback_data="edit_domain"),
        ],
        [
            InlineKeyboardButton("🔍 Search & Filter", callback_data="filter_domains"),
        ],
        [
            InlineKeyboardButton("🗑️ Remove Domain", callback_data="remove_domain"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Main Menu", callback_data="back_main"),
        ],
    ]

    if query:

        await query.answer()
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def dashboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id

    servers = load_servers()
    domains = load_domains()
    settings = load_settings()

    total_servers = len(servers)
    total_domains = len(domains)

    server_costs = 0
    for info in servers.values():
        price = info.get("price", 0)
        if isinstance(price, str):
            price = price.replace("$", "").replace("€", "").replace(",", "").strip()
        try:
            server_costs += float(price)
        except (ValueError, TypeError):
            server_costs += 0

    domain_costs = 0
    for info in domains.values():
        price = info.get("price", 0)
        if isinstance(price, str):
            price = price.replace("$", "").replace("€", "").replace(",", "").strip()
        try:
            domain_costs += float(price)
        except (ValueError, TypeError):
            domain_costs += 0

    total_monthly_cost = server_costs + domain_costs

    server_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in servers.values():
        status, _ = get_server_status(info["date"], settings.get("warning_days", 5))
        if status in server_status_counts:
            server_status_counts[status] += 1

    domain_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in domains.values():
        status, _ = get_server_status(info["date"], settings.get("warning_days", 5))
        if status in domain_status_counts:
            domain_status_counts[status] += 1

    yearly_cost = total_monthly_cost * 12

    dashboard_text = (
        "📊 *Analytical Dashboard - Watch Guard*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 *General Statistics:*\n"
        f"    • Total Servers: `{total_servers}`\n"
        f"    • Total Domains: `{total_domains}`\n"
        f"    • Total Items: `{total_servers + total_domains}`\n\n"
        f"💰 *Financial Analysis:*\n"
        f"    • Monthly Cost: `${total_monthly_cost:.2f}`\n"
        f"    • Yearly Cost: `${yearly_cost:.2f}`\n"
        f"    • Average Server Cost: `{(server_costs/total_servers if total_servers > 0 else 0):.2f}`\n"
        f"    • Average Domain Cost: `{(domain_costs/total_domains if total_domains > 0 else 0):.2f}`\n\n"
        f"⚠️ *Server Status:*\n"
        f"    • Expired: `{server_status_counts['expired']}` items\n"
        f"    • Near Expiration: `{server_status_counts['warning']}` items\n"
        f"    • Active: `{server_status_counts['safe']}` items\n\n"
        f"🌐 *Domain Status:*\n"
        f"    • Expired: `{domain_status_counts['expired']}` items\n"
        f"    • Near Expiration: `{domain_status_counts['warning']}` items\n"
        f"    • Active: `{domain_status_counts['safe']}` items\n\n"
        f"⚙️ *Current Settings:*\n"
        f"    • Notification Time: `{settings.get('notification_hour', 9):02d}:{settings.get('notification_minute', 0):02d}`\n"
        f"    • Warning Days: `{settings.get('warning_days', 5)} days`"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh Statistics", callback_data="dashboard"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Main Menu", callback_data="back_main"),
        ],
    ]

    if query:

        await query.answer()
        await query.edit_message_text(
            text=dashboard_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:

        await context.bot.send_message(
            chat_id=chat_id,
            text=dashboard_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id

    settings = load_settings()
    labels = load_labels()

    text = (
        f"📅 Warning Days: `{settings['warning_days']} days`\n"
        f"⏰ Notification Time: `{settings['notification_hour']:02d}:{settings['notification_minute']:02d}`\n"
        f"🔔 Daily Notifications: `{'Enabled' if settings['daily_notifications'] else 'Disabled'}`\n"
        f"🏷️ Labels: `{len(labels)} labels`\n\n"
        "👉 Select an option to modify:"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "📅 Change Warning Days", callback_data="set_warning_days"
            )
        ],
        [
            InlineKeyboardButton(
                "⏰ Change Notification Time", callback_data="set_notification_time"
            )
        ],
        [
            InlineKeyboardButton(
                "🔔 Toggle Notifications", callback_data="toggle_notifications"
            )
        ],
        [InlineKeyboardButton("🏷️ Manage Labels", callback_data="manage_labels")],
        [InlineKeyboardButton("⏎ Back to Main Menu", callback_data="back_main")],
    ]

    if query:

        await query.answer()
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_set_warning_days(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    text = (
        "📅 **Change Warning Days**\n\n"
        "Current warning days: `{}`\n\n"
        "Choose new warning days or type a custom number:"
    ).format(load_settings().get("warning_days", 5))

    keyboard = [
        [
            InlineKeyboardButton("1 day", callback_data="warning_days_1"),
            InlineKeyboardButton("3 days", callback_data="warning_days_3"),
            InlineKeyboardButton("5 days", callback_data="warning_days_5"),
        ],
        [
            InlineKeyboardButton(
                "✏️ Type Custom Number", callback_data="warning_days_custom"
            ),
        ],
        [
            InlineKeyboardButton("⏎ Back to Settings", callback_data="settings"),
        ],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_set_notification_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    settings = load_settings()
    current_time = f"{settings.get('notification_hour', 9):02d}:{settings.get('notification_minute', 0):02d}"

    text = (
        "⏰ **Change Notification Time**\n\n"
        f"Current time: `{current_time}`\n\n"
        "Choose new notification time:"
    )

    keyboard = [
        [
            InlineKeyboardButton("06:00", callback_data="time_6_0"),
            InlineKeyboardButton("08:00", callback_data="time_8_0"),
            InlineKeyboardButton("09:00", callback_data="time_9_0"),
        ],
        [
            InlineKeyboardButton("10:00", callback_data="time_10_0"),
            InlineKeyboardButton("12:00", callback_data="time_12_0"),
            InlineKeyboardButton("14:00", callback_data="time_14_0"),
        ],
        [
            InlineKeyboardButton("16:00", callback_data="time_16_0"),
            InlineKeyboardButton("18:00", callback_data="time_18_0"),
            InlineKeyboardButton("20:00", callback_data="time_20_0"),
        ],
        [
            InlineKeyboardButton("✏️ Type Custom Time", callback_data="time_custom"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Settings", callback_data="settings"),
        ],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_toggle_notifications(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    settings = load_settings()
    current_status = settings.get("daily_notifications", True)
    new_status = not current_status

    settings["daily_notifications"] = new_status
    save_settings(settings)

    await settings_menu(update, context)


async def handle_manage_labels(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    labels = load_labels()

    if "settings_label_page" not in context.user_data:
        context.user_data["settings_label_page"] = 0

    page = context.user_data["settings_label_page"]
    labels_per_page = 10
    start_idx = page * labels_per_page
    end_idx = start_idx + labels_per_page
    page_labels = labels[start_idx:end_idx]
    total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

    text = (
        "🏷️ **Manage Labels**\n\n"
        f"Total labels: `{len(labels)}`\n"
        f"Page {page + 1} of {total_pages}\n\n"
        "**Available Labels:**\n"
    )

    if page_labels:
        for i, label in enumerate(page_labels, start_idx + 1):
            text += f"{i}. `{label}`\n"
    else:
        text += "No labels found."

    keyboard = []

    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    "⬅️ Previous", callback_data=f"settings_label_page_{page-1}"
                )
            )
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    "Next ➡️", callback_data=f"settings_label_page_{page+1}"
                )
            )
        if pagination_row:
            keyboard.append(pagination_row)

    keyboard.extend(
        [
            [
                InlineKeyboardButton("➕ Add Label", callback_data="add_label"),
                InlineKeyboardButton("🗑️ Remove Label", callback_data="remove_label"),
            ],
            [InlineKeyboardButton("🔄 Refresh Labels", callback_data="manage_labels")],
            [InlineKeyboardButton("⏎ Back to Settings", callback_data="settings")],
        ]
    )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_warning_days_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    days = int(query.data.split("_")[-1])

    settings = load_settings()
    settings["warning_days"] = days
    save_settings(settings)

    text = (
        "📅 **Warning Days Updated**\n\n"
        f"Warning days set to: `{days} days`\n\n"
        "✅ Settings saved successfully!"
    )

    keyboard = [
        [InlineKeyboardButton("⏎ Back to Settings", callback_data="settings")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_time_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    time_parts = query.data.split("_")
    hour = int(time_parts[1])
    minute = int(time_parts[2])

    settings = load_settings()
    settings["notification_hour"] = hour
    settings["notification_minute"] = minute
    save_settings(settings)

    text = (
        "⏰ **Notification Time Updated**\n\n"
        f"Notification time set to: `{hour:02d}:{minute:02d}`\n\n"
        "✅ Settings saved successfully!"
    )

    keyboard = [
        [InlineKeyboardButton("⏎ Back to Settings", callback_data="settings")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_warning_days_custom(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    context.user_data["waiting_for"] = "warning_days"

    text = "📅 **Enter Custom Warning Days**\n\n" "Please type the number of days:"

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="settings")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_time_custom(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    context.user_data["waiting_for"] = "notification_time"

    text = (
        "⏰ **Enter Custom Notification Time**\n\n"
        "Please type the time in HH:MM format (24-hour):"
    )

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="settings")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not context.user_data.get("waiting_for"):
        return

    waiting_for = context.user_data.get("waiting_for")
    text = update.message.text.strip()

    if waiting_for == "warning_days":
        try:
            days = int(text)
            if 1 <= days <= 365:
                settings = load_settings()
                settings["warning_days"] = days
                save_settings(settings)

                response_text = (
                    "📅 **Warning Days Updated**\n\n"
                    f"Warning days set to: `{days} days`\n\n"
                    "✅ Settings saved successfully!"
                )

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "⏎ Back to Settings", callback_data="settings"
                        )
                    ],
                ]

                await update.message.reply_text(
                    text=response_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

                context.user_data.pop("waiting_for", None)
            else:
                await update.message.reply_text(
                    "❌ Invalid number! Please enter a number between 1 and 365.",
                    parse_mode="Markdown",
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format! Please enter a valid number.", parse_mode="Markdown"
            )

    elif waiting_for == "notification_time":
        time_pattern = re.match(r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$", text)
        if time_pattern:
            hour = int(time_pattern.group(1))
            minute = int(time_pattern.group(2))

            settings = load_settings()
            settings["notification_hour"] = hour
            settings["notification_minute"] = minute
            save_settings(settings)

            response_text = (
                "⏰ **Notification Time Updated**\n\n"
                f"Notification time set to: `{hour:02d}:{minute:02d}`\n\n"
                "✅ Settings saved successfully!"
            )

            keyboard = [
                [InlineKeyboardButton("⏎ Back to Settings", callback_data="settings")],
            ]

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

            context.user_data.pop("waiting_for", None)
        else:
            await update.message.reply_text(
                "❌ Invalid time format! Please use HH:MM format (e.g., 09:30, 14:15)",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_label":
        label = text.strip()
        if label and len(label) <= 50:
            try:

                labels_file = "labels.json"
                labels_added = False

                if os.path.exists(labels_file):
                    with open(labels_file, "r", encoding="utf-8") as f:
                        labels_data = json.load(f)

                    if isinstance(labels_data, dict) and "labels" in labels_data:

                        if label not in labels_data["labels"]:
                            labels_data["labels"].append(label)
                            labels_data["last_updated"] = datetime.now().isoformat()
                            labels_added = True

                            with open(labels_file, "w", encoding="utf-8") as f:
                                json.dump(labels_data, f, indent=4, ensure_ascii=False)
                        else:
                            response_text = (
                                "⚠️ **Label Already Exists**\n\n"
                                f"Label `{label}` already exists in the system."
                            )

                            keyboard = [
                                [
                                    InlineKeyboardButton(
                                        "⏎ Back to Labels",
                                        callback_data="manage_labels",
                                    )
                                ],
                            ]

                            await update.message.reply_text(
                                text=response_text,
                                parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup(keyboard),
                            )

                            context.user_data.pop("waiting_for", None)
                            return
                    else:

                        if isinstance(labels_data, list):
                            if label not in labels_data:
                                labels_data.append(label)
                            else:
                                response_text = (
                                    "⚠️ **Label Already Exists**\n\n"
                                    f"Label `{label}` already exists in the system."
                                )

                                keyboard = [
                                    [
                                        InlineKeyboardButton(
                                            "⏎ Back to Labels",
                                            callback_data="manage_labels",
                                        )
                                    ],
                                ]

                                await update.message.reply_text(
                                    text=response_text,
                                    parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard),
                                )

                                context.user_data.pop("waiting_for", None)
                                return
                        else:
                            labels_data = [label]

                        new_labels_data = {
                            "labels": labels_data,
                            "created_at": datetime.now().isoformat(),
                            "last_updated": datetime.now().isoformat(),
                            "version": "1.0",
                        }

                        with open(labels_file, "w", encoding="utf-8") as f:
                            json.dump(new_labels_data, f, indent=4, ensure_ascii=False)

                        labels_added = True
                else:

                    new_labels_data = {
                        "labels": [label],
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "version": "1.0",
                    }

                    with open(labels_file, "w", encoding="utf-8") as f:
                        json.dump(new_labels_data, f, indent=4, ensure_ascii=False)

                    labels_added = True

                if labels_added:
                    settings = load_settings()
                    if "labels" not in settings:
                        settings["labels"] = []
                    if label not in settings["labels"]:
                        settings["labels"].append(label)
                        save_settings(settings)

                if labels_added:
                    response_text = (
                        "✅ **Label Added Successfully!**\n\n"
                        f"• Label: `{label}`\n"
                        f"• Status: `Saved and synced`\n\n"
                        "The label is now available for use with servers and domains."
                    )
                else:
                    response_text = (
                        "❌ **Failed to Add Label**\n\n"
                        f"Could not add label `{label}` to the system."
                    )

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "⏎ Back to Labels", callback_data="manage_labels"
                        )
                    ],
                ]

                await update.message.reply_text(
                    text=response_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

                context.user_data.pop("waiting_for", None)

            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error adding label: {str(e)}", parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Invalid label! Please enter a label with 1-50 characters.",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_server_name":
        server_name = text.strip()
        if server_name and len(server_name) <= 100 and is_valid_name(server_name):
            servers = load_servers()
            if server_name in servers:
                await update.message.reply_text(
                    "❌ Server name already exists! Please choose a different name.",
                    parse_mode="Markdown",
                )
            else:
                context.user_data["new_server"]["name"] = server_name
                context.user_data["waiting_for"] = "add_server_date"

                response_text = (
                    "📅 **Enter Renewal Date**\n\n"
                    f"Server: `{server_name}`\n\n"
                    "Please enter the renewal date in `YYYY-MM-DD` format:"
                )

                keyboard = [
                    [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
                ]

                await update.message.reply_text(
                    text=response_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
        else:
            await update.message.reply_text(
                "❌ Invalid server name! Please enter a valid name (1-100 characters, alphanumeric only).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_server_date":
        date_str = text.strip()

        formatted_date = format_date_input(date_str)
        if is_valid_date(formatted_date):
            if is_future_date(formatted_date):
                context.user_data["new_server"]["date"] = formatted_date
                context.user_data["waiting_for"] = "add_server_price"

                response_text = (
                    "💰 **Enter Server Price**\n\n"
                    f"Server: `{context.user_data['new_server']['name']}`\n"
                    f"Renewal Date: `{formatted_date}`\n\n"
                    "Please enter the monthly price:"
                )

                keyboard = [
                    [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
                ]

                await update.message.reply_text(
                    text=response_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await update.message.reply_text(
                    "❌ Invalid date! Please enter a future date (today or later).",
                    parse_mode="Markdown",
                )
        else:
            await update.message.reply_text(
                "❌ Invalid date format! Please use `YYYY-MM-DD` format.",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_server_price":
        price_str = text.strip()
        if is_valid_price(price_str):
            context.user_data["new_server"]["raw_price"] = price_str
            context.user_data["waiting_for"] = "add_server_currency"

            response_text = (
                "💲 **Select Currency**\n\n"
                f"Server: `{context.user_data['new_server']['name']}`\n"
                f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
                f"Price: `{price_str}`\n\n"
                "Please select the currency:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("$ USD", callback_data="currency_usd"),
                    InlineKeyboardButton("€ EUR", callback_data="currency_eur"),
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
            ]

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid price format! Please enter a valid price (e.g., 25.99, 19.50, 45.00).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_server_custom_emoji":
        custom_emoji = text.strip()
        if custom_emoji and len(custom_emoji) <= 10:
            context.user_data["new_server"]["emoji"] = custom_emoji
            context.user_data["waiting_for"] = "add_server_datacenter"

            response_text = (
                "🏢 **Enter Datacenter**\n\n"
                f"Server: `{context.user_data['new_server']['name']}`\n"
                f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
                f"Price: `{context.user_data['new_server']['price']}`\n"
                f"Emoji: `{custom_emoji}`\n\n"
                "Please enter the datacenter/provider name:"
            )

            keyboard = [
                [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
            ]

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid emoji! Please enter a valid emoji (1-10 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_server_datacenter":
        datacenter = text.strip()
        if datacenter and len(datacenter) <= 100:
            context.user_data["new_server"]["datacenter"] = datacenter
            context.user_data["waiting_for"] = "add_server_label"

            labels = load_labels()

            response_text = (
                "🏷️ **Select Label for Server**\n\n"
                f"Server: `{context.user_data['new_server']['name']}`\n"
                f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
                f"Price: `{context.user_data['new_server']['price']}`\n"
                f"Datacenter: `{datacenter}`\n\n"
                "Choose a label for your server:"
            )

            keyboard = []

            keyboard.extend(create_labels_keyboard(labels, 0, "server"))

            keyboard.append(
                [InlineKeyboardButton("⏭️ Skip", callback_data="skip_server_label")]
            )

            keyboard.append(
                [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")]
            )

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid datacenter name! Please enter a valid name (1-100 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_server_date":
        date_str = text.strip()

        formatted_date = format_date_input(date_str)
        if is_valid_date(formatted_date):
            if is_future_date(formatted_date):
                try:
                    servers = load_servers()
                    server_name = context.user_data["edit_server"]["name"]

                    if server_name in servers:
                        servers[server_name]["date"] = formatted_date
                        save_servers(servers)

                        response_text = (
                            "📅 **Renewal Date Updated**\n\n"
                            f"Server: `{server_name}`\n"
                            f"New Date: `{formatted_date}`\n\n"
                            "✅ Changes saved successfully!"
                        )

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "Edit Another Field",
                                    callback_data=f"edit_server_select_{server_name}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "⏎ Back to Servers", callback_data="servers_menu"
                                )
                            ],
                        ]

                        await update.message.reply_text(
                            text=response_text,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )

                        context.user_data.pop("waiting_for", None)
                        context.user_data.pop("edit_server", None)
                    else:
                        await update.message.reply_text(
                            "❌ Server not found!", parse_mode="Markdown"
                        )
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ Error updating date: {str(e)}", parse_mode="Markdown"
                    )
            else:
                await update.message.reply_text(
                    "❌ Invalid date! Please enter a future date (today or later).",
                    parse_mode="Markdown",
                )
        else:
            await update.message.reply_text(
                "❌ Invalid date format! Please use `YYYY-MM-DD` format.",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_server_price":
        price_str = text.strip()
        if is_valid_price(price_str):

            context.user_data["edit_server"]["price_amount"] = price_str
            context.user_data["waiting_for"] = "edit_server_currency"

            text = (
                f"💲 **Select Currency**\n\n"
                f"Server: `{context.user_data['edit_server']['name']}`\n"
                f"Price: `{price_str}`\n\n"
                "Please select the currency:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("$ USD", callback_data="edit_currency_usd"),
                    InlineKeyboardButton("€ EUR", callback_data="edit_currency_eur"),
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data=f"edit_server_select_{context.user_data['edit_server']['name']}",
                    )
                ],
            ]

            await update.message.reply_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid price format! Please enter a valid number.",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_server_datacenter":
        new_datacenter = text.strip()
        if new_datacenter and len(new_datacenter) <= 100:
            try:
                servers = load_servers()
                server_name = context.user_data["edit_server"]["name"]

                if server_name in servers:
                    servers[server_name]["datacenter"] = new_datacenter
                    save_servers(servers)

                    response_text = (
                        "🏢 **Datacenter Updated**\n\n"
                        f"Server: `{server_name}`\n"
                        f"New Datacenter: `{new_datacenter}`\n\n"
                        "✅ Changes saved successfully!"
                    )

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Edit Another Field",
                                callback_data=f"edit_server_select_{server_name}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Servers", callback_data="servers_menu"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        text=response_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )

                    context.user_data.pop("waiting_for", None)
                    context.user_data.pop("edit_server", None)
                else:
                    await update.message.reply_text(
                        "❌ Server not found!", parse_mode="Markdown"
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error updating datacenter: {str(e)}", parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Invalid datacenter name! Please enter 1-100 characters.",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_server_name":
        new_name = text.strip()
        if new_name and len(new_name) <= 100:
            try:
                servers = load_servers()
                old_name = context.user_data["edit_server"]["name"]

                if old_name in servers:

                    if new_name in servers and new_name != old_name:
                        await update.message.reply_text(
                            "❌ **Name Already Exists**\n\n"
                            f"A server with the name `{new_name}` already exists.\n"
                            "Please choose a different name.",
                            parse_mode="Markdown",
                        )
                        return

                    server_data = servers[old_name]
                    del servers[old_name]

                    servers[new_name] = server_data
                    save_servers(servers)

                    response_text = (
                        "✏️ **Server Name Updated**\n\n"
                        f"Old Name: `{old_name}`\n"
                        f"New Name: `{new_name}`\n\n"
                        "✅ Changes saved successfully!"
                    )

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Edit Another Field",
                                callback_data=f"edit_server_select_{new_name}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Servers", callback_data="servers_menu"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        text=response_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )

                    context.user_data["edit_server"]["name"] = new_name
                    context.user_data.pop("waiting_for", None)
                else:
                    await update.message.reply_text(
                        "❌ Server not found!", parse_mode="Markdown"
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error updating name: {str(e)}", parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Invalid server name! Please enter a valid name (1-100 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_domain_date":
        date_str = text.strip()

        formatted_date = format_date_input(date_str)
        if is_valid_date(formatted_date):
            if is_future_date(formatted_date):
                try:
                    domains = load_domains()
                    domain_name = context.user_data["edit_domain"]["name"]

                    if domain_name in domains:
                        domains[domain_name]["date"] = formatted_date
                        save_domains(domains)

                        response_text = (
                            "📅 **Domain Renewal Date Updated**\n\n"
                            f"Domain: `{domain_name}`\n"
                            f"New Date: `{formatted_date}`\n\n"
                            "✅ Changes saved successfully!"
                        )

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "Edit Another Field",
                                    callback_data=f"edit_domain_select_{domain_name}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "⏎ Back to Domains", callback_data="domains_menu"
                                )
                            ],
                        ]

                        await update.message.reply_text(
                            text=response_text,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )

                        context.user_data.pop("waiting_for", None)
                        context.user_data.pop("edit_domain", None)
                    else:
                        await update.message.reply_text(
                            "❌ Domain not found!", parse_mode="Markdown"
                        )
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ Error updating date: {str(e)}", parse_mode="Markdown"
                    )
            else:
                await update.message.reply_text(
                    "❌ Invalid date! Please enter a future date (today or later).",
                    parse_mode="Markdown",
                )
        else:
            await update.message.reply_text(
                "❌ Invalid date format! Please use `YYYY-MM-DD` format.",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_domain_price":
        price_str = text.strip()
        if is_valid_price(price_str):
            try:
                domains = load_domains()
                domain_name = context.user_data["edit_domain"]["name"]

                if domain_name in domains:
                    domains[domain_name]["price"] = price_str
                    save_domains(domains)

                    response_text = (
                        "💲 **Domain Price Updated**\n\n"
                        f"Domain: `{domain_name}`\n"
                        f"New Price: `{price_str}`\n\n"
                        "✅ Changes saved successfully!"
                    )

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Edit Another Field",
                                callback_data=f"edit_domain_select_{domain_name}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Domains", callback_data="domains_menu"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        text=response_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )

                    context.user_data.pop("waiting_for", None)
                    context.user_data.pop("edit_domain", None)
                else:
                    await update.message.reply_text(
                        "❌ Domain not found!", parse_mode="Markdown"
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error updating price: {str(e)}", parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Invalid price format! Please enter a valid number.",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_domain_name":
        new_name = text.strip().lower()
        if new_name and len(new_name) <= 100 and is_valid_domain_name(new_name):
            try:
                domains = load_domains()
                old_name = context.user_data["edit_domain"]["name"]

                if old_name in domains:

                    if new_name in domains and new_name != old_name:
                        await update.message.reply_text(
                            "❌ **Name Already Exists**\n\n"
                            f"A domain with the name `{new_name}` already exists.\n"
                            "Please choose a different name.",
                            parse_mode="Markdown",
                        )
                        return

                    domain_data = domains[old_name]
                    del domains[old_name]

                    domains[new_name] = domain_data
                    save_domains(domains)

                    response_text = (
                        "✏️ **Domain Name Updated**\n\n"
                        f"Old Name: `{old_name}`\n"
                        f"New Name: `{new_name}`\n\n"
                        "✅ Changes saved successfully!"
                    )

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Edit Another Field",
                                callback_data=f"edit_domain_select_{new_name}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Domains", callback_data="domains_menu"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        text=response_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )

                    context.user_data["edit_domain"]["name"] = new_name
                    context.user_data.pop("waiting_for", None)
                else:
                    await update.message.reply_text(
                        "❌ Domain not found!", parse_mode="Markdown"
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error updating name: {str(e)}", parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Invalid domain name! Please enter a valid domain name (1-100 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_domain_registrar":
        registrar = text.strip()
        if registrar and len(registrar) <= 100:
            try:
                domains = load_domains()
                domain_name = context.user_data["edit_domain"]["name"]

                if domain_name in domains:
                    domains[domain_name]["registrar"] = registrar
                    save_domains(domains)

                    response_text = (
                        "🏢 **Domain Registrar Updated**\n\n"
                        f"Domain: `{domain_name}`\n"
                        f"New Registrar: `{registrar}`\n\n"
                        "✅ Changes saved successfully!"
                    )

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Edit Another Field",
                                callback_data=f"edit_domain_select_{domain_name}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Domains", callback_data="domains_menu"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        text=response_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )

                    context.user_data.pop("waiting_for", None)
                    context.user_data.pop("edit_domain", None)
                else:
                    await update.message.reply_text(
                        "❌ Domain not found!", parse_mode="Markdown"
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error updating registrar: {str(e)}", parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Invalid registrar name! Please enter a valid name (1-100 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_domain_name":
        domain_name = text.strip().lower()
        if (
            domain_name
            and len(domain_name) <= 100
            and is_valid_domain_name(domain_name)
        ):
            domains = load_domains()
            if domain_name in domains:
                await update.message.reply_text(
                    "❌ Domain name already exists! Please choose a different name.",
                    parse_mode="Markdown",
                )
            else:
                context.user_data["new_domain"]["name"] = domain_name
                context.user_data["waiting_for"] = "add_domain_date"

                response_text = (
                    "📅 **Enter Renewal Date**\n\n"
                    f"Domain: `{domain_name}`\n\n"
                    "Please enter the renewal date in `YYYY-MM-DD` format:"
                )

                keyboard = [
                    [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
                ]

                await update.message.reply_text(
                    text=response_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
        else:
            await update.message.reply_text(
                "❌ Invalid domain name! Please enter a valid domain name (e.g., example.com).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_domain_date":
        date_str = text.strip()
        formatted_date = format_date_input(date_str)
        if is_valid_date(formatted_date):
            if is_future_date(formatted_date):
                context.user_data["new_domain"]["date"] = formatted_date
                context.user_data["waiting_for"] = "add_domain_price"

                response_text = (
                    "💰 **Enter Domain Price**\n\n"
                    f"Domain: `{context.user_data['new_domain']['name']}`\n"
                    f"Renewal Date: `{formatted_date}`\n\n"
                    "Please enter the annual price:"
                )

                keyboard = [
                    [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
                ]

                await update.message.reply_text(
                    text=response_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await update.message.reply_text(
                    "❌ Invalid date! Please enter a future date (today or later).",
                    parse_mode="Markdown",
                )
        else:
            await update.message.reply_text(
                "❌ Invalid date format! Please use `YYYY-MM-DD` format.",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_domain_price":
        price_str = text.strip()
        if is_valid_price(price_str):
            context.user_data["new_domain"]["raw_price"] = price_str
            context.user_data["waiting_for"] = "add_domain_currency"

            response_text = (
                "💲 **Select Currency**\n\n"
                f"Domain: `{context.user_data['new_domain']['name']}`\n"
                f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
                f"Price: `{price_str}`\n\n"
                "Please select the currency:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("$ USD", callback_data="domain_currency_usd"),
                    InlineKeyboardButton("€ EUR", callback_data="domain_currency_eur"),
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
            ]

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid price format! Please enter a valid price (e.g., 25.99, 19.50, 45.00).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_domain_custom_emoji":
        custom_emoji = text.strip()
        if custom_emoji and len(custom_emoji) <= 10:
            context.user_data["new_domain"]["emoji"] = custom_emoji
            context.user_data["waiting_for"] = "add_domain_registrar"

            response_text = (
                "🌐 **Enter Registrar**\n\n"
                f"Domain: `{context.user_data['new_domain']['name']}`\n"
                f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
                f"Price: `{context.user_data['new_domain']['price']}`\n"
                f"Emoji: `{custom_emoji}`\n\n"
                "Please enter the registrar name:"
            )

            keyboard = [
                [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
            ]

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid emoji! Please enter a valid emoji (1-10 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "add_domain_registrar":
        registrar = text.strip()
        if registrar and len(registrar) <= 100:
            context.user_data["new_domain"]["registrar"] = registrar
            context.user_data["waiting_for"] = "add_domain_label"

            labels = load_labels()

            response_text = (
                "🏷️ **Select Label for Domain**\n\n"
                f"Domain: `{context.user_data['new_domain']['name']}`\n"
                f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
                f"Price: `{context.user_data['new_domain']['price']}`\n"
                f"Registrar: `{registrar}`\n\n"
                "Choose a label for your domain:"
            )

            keyboard = []

            keyboard.extend(create_labels_keyboard(labels, 0, "domain"))

            keyboard.append(
                [InlineKeyboardButton("⏭️ Skip", callback_data="skip_domain_label")]
            )

            keyboard.append(
                [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")]
            )

            await update.message.reply_text(
                text=response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text(
                "❌ Invalid registrar name! Please enter a valid name (1-100 characters).",
                parse_mode="Markdown",
            )

    elif waiting_for == "edit_server_custom_emoji":
        custom_emoji = text.strip()
        if custom_emoji and len(custom_emoji) <= 10:
            try:
                servers = load_servers()
                server_name = context.user_data["edit_server"]["name"]

                if server_name in servers:

                    servers[server_name]["emoji"] = custom_emoji
                    save_servers(servers)

                    response_text = (
                        "🎨 **Server Emoji Updated Successfully!**\n\n"
                        f"• Server: `{server_name}`\n"
                        f"• New Emoji: `{custom_emoji}`\n"
                        f"• Status: `Updated and saved`"
                    )

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Edit Another Field",
                                callback_data=f"edit_server_select_{server_name}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Servers", callback_data="servers_menu"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        text=response_text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )

                    context.user_data.pop("waiting_for", None)
                    context.user_data.pop("edit_server", None)
                else:
                    await update.message.reply_text(
                        "❌ **Server Not Found**\n\n"
                        f"Server `{server_name}` was not found in the system.",
                        parse_mode="Markdown",
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ **Error Updating Emoji**\n\n"
                    f"Failed to update server emoji: {str(e)}",
                    parse_mode="Markdown",
                )
        else:
            await update.message.reply_text(
                "❌ Invalid emoji! Please enter a valid emoji (1-10 characters).",
                parse_mode="Markdown",
            )


async def handle_add_label(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    context.user_data["waiting_for"] = "add_label"

    text = (
        "🏷️ **Add New Label**\n\n"
        "Please type the label name (1-50 characters):\n\n"
        "Example: `Production`\n"
        "Example: `Development`\n"
        "Example: `Client-ABC`"
    )

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="manage_labels")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_remove_label(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    labels = load_labels()

    if not labels:
        text = "🏷️ **Remove Label**\n\n" "❌ No labels found to remove."

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Labels", callback_data="manage_labels")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if "remove_label_page" not in context.user_data:
        context.user_data["remove_label_page"] = 0

    page = context.user_data["remove_label_page"]
    labels_per_page = 10
    start_idx = page * labels_per_page
    end_idx = start_idx + labels_per_page
    page_labels = labels[start_idx:end_idx]
    total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

    text = (
        "🏷️ **Remove Label**\n\n"
        "⚠️ **Warning:** Removing a label will also remove it from all servers and domains using it.\n\n"
        f"Page {page + 1} of {total_pages} ({len(labels)} total labels)\n\n"
        "Select a label to remove:"
    )

    keyboard = []

    for label in page_labels:
        keyboard.append(
            [InlineKeyboardButton(f"{label}", callback_data=f"remove_label_{label}")]
        )

    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    "⬅️ Previous", callback_data=f"remove_label_page_{page-1}"
                )
            )
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    "Next ➡️", callback_data=f"remove_label_page_{page+1}"
                )
            )
        if pagination_row:
            keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="manage_labels")])

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_remove_label_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    label_to_remove = query.data.replace("remove_label_", "")

    try:

        labels_file = "labels.json"
        labels_removed = False

        if os.path.exists(labels_file):
            with open(labels_file, "r", encoding="utf-8") as f:
                labels_data = json.load(f)

            if isinstance(labels_data, dict) and "labels" in labels_data:

                if label_to_remove in labels_data["labels"]:
                    labels_data["labels"].remove(label_to_remove)
                    labels_data["last_updated"] = datetime.now().isoformat()
                    labels_removed = True

                    with open(labels_file, "w", encoding="utf-8") as f:
                        json.dump(labels_data, f, indent=4, ensure_ascii=False)
            elif isinstance(labels_data, list):

                if label_to_remove in labels_data:
                    labels_data.remove(label_to_remove)
                    labels_removed = True

                    new_labels_data = {
                        "labels": labels_data,
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "version": "1.0",
                    }

                    with open(labels_file, "w", encoding="utf-8") as f:
                        json.dump(new_labels_data, f, indent=4, ensure_ascii=False)

        settings = load_settings()
        if "labels" in settings and label_to_remove in settings["labels"]:
            settings["labels"].remove(label_to_remove)
            save_settings(settings)

        servers = load_servers()
        servers_updated = False
        for name, info in servers.items():
            if info.get("label", "").strip() == label_to_remove:
                info["label"] = ""
                servers_updated = True

        if servers_updated:
            save_servers(servers)

        domains = load_domains()
        domains_updated = False
        for name, info in domains.items():
            if info.get("label", "").strip() == label_to_remove:
                info["label"] = ""
                domains_updated = True

        if domains_updated:
            save_domains(domains)

        if labels_removed:
            text = (
                "🏷️ **Label Removed Successfully**\n\n"
                f"Removed label: `{label_to_remove}`\n\n"
                "✅ Label removed from all servers and domains!"
            )
        else:
            text = (
                "⚠️ **Label Not Found**\n\n"
                f"Label `{label_to_remove}` was not found in the labels list."
            )

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Labels", callback_data="manage_labels")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = (
            "❌ **Error Removing Label**\n\n"
            f"Failed to remove label: `{label_to_remove}`\n\n"
            f"Error: {str(e)}"
        )

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Labels", callback_data="manage_labels")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_add_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    context.user_data["waiting_for"] = "add_server_name"
    context.user_data["new_server"] = {}

    text = "➕ **Add New Server**\n\n" "Please enter the server name:"

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_edit_server(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    servers = load_servers()

    if not servers:
        text = (
            "**Edit Server**\n\n"
            "❌ No servers found to edit.\n"
            "Please add some servers first."
        )

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    text = "**Edit Server**\n\n" "Select a server to edit:"

    keyboard = []
    for server_name in list(servers.keys())[:10]:
        emoji = servers[server_name].get("emoji", "")
        if emoji and emoji.strip():
            display_name = f"{emoji} {server_name}"
        else:
            display_name = server_name
        keyboard.append(
            [
                InlineKeyboardButton(
                    display_name, callback_data=f"edit_server_select_{server_name}"
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")])

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_remove_server(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    servers = load_servers()

    if not servers:
        text = "🗑️ **Remove Server**\n\n" "❌ No servers found to remove."

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    text = "🗑️ **Remove Server**\n\n" "Select a server to remove:"

    keyboard = []
    for server_name in list(servers.keys())[:10]:
        emoji = servers[server_name].get("emoji", "")
        if emoji and emoji.strip():
            display_name = f"{emoji} {server_name}"
        else:
            display_name = server_name
        keyboard.append(
            [
                InlineKeyboardButton(
                    display_name, callback_data=f"remove_server_confirm_{server_name}"
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")])

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_remove_server_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    server_name = query.data.replace("remove_server_confirm_", "")

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "🗑️ **Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        server_info = servers[server_name]
        settings = load_settings()
        warning_days = settings.get("warning_days", 5)
        status, days_diff = get_server_status(server_info["date"], warning_days)
        days_text = format_status_text(days_diff)

        text = (
            "**Confirm Server Removal**\n\n"
            f"⚠️ Warning: This action cannot be undone!\n\n"
            f"**Server Details:**\n"
            f"Name: `{server_name}`\n"
            f"Renewal Date: `{server_info['date']}`\n"
            f"Status: `{days_text}`\n"
            f"Price: `{server_info['price']}`\n"
            f"Datacenter: `{server_info['datacenter']}`\n\n"
            "Are you sure you want to remove this server?"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Yes, Remove", callback_data=f"remove_server_final_{server_name}"
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="servers_menu"),
            ],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to load server details: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_remove_server_final(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    server_name = query.data.replace("remove_server_final_", "")

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "🗑️ **Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        del servers[server_name]
        save_servers(servers)

        text = (
            "✅ **Server Removed Successfully!**\n\n"
            f"• Server: `{server_name}`\n"
            f"• Status: `Permanently removed`"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🗑️ Remove Another Server", callback_data="remove_server"
                )
            ],
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = (
            "❌ **Error Removing Server**\n\n"
            f"Failed to remove server `{server_name}`: {str(e)}"
        )

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_filter_servers(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    text = "🔍 **Filter Servers**\n\n" "Choose a filter to apply:"

    keyboard = [
        [
            InlineKeyboardButton("🔴 Expired", callback_data="filter_servers_expired"),
            InlineKeyboardButton("🟡 Warning", callback_data="filter_servers_warning"),
        ],
        [
            InlineKeyboardButton("🟢 Active", callback_data="filter_servers_safe"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu"),
        ],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_add_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    context.user_data["waiting_for"] = "add_domain_name"
    context.user_data["new_domain"] = {}

    text = "➕ **Add New Domain**\n\n" "Please enter the domain name:"

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_edit_domain(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    domains = load_domains()

    if not domains:
        text = (
            "**Edit Domain**\n\n"
            "❌ No domains found to edit.\n"
            "Please add some domains first."
        )

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    text = "**Edit Domain**\n\n" "Select a domain to edit:"

    keyboard = []
    for domain_name in list(domains.keys())[:10]:
        emoji = domains[domain_name].get("emoji", "")
        if emoji and emoji.strip():
            display_name = f"{emoji} {domain_name}"
        else:
            display_name = domain_name
        keyboard.append(
            [
                InlineKeyboardButton(
                    display_name, callback_data=f"edit_domain_select_{domain_name}"
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")])

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_remove_domain(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    domains = load_domains()

    if not domains:
        text = "❌ No domains found to remove."

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    text = "🗑 Select a domain to remove:"

    keyboard = []
    for domain_name in list(domains.keys())[:10]:
        emoji = domains[domain_name].get("emoji", "")
        if emoji and emoji.strip():
            display_name = f"{emoji} {domain_name}"
        else:
            display_name = domain_name
        keyboard.append(
            [
                InlineKeyboardButton(
                    display_name, callback_data=f"remove_domain_confirm_{domain_name}"
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")])

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_remove_domain_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    domain_name = query.data.replace("remove_domain_confirm_", "")

    try:
        domains = load_domains()

        if domain_name not in domains:
            text = (
                "🗑️ **Domain Not Found**\n\n"
                f"Domain `{domain_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Domains", callback_data="domains_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        domain_info = domains[domain_name]
        settings = load_settings()
        warning_days = settings.get("warning_days", 5)
        status, days_diff = get_server_status(domain_info["date"], warning_days)
        days_text = format_status_text(days_diff)

        text = (
            "**Confirm Domain Removal**\n\n"
            f"⚠️ Warning: This action cannot be undone!\n\n"
            f"**Domain Details:**\n"
            f"Name: `{domain_name}`\n"
            f"Renewal Date: `{domain_info['date']}`\n"
            f"Status: `{days_text}`\n"
            f"Price: `{domain_info['price']}`\n"
            f"Registrar: `{domain_info['registrar']}`\n\n"
            "Are you sure you want to remove this domain?"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Yes, Remove", callback_data=f"remove_domain_final_{domain_name}"
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="domains_menu"),
            ],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to load domain details: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_remove_domain_final(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    domain_name = query.data.replace("remove_domain_final_", "")

    try:
        domains = load_domains()

        if domain_name not in domains:
            text = (
                "🗑️ **Domain Not Found**\n\n"
                f"Domain `{domain_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Domains", callback_data="domains_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        del domains[domain_name]
        save_domains(domains)

        text = (
            "✅ **Domain Removed Successfully!**\n\n"
            f"• Domain: `{domain_name}`\n"
            f"• Status: `Permanently removed`"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🗑️ Remove Another Domain", callback_data="remove_domain"
                )
            ],
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = (
            "❌ **Error Removing Domain**\n\n"
            f"Failed to remove domain `{domain_name}`: {str(e)}"
        )

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_filter_domains(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    text = "🔍 **Filter Domains**\n\n" "Choose a filter to apply:"

    keyboard = [
        [
            InlineKeyboardButton("🔴 Expired", callback_data="filter_domains_expired"),
            InlineKeyboardButton("🟡 Warning", callback_data="filter_domains_warning"),
        ],
        [
            InlineKeyboardButton("🟢 Active", callback_data="filter_domains_safe"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu"),
        ],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_server_filter_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    filter_type = query.data.replace("filter_servers_", "")

    servers = load_servers()
    text = format_server_list(servers, filter_type)

    keyboard = [
        [
            InlineKeyboardButton("🔍 Change Filter", callback_data="filter_servers"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu"),
        ],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_domain_filter_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    filter_type = query.data.replace("filter_domains_", "")

    domains = load_domains()
    text = format_domain_list(domains, filter_type)

    keyboard = [
        [
            InlineKeyboardButton("🔍 Change Filter", callback_data="filter_domains"),
        ],
        [
            InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu"),
        ],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_currency_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    currency = query.data.replace("currency_", "").upper()

    if context.user_data.get("waiting_for") == "add_server_currency":

        raw_price = context.user_data["new_server"]["raw_price"]
        if currency == "USD":
            formatted_price = f"${raw_price}"
        elif currency == "EUR":
            formatted_price = f"€{raw_price}"
        else:
            formatted_price = raw_price

        context.user_data["new_server"]["price"] = formatted_price
        context.user_data["waiting_for"] = "add_server_emoji"

        response_text = (
            "👉 **Select Emoji for Server**\n\n"
            f"Server: `{context.user_data['new_server']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"Price: `{formatted_price}`\n\n"
            "Choose an emoji for your server:"
        )

        keyboard = []
        emoji_row = []
        for i, emoji in enumerate(EMOJI_OPTIONS):
            emoji_row.append(
                InlineKeyboardButton(emoji, callback_data=f"emoji_{emoji}")
            )
            if (i + 1) % 5 == 0:
                keyboard.append(emoji_row)
                emoji_row = []

        if emoji_row:
            keyboard.append(emoji_row)

        keyboard.append(
            [
                InlineKeyboardButton("✏️ Custom Emoji", callback_data="emoji_custom"),
                InlineKeyboardButton("⏭️ Skip", callback_data="emoji_skip"),
            ]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")]
        )

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_emoji_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "emoji_skip":

        context.user_data["new_server"]["emoji"] = ""
        context.user_data["waiting_for"] = "add_server_datacenter"

        response_text = (
            "🏢 **Enter Datacenter**\n\n"
            f"Server: `{context.user_data['new_server']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"Price: `{context.user_data['new_server']['price']}`\n"
            f"Emoji: `No emoji selected`\n\n"
            "Please enter the datacenter/provider name:"
        )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "emoji_custom":

        context.user_data["waiting_for"] = "add_server_custom_emoji"

        response_text = (
            "✏️ **Enter Custom Emoji**\n\n"
            f"Server: `{context.user_data['new_server']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"Price: `{context.user_data['new_server']['price']}`\n\n"
            "Please type your custom emoji (e.g., 🚀, ⭐, 🔥):"
        )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    else:

        selected_emoji = query.data.replace("emoji_", "")
        context.user_data["new_server"]["emoji"] = selected_emoji
        context.user_data["waiting_for"] = "add_server_datacenter"

        response_text = (
            "🏢 **Enter Datacenter**\n\n"
            f"Server: `{context.user_data['new_server']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"Price: `{context.user_data['new_server']['price']}`\n"
            f"Emoji: `{selected_emoji}`\n\n"
            "Please enter the datacenter/provider name:"
        )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_domain_currency_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    currency = query.data.replace("domain_currency_", "").upper()

    if context.user_data.get("waiting_for") == "add_domain_currency":

        raw_price = context.user_data["new_domain"]["raw_price"]
        if currency == "USD":
            formatted_price = f"${raw_price}"
        elif currency == "EUR":
            formatted_price = f"€{raw_price}"
        else:
            formatted_price = raw_price

        context.user_data["new_domain"]["price"] = formatted_price
        context.user_data["waiting_for"] = "add_domain_emoji"

        response_text = (
            "👉 **Select Emoji for Domain**\n\n"
            f"Domain: `{context.user_data['new_domain']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"Price: `{formatted_price}`\n\n"
            "Choose an emoji for your domain:"
        )

        keyboard = []
        emoji_row = []
        for i, emoji in enumerate(EMOJI_OPTIONS):
            emoji_row.append(
                InlineKeyboardButton(emoji, callback_data=f"domain_emoji_{emoji}")
            )
            if (i + 1) % 5 == 0:
                keyboard.append(emoji_row)
                emoji_row = []

        if emoji_row:
            keyboard.append(emoji_row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    "✏️ Custom Emoji", callback_data="domain_emoji_custom"
                ),
                InlineKeyboardButton("⏭️ Skip", callback_data="domain_emoji_skip"),
            ]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")]
        )

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_domain_emoji_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "domain_emoji_skip":

        context.user_data["new_domain"]["emoji"] = ""
        context.user_data["waiting_for"] = "add_domain_registrar"

        response_text = (
            "🌐 **Enter Registrar**\n\n"
            f"Domain: `{context.user_data['new_domain']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"Price: `{context.user_data['new_domain']['price']}`\n"
            f"Emoji: `No emoji selected`\n\n"
            "Please enter the registrar name:"
        )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "domain_emoji_custom":

        context.user_data["waiting_for"] = "add_domain_custom_emoji"

        response_text = (
            "✏️ **Enter Custom Emoji**\n\n"
            f"Domain: `{context.user_data['new_domain']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"Price: `{context.user_data['new_domain']['price']}`\n\n"
            "Please type your custom emoji (e.g., 🚀, ⭐, 🔥):"
        )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    else:

        selected_emoji = query.data.replace("domain_emoji_", "")
        context.user_data["new_domain"]["emoji"] = selected_emoji
        context.user_data["waiting_for"] = "add_domain_registrar"

        response_text = (
            "🌐 **Enter Registrar**\n\n"
            f"Domain: `{context.user_data['new_domain']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"Price: `{context.user_data['new_domain']['price']}`\n"
            f"Emoji: `{selected_emoji}`\n\n"
            "Please enter the registrar name:"
        )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_edit_currency_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    currency = query.data.replace("edit_currency_", "").upper()

    if context.user_data.get("waiting_for") == "edit_server_currency":
        try:
            servers = load_servers()
            server_name = context.user_data["edit_server"]["name"]
            price_amount = context.user_data["edit_server"]["price_amount"]

            if server_name in servers:

                if currency == "USD":
                    new_price = f"${price_amount}"
                elif currency == "EUR":
                    new_price = f"€{price_amount}"
                else:
                    new_price = price_amount

                servers[server_name]["price"] = new_price
                servers[server_name]["last_updated"] = datetime.now().isoformat()

                save_servers(servers)

                await query.edit_message_text(
                    f"✅ **Server Price Updated Successfully!**\n\n"
                    f"• Server: `{server_name}`\n"
                    f"• New Price: `{new_price}`\n"
                    f"• Status: `Updated and saved`",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "Edit Another Field",
                                    callback_data=f"edit_server_select_{server_name}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "⏎ Back to Servers", callback_data="servers_menu"
                                )
                            ],
                        ]
                    ),
                )

                context.user_data.pop("waiting_for", None)
                context.user_data.pop("edit_server", None)
            else:
                await query.edit_message_text(
                    "❌ **Server Not Found**\n\n"
                    f"Server `{server_name}` was not found in the system.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "⏎ Back to Servers", callback_data="servers_menu"
                                )
                            ],
                        ]
                    ),
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Error Updating Price**\n\n"
                f"Failed to update server price: {str(e)}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⏎ Back to Servers", callback_data="servers_menu"
                            )
                        ],
                    ]
                ),
            )


async def handle_edit_server_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    server_name = query.data.replace("edit_server_select_", "")

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "**Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        server_info = servers[server_name]
        settings = load_settings()
        warning_days = settings.get("warning_days", 5)
        status, days_diff = get_server_status(server_info["date"], warning_days)
        days_text = format_status_text(days_diff)

        emoji = server_info.get("emoji", "🖥️")
        label = server_info.get("label", "")

        text = (
            "**Current Details:**\n"
            f"• Name: `{server_name}`\n"
            f"• Renewal Date: `{server_info['date']}`\n"
            f"• Status: `{days_text}`\n"
            f"• Price: `{server_info['price']}`\n"
            f"• Datacenter: `{server_info['datacenter']}`"
        )

        if label:
            text += f"\n• Label: `{label}`"

        text += "\n\nWhat would you like to edit?"

        keyboard = [
            [
                InlineKeyboardButton(
                    "Name", callback_data=f"edit_field_name_{server_name}"
                ),
                InlineKeyboardButton(
                    "Renewal Date", callback_data=f"edit_field_date_{server_name}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Price", callback_data=f"edit_field_price_{server_name}"
                ),
                InlineKeyboardButton(
                    "Datacenter", callback_data=f"edit_field_datacenter_{server_name}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Label", callback_data=f"edit_field_label_{server_name}"
                ),
                InlineKeyboardButton(
                    "Emoji", callback_data=f"edit_field_emoji_{server_name}"
                ),
            ],
            [
                InlineKeyboardButton("Back to Edit Menu", callback_data="edit_server"),
            ],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to load server details: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_edit_domain_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    domain_name = query.data.replace("edit_domain_select_", "")

    try:
        domains = load_domains()

        if domain_name not in domains:
            text = (
                "**Domain Not Found**\n\n"
                f"Domain `{domain_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Domains", callback_data="domains_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        domain_info = domains[domain_name]
        settings = load_settings()
        warning_days = settings.get("warning_days", 5)
        status, days_diff = get_server_status(domain_info["date"], warning_days)
        days_text = format_status_text(days_diff)

        emoji = domain_info.get("emoji", "")
        label = domain_info.get("label", "")

        text = (
            "**Current Details:**\n"
            f"• Name: `{domain_name}`\n"
            f"• Renewal Date: `{domain_info['date']}`\n"
            f"• Status: `{days_text}`\n"
            f"• Price: `{domain_info['price']}`\n"
            f"• Registrar: `{domain_info['registrar']}`"
        )

        if label:
            text += f"\n• Label: `{label}`"

        text += "\n\nWhat would you like to edit?"

        keyboard = [
            [
                InlineKeyboardButton(
                    "Name", callback_data=f"edit_domain_field_name_{domain_name}"
                ),
                InlineKeyboardButton(
                    "Renewal Date",
                    callback_data=f"edit_domain_field_date_{domain_name}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Price", callback_data=f"edit_domain_field_price_{domain_name}"
                ),
                InlineKeyboardButton(
                    "Registrar",
                    callback_data=f"edit_domain_field_registrar_{domain_name}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Label", callback_data=f"edit_domain_field_label_{domain_name}"
                ),
                InlineKeyboardButton(
                    "Emoji", callback_data=f"edit_domain_field_emoji_{domain_name}"
                ),
            ],
            [
                InlineKeyboardButton("Back to Edit Menu", callback_data="edit_domain"),
            ],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to load domain details: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 3)
    if len(parts) < 4:
        return

    field = parts[2]
    server_name = parts[3]

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "**Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        server_info = servers[server_name]

        if field == "date":
            context.user_data["edit_server"] = {"name": server_name, "field": "date"}
            context.user_data["waiting_for"] = "edit_server_date"

            text = (
                f"**Edit Renewal Date**\n\n"
                f"Server: `{server_name}`\n"
                f"Current Date: `{server_info['date']}`\n\n"
                "Please enter the new renewal date in `YYYY-MM-DD` format:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "price":
            context.user_data["edit_server"] = {"name": server_name, "field": "price"}
            context.user_data["waiting_for"] = "edit_server_price"

            text = (
                f"**Edit Server Price**\n\n"
                f"Server: `{server_name}`\n"
                f"Current Price: `{server_info['price']}`\n\n"
                "Please enter the new monthly price:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "datacenter":
            context.user_data["edit_server"] = {
                "name": server_name,
                "field": "datacenter",
            }
            context.user_data["waiting_for"] = "edit_server_datacenter"

            text = (
                f"**Edit Datacenter**\n\n"
                f"Server: `{server_name}`\n"
                f"Current Datacenter: `{server_info['datacenter']}`\n\n"
                "Please enter the new datacenter/provider name:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "label":
            labels = load_labels()
            current_label = server_info.get("label", "")

            if "server_label_page" not in context.user_data:
                context.user_data["server_label_page"] = 0

            page = context.user_data["server_label_page"]
            labels_per_page = 8
            start_idx = page * labels_per_page
            end_idx = start_idx + labels_per_page
            page_labels = labels[start_idx:end_idx]
            total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

            text = (
                f"**Edit Server Label**\n\n"
                f"Server: `{server_name}`\n"
                f"Current Label: `{current_label if current_label else 'None'}`\n\n"
                f"Page {page + 1} of {total_pages} ({len(labels)} total labels)\n\n"
                "Select a new label:"
            )

            keyboard = []

            for label in page_labels:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"{label}", callback_data=f"set_label_{server_name}_{label}"
                        )
                    ]
                )

            if total_pages > 1:
                pagination_row = []
                if page > 0:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "⬅️ Previous",
                            callback_data=f"server_label_page_{server_name}_{page-1}",
                        )
                    )
                if page < total_pages - 1:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "Next ➡️",
                            callback_data=f"server_label_page_{server_name}_{page+1}",
                        )
                    )
                if pagination_row:
                    keyboard.append(pagination_row)

            if current_label:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "Remove Label",
                            callback_data=f"set_label_{server_name}_REMOVE",
                        )
                    ]
                )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                    )
                ]
            )

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "name":
            context.user_data["edit_server"] = {"name": server_name, "field": "name"}
            context.user_data["waiting_for"] = "edit_server_name"

            text = (
                f"**Edit Server Name**\n\n"
                f"Current Name: `{server_name}`\n\n"
                "Please enter the new server name:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        elif field == "emoji":
            current_emoji = server_info.get("emoji", "🖥️")

            text = (
                f"**Edit Server Emoji**\n\n"
                f"Server: `{server_name}`\n"
                f"Current Emoji: `{current_emoji}`\n\n"
                "Select a new emoji:"
            )

            keyboard = []

            for i in range(0, len(EMOJI_OPTIONS), 5):
                row = []
                for emoji in EMOJI_OPTIONS[i : i + 5]:
                    row.append(
                        InlineKeyboardButton(
                            emoji, callback_data=f"set_emoji_{server_name}_{emoji}"
                        )
                    )
                keyboard.append(row)

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "✏️ Custom Emoji",
                        callback_data=f"edit_emoji_custom_{server_name}",
                    ),
                    InlineKeyboardButton(
                        "🗑️ Delete Emoji", callback_data=f"delete_emoji_{server_name}"
                    ),
                ]
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                    )
                ]
            )

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to edit server field: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_delete_emoji(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    server_name = query.data.replace("delete_emoji_", "")

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "**Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        servers[server_name]["emoji"] = ""
        save_servers(servers)

        text = (
            "🗑️ **Server Emoji Deleted**\n\n"
            f"Server: `{server_name}`\n"
            f"Emoji: `Removed`\n\n"
            "✅ Changes saved successfully!"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "Edit Another Field",
                    callback_data=f"edit_server_select_{server_name}",
                )
            ],
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to delete server emoji: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_edit_domain_field(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 4)
    if len(parts) < 5:
        return

    field = parts[3]
    domain_name = parts[4]

    try:
        domains = load_domains()

        if domain_name not in domains:
            text = (
                "**Domain Not Found**\n\n"
                f"Domain `{domain_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Domains", callback_data="domains_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        domain_info = domains[domain_name]

        if field == "date":
            context.user_data["edit_domain"] = {"name": domain_name, "field": "date"}
            context.user_data["waiting_for"] = "edit_domain_date"

            text = (
                f"**Edit Domain Renewal Date**\n\n"
                f"Domain: `{domain_name}`\n"
                f"Current Date: `{domain_info['date']}`\n\n"
                "Please enter the new renewal date in `YYYY-MM-DD` format:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "price":
            context.user_data["edit_domain"] = {"name": domain_name, "field": "price"}
            context.user_data["waiting_for"] = "edit_domain_price"

            text = (
                f"**Edit Domain Price**\n\n"
                f"Domain: `{domain_name}`\n"
                f"Current Price: `{domain_info['price']}`\n\n"
                "Please enter the new annual price:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "registrar":
            context.user_data["edit_domain"] = {
                "name": domain_name,
                "field": "registrar",
            }
            context.user_data["waiting_for"] = "edit_domain_registrar"

            text = (
                f"**Edit Domain Registrar**\n\n"
                f"Domain: `{domain_name}`\n"
                f"Current Registrar: `{domain_info['registrar']}`\n\n"
                "Please enter the new registrar name:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "name":
            context.user_data["edit_domain"] = {"name": domain_name, "field": "name"}
            context.user_data["waiting_for"] = "edit_domain_name"

            text = (
                f"**Edit Domain Name**\n\n"
                f"Current Name: `{domain_name}`\n\n"
                "Please enter the new domain name:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        elif field == "label":
            labels = load_labels()
            current_label = domain_info.get("label", "")

            if "domain_label_page" not in context.user_data:
                context.user_data["domain_label_page"] = 0

            page = context.user_data["domain_label_page"]
            labels_per_page = 8
            start_idx = page * labels_per_page
            end_idx = start_idx + labels_per_page
            page_labels = labels[start_idx:end_idx]
            total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

            text = (
                f"**Edit Domain Label**\n\n"
                f"Domain: `{domain_name}`\n"
                f"Current Label: `{current_label if current_label else 'None'}`\n\n"
                f"Page {page + 1} of {total_pages} ({len(labels)} total labels)\n\n"
                "Select a new label:"
            )

            keyboard = []

            for label in page_labels:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"{label}",
                            callback_data=f"set_domain_label_{domain_name}_{label}",
                        )
                    ]
                )

            if total_pages > 1:
                pagination_row = []
                if page > 0:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "⬅️ Previous",
                            callback_data=f"domain_label_page_{domain_name}_{page-1}",
                        )
                    )
                if page < total_pages - 1:
                    pagination_row.append(
                        InlineKeyboardButton(
                            "Next ➡️",
                            callback_data=f"domain_label_page_{domain_name}_{page+1}",
                        )
                    )
                if pagination_row:
                    keyboard.append(pagination_row)

            if current_label:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "Remove Label",
                            callback_data=f"set_domain_label_{domain_name}_REMOVE",
                        )
                    ]
                )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                    )
                ]
            )

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif field == "emoji":
            current_emoji = domain_info.get("emoji", "")

            text = (
                f"**Edit Domain Emoji**\n\n"
                f"Domain: `{domain_name}`\n"
                f"Current Emoji: `{current_emoji if current_emoji else 'None'}`\n\n"
                "Select a new emoji:"
            )

            keyboard = []

            for i in range(0, len(EMOJI_OPTIONS), 5):
                row = []
                for emoji in EMOJI_OPTIONS[i : i + 5]:
                    row.append(
                        InlineKeyboardButton(
                            emoji,
                            callback_data=f"set_domain_emoji_{domain_name}_{emoji}",
                        )
                    )
                row.append(row)

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "✏️ Custom Emoji",
                        callback_data=f"edit_domain_emoji_custom_{domain_name}",
                    ),
                    InlineKeyboardButton(
                        "🗑️ Delete Emoji",
                        callback_data=f"delete_domain_emoji_{domain_name}",
                    ),
                ]
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                    )
                ]
            )

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to edit domain field: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_delete_domain_emoji(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    domain_name = query.data.replace("delete_domain_emoji_", "")

    try:
        domains = load_domains()

        if domain_name not in domains:
            text = (
                "**Domain Not Found**\n\n"
                f"Domain `{domain_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Domains", callback_data="domains_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        domains[domain_name]["emoji"] = ""
        save_domains(domains)

        text = (
            "🗑️ **Domain Emoji Deleted**\n\n"
            f"Domain: `{domain_name}`\n"
            f"Emoji: `Removed`\n\n"
            "✅ Changes saved successfully!"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "Edit Another Field",
                    callback_data=f"edit_domain_select_{domain_name}",
                )
            ],
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to delete domain emoji: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_set_label(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 3)
    if len(parts) < 4:
        return

    server_name = parts[2]
    label = parts[3]

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "**Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        if label == "REMOVE":
            servers[server_name]["label"] = ""
            label_text = "removed"
        else:
            servers[server_name]["label"] = label
            label_text = f"set to `{label}`"

        save_servers(servers)

        text = (
            "🏷️ **Server Label Updated**\n\n"
            f"Server: `{server_name}`\n"
            f"Label {label_text}\n\n"
            "✅ Changes saved successfully!"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "Edit Another Field",
                    callback_data=f"edit_server_select_{server_name}",
                )
            ],
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to update server label: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_set_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 3)
    if len(parts) < 4:
        return

    server_name = parts[2]
    emoji = parts[3]

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "**Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        servers[server_name]["emoji"] = emoji
        save_servers(servers)

        text = (
            "🎨 **Server Emoji Updated**\n\n"
            f"Server: `{server_name}`\n"
            f"New Emoji: {emoji}\n\n"
            "✅ Changes saved successfully!"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "Edit Another Field",
                    callback_data=f"edit_server_select_{server_name}",
                )
            ],
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to update server emoji: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_edit_emoji_custom(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    server_name = query.data.replace("edit_emoji_custom_", "")

    try:
        servers = load_servers()

        if server_name not in servers:
            text = (
                "**Server Not Found**\n\n"
                f"Server `{server_name}` was not found in the system."
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Servers", callback_data="servers_menu"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        context.user_data["edit_server"] = {"name": server_name, "field": "emoji"}
        context.user_data["waiting_for"] = "edit_server_custom_emoji"

        current_emoji = servers[server_name].get("emoji", "🖥️")

        text = (
            f"✏️ **Enter Custom Emoji**\n\n"
            f"Server: `{server_name}`\n"
            f"Current Emoji: {current_emoji}\n\n"
            "Please type your custom emoji (e.g., 🚀, ⭐, 🔥):"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                )
            ],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        text = "❌ **Error**\n\n" f"Failed to setup custom emoji input: {str(e)}"

        keyboard = [
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_set_server_label(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    selected_label = query.data.replace("set_server_label_", "")

    try:

        context.user_data["new_server"]["label"] = selected_label
        if "emoji" not in context.user_data["new_server"]:
            context.user_data["new_server"]["emoji"] = ""

        servers = load_servers()
        server_name = context.user_data["new_server"]["name"]
        servers[server_name] = {
            "date": context.user_data["new_server"]["date"],
            "price": context.user_data["new_server"]["price"],
            "datacenter": context.user_data["new_server"]["datacenter"],
            "emoji": context.user_data["new_server"]["emoji"],
            "label": selected_label,
        }
        save_servers(servers)

        emoji_text = context.user_data["new_server"].get("emoji", "")
        if emoji_text and emoji_text.strip():
            emoji_display = f"• Emoji: `{emoji_text}`"
        else:
            emoji_display = "• Emoji: `No emoji selected`"

        response_text = (
            "✅ **Server Added Successfully!**\n\n"
            f"• Name: `{server_name}`\n"
            f"{emoji_display}\n"
            f"• Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"• Price: `{context.user_data['new_server']['price']}`\n"
            f"• Datacenter: `{context.user_data['new_server']['datacenter']}`\n"
            f"• Label: `{selected_label}`"
        )

        keyboard = [
            [InlineKeyboardButton("➕ Add Another Server", callback_data="add_server")],
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        context.user_data.pop("waiting_for", None)
        context.user_data.pop("new_server", None)

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error adding server: {str(e)}", parse_mode="Markdown"
        )


async def handle_skip_server_label(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        context.user_data["new_server"]["label"] = ""
        if "emoji" not in context.user_data["new_server"]:
            context.user_data["new_server"]["emoji"] = ""

        servers = load_servers()
        server_name = context.user_data["new_server"]["name"]
        servers[server_name] = {
            "date": context.user_data["new_server"]["date"],
            "price": context.user_data["new_server"]["price"],
            "datacenter": context.user_data["new_server"]["datacenter"],
            "emoji": context.user_data["new_server"]["emoji"],
            "label": "",
        }
        save_servers(servers)

        emoji_text = context.user_data["new_server"].get("emoji", "")
        if emoji_text and emoji_text.strip():
            emoji_display = f"• Emoji: `{emoji_text}`"
        else:
            emoji_display = "• Emoji: `No emoji selected`"

        response_text = (
            "✅ **Server Added Successfully!**\n\n"
            f"• Name: `{server_name}`\n"
            f"{emoji_display}\n"
            f"• Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"• Price: `{context.user_data['new_server']['price']}`\n"
            f"• Datacenter: `{context.user_data['new_server']['datacenter']}`\n"
            f"• Label: `No label selected`"
        )

        keyboard = [
            [InlineKeyboardButton("➕ Add Another Server", callback_data="add_server")],
            [InlineKeyboardButton("⏎ Back to Servers", callback_data="servers_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        context.user_data.pop("waiting_for", None)
        context.user_data.pop("new_server", None)

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error adding server: {str(e)}", parse_mode="Markdown"
        )


async def handle_set_domain_label(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    selected_label = query.data.replace("set_domain_label_", "")

    try:

        context.user_data["new_domain"]["label"] = selected_label
        if "emoji" not in context.user_data["new_domain"]:
            context.user_data["new_domain"]["emoji"] = ""

        domains = load_domains()
        domain_name = context.user_data["new_domain"]["name"]
        domains[domain_name] = {
            "date": context.user_data["new_domain"]["date"],
            "price": context.user_data["new_domain"]["price"],
            "registrar": context.user_data["new_domain"]["registrar"],
            "emoji": context.user_data["new_domain"]["emoji"],
            "label": selected_label,
        }
        save_domains(domains)

        emoji_text = context.user_data["new_domain"].get("emoji", "")
        if emoji_text and emoji_text.strip():
            emoji_display = f"• Emoji: `{emoji_text}`"
        else:
            emoji_display = "• Emoji: `No emoji selected`"

        response_text = (
            "✅ **Domain Added Successfully!**\n\n"
            f"• Domain: `{domain_name}`\n"
            f"{emoji_display}\n"
            f"• Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"• Price: `{context.user_data['new_domain']['price']}`\n"
            f"• Registrar: `{context.user_data['new_domain']['registrar']}`\n"
            f"• Label: `{selected_label}`"
        )

        keyboard = [
            [InlineKeyboardButton("➕ Add Another Domain", callback_data="add_domain")],
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        context.user_data.pop("waiting_for", None)
        context.user_data.pop("new_domain", None)

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error adding domain: {str(e)}", parse_mode="Markdown"
        )


async def handle_skip_domain_label(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        context.user_data["new_domain"]["label"] = ""
        if "emoji" not in context.user_data["new_domain"]:
            context.user_data["new_domain"]["emoji"] = ""

        domains = load_domains()
        domain_name = context.user_data["new_domain"]["name"]
        domains[domain_name] = {
            "date": context.user_data["new_domain"]["date"],
            "price": context.user_data["new_domain"]["price"],
            "registrar": context.user_data["new_domain"]["registrar"],
            "emoji": context.user_data["new_domain"]["emoji"],
            "label": "",
        }
        save_domains(domains)

        emoji_text = context.user_data["new_domain"].get("emoji", "")
        if emoji_text and emoji_text.strip():
            emoji_display = f"• Emoji: `{emoji_text}`"
        else:
            emoji_display = "• Emoji: `No emoji selected`"

        response_text = (
            "✅ **Domain Added Successfully!**\n\n"
            f"• Domain: `{domain_name}`\n"
            f"{emoji_display}\n"
            f"• Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"• Price: `{context.user_data['new_domain']['price']}`\n"
            f"• Registrar: `{context.user_data['new_domain']['registrar']}`\n"
            f"• Label: `No label selected`"
        )

        keyboard = [
            [InlineKeyboardButton("➕ Add Another Domain", callback_data="add_domain")],
            [InlineKeyboardButton("⏎ Back to Domains", callback_data="domains_menu")],
        ]

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        context.user_data.pop("waiting_for", None)
        context.user_data.pop("new_domain", None)

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error adding domain: {str(e)}", parse_mode="Markdown"
        )


def create_labels_keyboard(labels, current_page, label_type, extra_data=""):
    keyboard = []
    labels_per_page = 8
    total_pages = (
        (len(labels) + labels_per_page - 1) // labels_per_page if labels else 1
    )

    current_page = max(0, min(current_page, total_pages - 1))

    start_idx = current_page * labels_per_page
    end_idx = min(start_idx + labels_per_page, len(labels))

    for label in labels[start_idx:end_idx]:
        if label_type == "server":
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}", callback_data=f"set_server_label_{label}"
                    )
                ]
            )
        elif label_type == "domain":
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}", callback_data=f"set_domain_label_{label}"
                    )
                ]
            )
        elif label_type == "edit_server":
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}", callback_data=f"set_label_{extra_data}_{label}"
                    )
                ]
            )
        elif label_type == "edit_domain":
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}",
                        callback_data=f"set_domain_label_{extra_data}_{label}",
                    )
                ]
            )

    if total_pages > 1:
        pagination_row = []
        if current_page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    "<<",
                    callback_data=f"{label_type}_labels_page_{current_page - 1}_{extra_data}",
                )
            )
        pagination_row.append(
            InlineKeyboardButton(
                f"{current_page + 1}/{total_pages}",
                callback_data=f"{label_type}_labels_page_info",
            )
        )
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    ">>",
                    callback_data=f"{label_type}_labels_page_{current_page + 1}_{extra_data}",
                )
            )
        keyboard.append(pagination_row)

    return keyboard


def get_labels_status():
    try:
        labels = load_labels()
        settings = load_settings()
        settings_labels = settings.get("labels", [])

        status = {
            "labels_json": labels,
            "settings_labels": settings_labels,
            "labels_count": len(labels),
            "settings_count": len(settings_labels),
        }

        logging.info(f"Labels status: {status}")
        return status
    except Exception as e:
        logging.error(f"Error getting labels status: {e}")
        return None


async def handle_server_labels_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        parts = query.data.split("_")
        if len(parts) >= 4 and parts[3].isdigit():
            current_page = int(parts[3])
        else:
            current_page = 0

        labels = load_labels()

        response_text = (
            "🏷️ **Select Label for Server**\n\n"
            f"Server: `{context.user_data['new_server']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_server']['date']}`\n"
            f"Price: `{context.user_data['new_server']['price']}`\n"
            f"Datacenter: `{context.user_data['new_server']['datacenter']}`\n\n"
            "Choose a label for your server:"
        )

        keyboard = create_labels_keyboard(labels, current_page, "server")

        keyboard.append(
            [InlineKeyboardButton("⏭️ Skip", callback_data="skip_server_label")]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data="servers_menu")]
        )

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error in pagination: {str(e)}", parse_mode="Markdown"
        )


async def handle_domain_labels_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        parts = query.data.split("_")
        if len(parts) >= 4 and parts[3].isdigit():
            current_page = int(parts[3])
        else:
            current_page = 0

        labels = load_labels()

        response_text = (
            "🏷️ **Select Label for Domain**\n\n"
            f"Domain: `{context.user_data['new_domain']['name']}`\n"
            f"Renewal Date: `{context.user_data['new_domain']['date']}`\n"
            f"Price: `{context.user_data['new_domain']['price']}`\n"
            f"Registrar: `{context.user_data['new_domain']['registrar']}`\n\n"
            "Choose a label for your domain:"
        )

        keyboard = create_labels_keyboard(labels, current_page, "domain")

        keyboard.append(
            [InlineKeyboardButton("⏭️ Skip", callback_data="skip_domain_label")]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data="domains_menu")]
        )

        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error in pagination: {str(e)}", parse_mode="Markdown"
        )


async def handle_edit_server_label_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        parts = query.data.split("_", 4)
        if len(parts) < 5:
            return

        server_name = parts[3]
        page = int(parts[4])

        context.user_data["server_label_page"] = page

        servers = load_servers()
        if server_name not in servers:
            return

        server_info = servers[server_name]
        labels = load_labels()
        current_label = server_info.get("label", "")

        labels_per_page = 8
        start_idx = page * labels_per_page
        end_idx = start_idx + labels_per_page
        page_labels = labels[start_idx:end_idx]
        total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

        text = (
            f"**Edit Server Label**\n\n"
            f"Server: `{server_name}`\n"
            f"Current Label: `{current_label if current_label else 'None'}`\n\n"
            f"Page {page + 1} of {total_pages} ({len(labels)} total labels)\n\n"
            "Select a new label:"
        )

        keyboard = []

        for label in page_labels:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}", callback_data=f"set_label_{server_name}_{label}"
                    )
                ]
            )

        if total_pages > 1:
            pagination_row = []
            if page > 0:
                pagination_row.append(
                    InlineKeyboardButton(
                        "⬅️ Previous",
                        callback_data=f"server_label_page_{server_name}_{page-1}",
                    )
                )
            if page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton(
                        "Next ➡️",
                        callback_data=f"server_label_page_{server_name}_{page+1}",
                    )
                )
            if pagination_row:
                keyboard.append(pagination_row)

        if current_label:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Remove Label", callback_data=f"set_label_{server_name}_REMOVE"
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"edit_server_select_{server_name}"
                )
            ]
        )

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error in pagination: {str(e)}", parse_mode="Markdown"
        )


async def handle_edit_domain_label_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        parts = query.data.split("_", 4)
        if len(parts) < 5:
            return

        domain_name = parts[3]
        page = int(parts[4])

        context.user_data["domain_label_page"] = page

        domains = load_domains()
        if domain_name not in domains:
            return

        domain_info = domains[domain_name]
        labels = load_labels()
        current_label = domain_info.get("label", "")

        labels_per_page = 8
        start_idx = page * labels_per_page
        end_idx = start_idx + labels_per_page
        page_labels = labels[start_idx:end_idx]
        total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

        text = (
            f"**Edit Domain Label**\n\n"
            f"Domain: `{domain_name}`\n"
            f"Current Label: `{current_label if current_label else 'None'}`\n\n"
            f"Page {page + 1} of {total_pages} ({len(labels)} total labels)\n\n"
            "Select a new label:"
        )

        keyboard = []

        for label in page_labels:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}",
                        callback_data=f"set_domain_label_{domain_name}_{label}",
                    )
                ]
            )

        if total_pages > 1:
            pagination_row = []
            if page > 0:
                pagination_row.append(
                    InlineKeyboardButton(
                        "⬅️ Previous",
                        callback_data=f"domain_label_page_{domain_name}_{page-1}",
                    )
                )
            if page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton(
                        "Next ➡️",
                        callback_data=f"domain_label_page_{domain_name}_{page+1}",
                    )
                )
            if pagination_row:
                keyboard.append(pagination_row)

        if current_label:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "Remove Label",
                        callback_data=f"set_domain_label_{domain_name}_REMOVE",
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"edit_domain_select_{domain_name}"
                )
            ]
        )

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error in pagination: {str(e)}", parse_mode="Markdown"
        )


async def handle_settings_label_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        parts = query.data.split("_")
        if len(parts) >= 4 and parts[3].isdigit():
            current_page = int(parts[3])
        else:
            current_page = 0

        context.user_data["settings_label_page"] = current_page

        labels = load_labels()

        labels_per_page = 10
        start_idx = current_page * labels_per_page
        end_idx = start_idx + labels_per_page
        page_labels = labels[start_idx:end_idx]
        total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

        text = (
            "🏷️ **Manage Labels**\n\n"
            f"Total labels: `{len(labels)}`\n"
            f"Page {current_page + 1} of {total_pages}\n\n"
            "**Available Labels:**\n"
        )

        if page_labels:
            for i, label in enumerate(page_labels, start_idx + 1):
                text += f"{i}. `{label}`\n"
        else:
            text += "No labels found."

        keyboard = []

        if total_pages > 1:
            pagination_row = []
            if current_page > 0:
                pagination_row.append(
                    InlineKeyboardButton(
                        "⬅️ Previous",
                        callback_data=f"settings_label_page_{current_page-1}",
                    )
                )
            if current_page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton(
                        "Next ➡️", callback_data=f"settings_label_page_{current_page+1}"
                    )
                )
            if pagination_row:
                keyboard.append(pagination_row)

        keyboard.extend(
            [
                [
                    InlineKeyboardButton("➕ Add Label", callback_data="add_label"),
                    InlineKeyboardButton(
                        "🗑️ Remove Label", callback_data="remove_label"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🔄 Refresh Labels", callback_data="manage_labels"
                    )
                ],
                [InlineKeyboardButton("⏎ Back to Settings", callback_data="settings")],
            ]
        )

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error in pagination: {str(e)}", parse_mode="Markdown"
        )


async def handle_remove_label_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    try:

        parts = query.data.split("_")
        if len(parts) >= 4 and parts[3].isdigit():
            current_page = int(parts[3])
        else:
            current_page = 0

        context.user_data["remove_label_page"] = current_page

        labels = load_labels()

        if not labels:
            text = "🏷️ **Remove Label**\n\n" "❌ No labels found to remove."

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏎ Back to Labels", callback_data="manage_labels"
                    )
                ],
            ]

            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        labels_per_page = 10
        start_idx = current_page * labels_per_page
        end_idx = start_idx + labels_per_page
        page_labels = labels[start_idx:end_idx]
        total_pages = (len(labels) + labels_per_page - 1) // labels_per_page

        text = (
            "🏷️ **Remove Label**\n\n"
            "⚠️ **Warning:** Removing a label will also remove it from all servers and domains using it.\n\n"
            f"Page {current_page + 1} of {total_pages} ({len(labels)} total labels)\n\n"
            "Select a label to remove:"
        )

        keyboard = []

        for label in page_labels:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{label}", callback_data=f"remove_label_{label}"
                    )
                ]
            )

        if total_pages > 1:
            pagination_row = []
            if current_page > 0:
                pagination_row.append(
                    InlineKeyboardButton(
                        "⬅️ Previous",
                        callback_data=f"remove_label_page_{current_page-1}",
                    )
                )
            if current_page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton(
                        "Next ➡️", callback_data=f"remove_label_page_{current_page+1}"
                    )
                )
            if pagination_row:
                keyboard.append(pagination_row)

        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data="manage_labels")]
        )

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ Error in pagination: {str(e)}", parse_mode="Markdown"
        )


async def debug_labels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        status = get_labels_status()
        if status:
            text = (
                "🔍 **Labels Debug Information**\n\n"
                f"• Labels from labels.json: `{status['labels_json']}`\n"
                f"• Labels from settings.json: `{status['settings_labels']}`\n"
                f"• Count in labels.json: `{status['labels_count']}`\n"
                f"• Count in settings.json: `{status['settings_count']}`\n\n"
                "Use this command to verify label synchronization."
            )
        else:
            text = "❌ **Error getting labels status**"

        await update.message.reply_text(text=text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error in debug_labels: {str(e)}", parse_mode="Markdown"
        )


def setup_bot():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    config = load_config()
    token = config.get("TOKEN")
    chat_ids = config.get("CHAT_IDS", [])

    if not token:
        print("Error: No bot token found in config.json")
        return

    if not chat_ids:
        print("Error: No chat IDs found in config.json")
        return

    print(f"Creating application with token: {token[:10]}...")

    async def _set_bot_commands(app: Application):
        try:
            await app.bot.set_my_commands(
                [
                    BotCommand("start", "Open main menu"),
                    BotCommand("servers", "Manage servers"),
                    BotCommand("domains", "Manage domains"),
                    BotCommand("settings", "Open settings"),
                    BotCommand("dashboard", "View dashboard"),
                    BotCommand("notify", "Send daily expiration summary now"),
                ]
            )
        except Exception:

            pass

    application = (
        Application.builder().token(token).post_init(_set_bot_commands).build()
    )

    application.add_handler(MessageHandler(filters.ALL, auth_guard), group=-1)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notify", notify_cmd))
    application.add_handler(CommandHandler("servers", servers_menu))
    application.add_handler(CommandHandler("domains", domains_menu))
    application.add_handler(CommandHandler("dashboard", dashboard_menu))
    application.add_handler(CommandHandler("settings", settings_menu))
    application.add_handler(CommandHandler("debug_labels", debug_labels))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    try:
        settings = load_settings()
        hour = int(settings.get("notification_hour", 9))
        minute = int(settings.get("notification_minute", 0))
        daily_enabled = settings.get("daily_notifications", True)

        if daily_enabled:
            scheduler = AsyncIOScheduler(timezone=TIMEZONE)
            scheduler.add_job(
                lambda: asyncio.create_task(run_daily_notifications()),
                CronTrigger(hour=hour, minute=minute),
            )
            scheduler.start()
            print(
                f"⏰ Daily notifications scheduled at {hour:02d}:{minute:02d} ({TIMEZONE})"
            )
        else:
            print("⏰ Daily notifications are disabled in settings")
    except Exception as e:
        print(f"[WARNING] Failed to schedule daily notifications: {e}")

    print("Bot is starting...")
    application.run_polling()


async def main() -> None:
    setup_bot()


if __name__ == "__main__":
    setup_bot()
