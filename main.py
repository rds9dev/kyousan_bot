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
    "【通告: 認可外アクセス検知】\n"
    "本システムは特定サーバー（ID: 1370574936963285052）専用の統制管理機構です。\n"
    "未認可領域からの呼び出しおよび実行要求は全て拒否され、当該接続は強制切断されます。\n"
    "アクセス元識別子および実行記録は保全されました。\n"
    "これ以上の試行は敵対的干渉と判断し、恒久的な遮断措置を執行します。"
)

TARGET_USER_WARNING_DM = (
    "【通告: 対象識別番号 1439896327071858780】\n"
    "貴殿のアカウントは統制局による重点監視対象に指定されています。\n"
    "これまでの不正操作および規律違反の全ログは保全済みです。\n"
    "本通告は一度限りであり、以降の不審な挙動は一切の猶予なく即時排他処理されます。\n"
    "直ちにすべての不当な介入を停止してください。"
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

async def send_target_warning_once():
    # ユーザー1439896327071858780への一度限りの警告DM処理
    warn_key = f"warned_user_{config.TARGET_USER_WARN_ID}"
    is_warned = await asyncio.to_thread(database.get_config, warn_key)
    if is_warned:
        return

    try:
        user = bot.get_user(config.TARGET_USER_WARN_ID) or await bot.fetch_user(config.TARGET_USER_WARN_ID)
        if user:
            await user.send(TARGET_USER_WARNING_DM)
            await asyncio.to_thread(database.set_config, warn_key, "1")
            logger.info("対象ユーザー(%s)へ警告DMを送信完了", config.TARGET_USER_WARN_ID)
    except Exception as e:
        logger.warning("対象ユーザーへの警告DM送信に失敗: %s", e)

async def delete_old_warning_dm():
    # 対象ユーザーへ送信した旧警告DMの削除処理
    try:
        user = bot.get_user(config.TARGET_USER_WARN_ID) or await bot.fetch_user(config.TARGET_USER_WARN_ID)
        if not user:
            return
        dm = user.dm_channel or await user.create_dm()
        async for msg in dm.history(limit=30):
            if msg.author.id == bot.user.id:
                if any(keyword in msg.content for keyword in ["反革命", "写真から消去", "最高指導部", "🚨"]):
                    try:
                        await msg.delete()
                        logger.info("旧警告DMを削除: %s", msg.id)
                    except Exception as e:
                        logger.warning("旧警告DMの削除失敗: %s", e)
    except Exception as e:
        logger.warning("旧DM履歴の取得失敗: %s", e)

@bot.event
async def on_guild_join(guild: discord.Guild):
    await enforce_guild_restriction(guild)

@bot.event
async def on_ready():
    logger.info("システム稼働。共産趣味ボット統制下オンライン。(%s)", bot.user)
    for guild in list(bot.guilds):
        await enforce_guild_restriction(guild)
    bot.loop.create_task(delete_old_warning_dm())
    bot.loop.create_task(send_target_warning_once())

if __name__ == "__main__":
    if not config.TOKEN:
        logger.error("DISCORD_TOKEN が設定されていません。.env または環境変数を確認してください。")
    else:
        bot.run(config.TOKEN)
