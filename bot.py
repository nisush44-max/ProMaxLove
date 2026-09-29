import os
import asyncio
from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from config import API_ID, API_HASH, BOT_TOKEN


def _validate_config():
    missing=[]
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if missing:
        raise RuntimeError(
            "Missing required Render environment variable(s): " + ", ".join(missing) +
            ". Add them in Render → Environment, then redeploy. "
            "The bot will not open an interactive phone-number prompt on a server."
        )


_validate_config()


class Bot(Client):
    def __init__(self):
        super().__init__(
            "vj_join_request_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
            workers=50,
            sleep_threshold=10,
        )
        self.rich_callback_poller = None

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.username = "@" + (me.username or "")

        # Publish the command menu for ALL users.  Previously only the
        # Telegram/BotFather default (often just /start) was visible.
        await self._set_command_menus()

        try:
            from plugins.rich_callback_poll import RichCallbackPoller
            self.rich_callback_poller = RichCallbackPoller(self)
            await self.rich_callback_poller.start()
        except Exception as exc:
            print(f"[Rich] callback poller could not start: {exc}")
        print(f"Bot Started: @{me.username or me.id}")

    async def _set_command_menus(self):
        """Install separate command menus for normal users and admins."""
        user_commands = [
            BotCommand("start", "🚀 Start the bot"),
            BotCommand("login", "🔐 Connect your Telegram account"),
            BotCommand("logout", "🚪 Remove saved Telegram session"),
            BotCommand("accept", "⚡ Accept pending join requests"),
            BotCommand("mystats", "📊 View your personal statistics"),
        ]

        admin_commands = user_commands + [
            BotCommand("admin", "🛠 Open admin control center"),
            BotCommand("stats", "📈 View global bot statistics"),
            BotCommand("ban", "🚫 Ban a user"),
            BotCommand("unban", "✅ Unban a user"),
            BotCommand("broadcast", "📢 Broadcast a replied message"),
        ]

        try:
            # Private-chat scope: every normal user gets the complete user menu.
            # This intentionally overrides a stale BotFather command list.
            await self.set_bot_commands(
                user_commands,
                scope=BotCommandScopeAllPrivateChats(),
            )

            # Keep the default scope aligned as well for clients that fall back
            # to it when resolving the command menu.
            await self.set_bot_commands(
                user_commands,
                scope=BotCommandScopeDefault(),
            )

            # Explicit admin scopes: each configured admin gets the full menu.
            from config import ADMINS
            admin_ids = ADMINS if isinstance(ADMINS, (list, tuple, set)) else [ADMINS]
            for admin_id in admin_ids:
                try:
                    await self.set_bot_commands(
                        admin_commands,
                        scope=BotCommandScopeChat(chat_id=int(admin_id)),
                    )
                except Exception as exc:
                    print(f"[Commands] admin scope failed for {admin_id}: {exc}")

            print("[Commands] user + admin command menus installed")
        except Exception as exc:
            print(f"[Commands] command menu setup failed: {exc}")

    async def stop(self, *args):
        if self.rich_callback_poller:
            try:
                await self.rich_callback_poller.stop()
            except Exception:
                pass
        await super().stop()
        print("Bot Stopped Bye")


Bot().run()
