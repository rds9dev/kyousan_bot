import asyncio
import sys
import discord
import config

TARGET_USER_ID = config.TARGET_USER_WARN_ID

async def main():
    if not config.TOKEN:
        print("エラー: DISCORD_TOKEN が設定されていません。")
        sys.exit(1)

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        try:
            user = client.get_user(TARGET_USER_ID) or await client.fetch_user(TARGET_USER_ID)
            dm = user.dm_channel or await user.create_dm()
            deleted = 0
            async for msg in dm.history(limit=50):
                if msg.author.id == client.user.id:
                    if any(k in msg.content for k in ["反革命", "写真から消去", "最高指導部", "🚨"]):
                        await msg.delete()
                        print(f"削除完了: {msg.id}")
                        deleted += 1
            print(f"完了: 計 {deleted} 件の旧DMを削除しました。")
        except Exception as e:
            print(f"エラー: {e}")
        finally:
            await client.close()

    await client.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
