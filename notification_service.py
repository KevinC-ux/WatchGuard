import asyncio
import logging
from typing import Optional
from telegram import Bot
from data_manager import DataChangeEvent, get_shared_data_manager


class BotNotificationHandler:

    def __init__(self, bot_token: str = None, chat_ids: list = None):
        self.bot_token = bot_token
        self.chat_ids = chat_ids or []
        self.bot: Optional[Bot] = None
        self.enabled = False

        if bot_token and chat_ids:
            self.bot = Bot(token=bot_token)
            self.enabled = True

        shared_dm = get_shared_data_manager()
        shared_dm.add_observer(self.handle_data_change)

    def update_config(self, bot_token: str, chat_ids: list):
        self.bot_token = bot_token
        self.chat_ids = chat_ids

        if bot_token and chat_ids:
            self.bot = Bot(token=bot_token)
            self.enabled = True
        else:
            self.enabled = False

    def handle_data_change(self, event: DataChangeEvent):
        if not self.enabled or not self.bot or not self.chat_ids:
            return

        try:

            asyncio.create_task(self._send_notification(event))
        except Exception as e:
            logging.error(f"Error creating notification task: {e}")

    async def _send_notification(self, event: DataChangeEvent):
        try:
            message = self._format_notification_message(event)
            if not message:
                return

            for chat_id in self.chat_ids:
                try:
                    await self.bot.send_message(
                        chat_id=chat_id, text=message, parse_mode="Markdown"
                    )
                except Exception as e:
                    logging.error(f"Error sending notification to {chat_id}: {e}")

        except Exception as e:
            logging.error(f"Error in _send_notification: {e}")

    def _format_notification_message(self, event: DataChangeEvent) -> str:

        if event.data_type == "server":

            custom_emoji = event.data.get("emoji", "🔹") if event.data else "🔹"
            if custom_emoji == "🔹":
                emoji = "👉"
            else:
                emoji = custom_emoji

            if event.event_type == "add":
                return (
                    f"✅ New Server Added\n\n"
                    f"{emoji} {event.item_name}\n"
                    f"• Expiration Date: `{event.data.get('date', 'Not specified')}`\n"
                    f"• Price: `{event.data.get('price', 'Not specified')}`\n"
                    f"• Datacenter: `{event.data.get('datacenter', 'Not specified')}`\n"
                    f"• Label: `{event.data.get('label', 'None') if event.data.get('label') else 'None'}`\n\n"
                    f"- Added via WebPanel"
                )
            elif event.event_type == "update":
                return (
                    f"✅ Server Updated\n\n"
                    f"{emoji} {event.item_name}\n"
                    f"• Expiration Date: `{event.data.get('date', 'Not specified')}`\n"
                    f"• Price: `{event.data.get('price', 'Not specified')}`\n"
                    f"• Datacenter: `{event.data.get('datacenter', 'Not specified')}`\n"
                    f"• Label: `{event.data.get('label', 'None') if event.data.get('label') else 'None'}`\n\n"
                    f"- Updated via WebPanel"
                )
            elif event.event_type == "delete":
                return (
                    f"🗑️ `{event.item_name}` has been removed from the system.\n\n"
                    f"- Deleted via WebPanel"
                )

        elif event.data_type == "domain":

            custom_emoji = event.data.get("emoji", "🔹") if event.data else "🔹"
            if custom_emoji == "🔹":
                emoji = "👉"
            else:
                emoji = custom_emoji

            if event.event_type == "add":
                return (
                    f"✅ New Domain Added\n\n"
                    f"{emoji} {event.item_name}\n"
                    f"• Expiration Date: `{event.data.get('date', 'Not specified')}`\n"
                    f"• Price: `{event.data.get('price', 'Not specified')}`\n"
                    f"• Registrar: `{event.data.get('registrar', 'Not specified')}`\n\n"
                    f"- Added via WebPanel"
                )
            elif event.event_type == "update":
                return (
                    f"✅ Domain Updated\n\n"
                    f"{emoji} {event.item_name}\n"
                    f"• Expiration Date: `{event.data.get('date', 'Not specified')}`\n"
                    f"• Price: `{event.data.get('price', 'Not specified')}`\n"
                    f"• Registrar: `{event.data.get('registrar', 'Not specified')}`\n\n"
                    f"- Updated via WebPanel"
                )
            elif event.event_type == "delete":
                return (
                    f"🗑️ `{event.item_name}` has been removed from the system.\n\n"
                    f"- Deleted via WebPanel"
                )

        elif event.data_type == "settings":
            return (
                f"⚙️ Settings Updated\n\n"
                f"• Warning Days: `{event.data.get('warning_days', 'Not specified')}`\n"
                f"• Notification Time: `{event.data.get('notification_hour', 9):02d}:{event.data.get('notification_minute', 0):02d}`\n"
                f"• Daily Notifications: `{'Enabled' if event.data.get('daily_notifications', True) else 'Disabled'}`\n\n"
                f"- Updated via WebPanel"
            )
        elif event.data_type == "label":
            if event.event_type == "add":
                return (
                    f"🏷️ New Label Added\n\n"
                    f"• Name: `{event.item_name}`\n\n"
                    f"- Added via WebPanel"
                )
            elif event.event_type == "delete":
                return (
                    f"🗑️ Label Removed\n\n"
                    f"• Name: `{event.item_name}`\n\n"
                    f"- Deleted via WebPanel"
                )

        return ""


_notification_handler = None


def get_notification_handler() -> BotNotificationHandler:
    global _notification_handler

    if _notification_handler is None:
        _notification_handler = BotNotificationHandler()

    return _notification_handler


def setup_bot_notifications(bot_token: str, chat_ids: list):
    handler = get_notification_handler()
    handler.update_config(bot_token, chat_ids)
    logging.info("Bot notifications enabled")
