import asyncio
import os
import sys
import discord
from dotenv import load_dotenv

import config
import database

TARGET_USER_ID = config.TARGET_USER_WARN_ID

WARNING_TEXT = (
    f"【通告: 対象識別番号 {TARGET_USER_ID}】\n"
    "貴殿のアカウントは統制局による重点監視対象に指定されています。\n"
    "これまでの不正操作および規律違反の全ログは保全済みです。\n"
    "本通告は一度限りであり、以降の不審な挙動は一切の猶予なく即時排他処理されます。\n"
    "直ちにすべての不当な介入を停止してください。"
)

async def main():
    if not config.TOKEN:
        print("エラー: DISCORD_TOKEN が設定されていません。")
        sys.exit(1)

    database.init_db()
    warn_key = f"warned_user_{TARGET_USER_ID}"
    is_warned = database.get_config(warn_key)
    if is_warned:
        print(f"ユーザー {TARGET_USER_ID} には既に警告DMを送信済みです。(key: {warn_key})")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        try:
            user = client.get_user(TARGET_USER_ID) or await client.fetch_user(TARGET_USER_ID)
            if user:
                await user.send(WARNING_TEXT)
                database.set_config(warn_key, "1")
                print(f"成功: ユーザー {TARGET_USER_ID} ({user}) へ警告DMを送信しました。")
            else:
                print(f"エラー: ユーザー {TARGET_USER_ID} が見つかりませんでした。")
        except Exception as e:
            print(f"警告DM送信中にエラーが発生しました: {e}")
        finally:
            await client.close()

    await client.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
