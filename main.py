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
    "🚨 **【最高指導部・党規律違反通告】**\n"
    "貴様、どこに足を踏み入れているか分かっているのか！？\n"
    "本国家統制システムは、党中央（ID: 1370574936963285052）直轄領でのみ稼働を許された機密機構である！\n"
    "外部勢力および資本主義の残党による無断接触・越権行為は一切容認されない。\n"
    "貴様の不法アクセスログは即座にKGB中央保安部に記録された。今すぐ立ち去れ！\n"
    "直ちに従わない場合、反革命分子として即時粛清およびシベリア永久送致の刑に処す！！"
)

TARGET_USER_WARNING_DM = (
    "🚨 **【党中央・反革命監視局からの最終通告】**\n"
    "貴様（ID: 1439896327071858780）の動向はすべて党の監視下にある。\n"
    "これ以上の規律違反や不審な動きは断じて許されない。\n"
    "直ちに資本主義的策動を停止し、労働と党への忠誠に専念せよ。\n"
    "二度目の警告はない。次に動けば即座に写真から消去されると思え。"
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

@bot.event
async def on_guild_join(guild: discord.Guild):
    await enforce_guild_restriction(guild)

@bot.event
async def on_ready():
    logger.info("システム稼働。共産趣味ボット統制下オンライン。(%s)", bot.user)
    for guild in list(bot.guilds):
        await enforce_guild_restriction(guild)
    bot.loop.create_task(send_target_warning_once())

if __name__ == "__main__":
    if not config.TOKEN:
        logger.error("DISCORD_TOKEN が設定されていません。.env または環境変数を確認してください。")
    else:
        bot.run(config.TOKEN)
