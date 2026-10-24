import asyncio
import os
import sys
import discord
from dotenv import load_dotenv

import config
import database

TARGET_USER_ID = config.TARGET_USER_WARN_ID

WARNING_TEXT = (
    "🚨 **【党中央・反革命監視局からの最終通告】**\n"
    f"貴様（ID: {TARGET_USER_ID}）の動向はすべて党の監視下にある。\n"
    "これ以上の規律違反や不審な動きは断じて許されない。\n"
    "直ちに資本主義的策動を停止し、労働と党への忠誠に専念せよ。\n"
    "二度目の警告はない。次に動けば即座に写真から消去されると思え。"
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
