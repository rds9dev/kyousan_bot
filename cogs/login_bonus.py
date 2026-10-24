import asyncio
import datetime
import logging
import discord
from discord.ext import commands, tasks
import database
from config import JST, ALLOWED_GUILD_ID

logger = logging.getLogger(__name__)

class LoginBonusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.monthly_points_reset.start()

    def cog_unload(self):
        self.monthly_points_reset.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.guild.id != ALLOWED_GUILD_ID:
            return

        now_jst = datetime.datetime.now(JST)
        today_date = now_jst.date()
        current_month_str = now_jst.strftime("%Y-%m")

        msg_text = message.content.strip()
        if not msg_text:
            if message.attachments:
                msg_text = f"[Attachment: {len(message.attachments)}]"
            elif message.stickers:
                msg_text = f"[Sticker: {message.stickers[0].id}]"
            else:
                msg_text = "[Empty Media]"

        is_first_login, consecutive_days, total_points = await asyncio.to_thread(
            database.process_user_login_and_points,
            message.author.id,
            msg_text,
            today_date,
            current_month_str
        )

        if is_first_login:
            reply_text = f"-# ログインしました！\n-# {consecutive_days}日連続 | {total_points}point"
            try:
                target_channel = message.channel
                from config import LOGIN_NOTIFY_CHANNEL_ID
                if LOGIN_NOTIFY_CHANNEL_ID:
                    ch = self.bot.get_channel(LOGIN_NOTIFY_CHANNEL_ID)
                    if ch:
                        target_channel = ch
                        
                await target_channel.send(reply_text, delete_after=5.0)
            except discord.HTTPException as e:
                logger.warning("ログイン通知の送信に失敗しました: %s", e)

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=5, tzinfo=JST))
    async def monthly_points_reset(self):
        now_jst = datetime.datetime.now(JST)
        if now_jst.day != 1:
            return
        prev_month = (now_jst.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
        curr_month = now_jst.strftime("%Y-%m")
        await asyncio.to_thread(database.reset_monthly_points_for_all, curr_month, prev_month)
        logger.info("月初一括ポイントリセット完了: %s -> %s", prev_month, curr_month)

    @monthly_points_reset.before_loop
    async def before_monthly_points_reset(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LoginBonusCog(bot))
