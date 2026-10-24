import asyncio
import logging
import discord
from discord.ext import commands

import config
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

database.init_db()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

UNAUTHORIZED_GUILD_WARNING = (
    "**【Discord System Notice】**\n"
    "このアプリケーション（ID: 1370574936963285052 専用）は、認可されたギルド以外での利用が制限されています。\n"
    "未認可ギルドからのインタラクションおよびアクセス要求はすべてブロックされました。"
)

TARGET_USER_WARNING_DM = (
    "**【Discord System Notice】**\n"
    "アカウント通知: 違反警告\n\n"
    "対象アカウント識別子: `{user_id}`\n\n"
    "システム監視プロトコルにより、貴殿のアカウントから利用規約およびガイドラインに抵触する不正なアクセス・操作試行が検知されました。\n\n"
    "■ **措置内容**\n"
    "本通知は重大な規律違反に対する一度限りの公式システム警告です。直ちに該当するすべての不正操作・通信を停止してください。\n\n"
    "■ **今後の対応について**\n"
    "本通知以降も同様の不審な挙動または不正アクセスが確認された場合、事前の通告なくアカウントのアクセス遮断および関連サーバーからの恒久的な利用停止措置が執行されます。"
)

class KyosanBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            member_cache_flags=discord.MemberCacheFlags.none(),
            chunk_guilds_at_startup=False,
            max_messages=5
        )

    async def setup_hook(self):
        async def global_interaction_check(interaction: discord.Interaction) -> bool:
            if interaction.guild_id != config.ALLOWED_GUILD_ID:
                if not interaction.response.is_done():
                    await interaction.response.send_message(UNAUTHORIZED_GUILD_WARNING, ephemeral=True)
                return False
            return True

        self.tree.interaction_check = global_interaction_check

        initial_extensions = [
            "cogs.activity",
            "cogs.akeome",
            "cogs.admin",
            "cogs.fun",
            "cogs.login_bonus",
        ]
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
            except Exception as e:
                logger.error("Failed to load extension %s: %s", ext, e)

        await self.tree.sync()
        logger.info("Command tree synced.")

bot = KyosanBot()

async def enforce_guild_restriction(guild: discord.Guild):
    if guild.id == config.ALLOWED_GUILD_ID:
        return
    logger.warning("不正なギルドへの参加を検知: %s (%s)", guild.name, guild.id)
    target_channel = guild.system_channel
    if not target_channel:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                target_channel = ch
                break
    if target_channel:
        try:
            await target_channel.send(UNAUTHORIZED_GUILD_WARNING)
        except Exception as e:
            logger.warning("警告文送信失敗: %s", e)
    try:
        await guild.leave()
        logger.info("不正ギルドから離脱完了: %s (%s)", guild.name, guild.id)
    except Exception as e:
        logger.error("不正ギルド離脱失敗: %s", e)

async def send_system_warning_dms():
    targets = [config.TARGET_USER_WARN_ID, config.ADMIN_USER_ID]
    for uid in targets:
        if not uid:
            continue
        warn_key = f"official_warned_{uid}"
        is_warned = await asyncio.to_thread(database.get_config, warn_key)
        if is_warned:
            continue

        try:
            user = bot.get_user(uid) or await bot.fetch_user(uid)
            if user:
                msg = TARGET_USER_WARNING_DM.format(user_id=uid)
                await user.send(msg)
                await asyncio.to_thread(database.set_config, warn_key, "1")
                logger.info("対象ユーザー(%s)へ公式警告DMを送信完了", uid)
        except Exception as e:
            logger.warning("対象ユーザー(%s)への警告DM送信に失敗: %s", uid, e)

async def delete_old_warning_dm():
    targets = [config.TARGET_USER_WARN_ID, config.ADMIN_USER_ID]
    for uid in targets:
        if not uid:
            continue
        try:
            user = bot.get_user(uid) or await bot.fetch_user(uid)
            if not user:
                continue
            dm = user.dm_channel or await user.create_dm()
            async for msg in dm.history(limit=30):
                if msg.author.id == bot.user.id:
                    if any(k in msg.content for k in ["反革命", "写真から消去", "最高指導部", "🚨", "重点監視対象"]):
                        try:
                            await msg.delete()
                            logger.info("旧警告DMを削除: %s", msg.id)
                        except Exception as e:
                            logger.warning("旧警告DMの削除失敗: %s", e)
        except Exception as e:
            logger.warning("旧DM履歴の取得失敗(%s): %s", uid, e)

@bot.event
async def on_guild_join(guild: discord.Guild):
    await enforce_guild_restriction(guild)

@bot.event
async def on_ready():
    logger.info("システム稼働。共産趣味ボット統制下オンライン。(%s)", bot.user)
    for guild in list(bot.guilds):
        await enforce_guild_restriction(guild)
    bot.loop.create_task(delete_old_warning_dm())
    bot.loop.create_task(send_system_warning_dms())

if __name__ == "__main__":
    if not config.TOKEN:
        logger.error("DISCORD_TOKEN が設定されていません。.env または環境変数を確認してください。")
    else:
        bot.run(config.TOKEN)
