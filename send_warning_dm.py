import asyncio
import os
import sys
import discord
from dotenv import load_dotenv

import config
import database

WARNING_TEXT_TEMPLATE = (
    "**【Discord System Notice】**\n"
    "アカウント通知: 違反警告\n\n"
    "対象アカウント識別子: `{user_id}`\n\n"
    "システム監視プロトコルにより、貴殿のアカウントから利用規約およびガイドラインに抵触する不正なアクセス・操作試行が検知されました。\n\n"
    "■ **措置内容**\n"
    "本通知は重大な規律違反に対する一度限りの公式システム警告です。直ちに該当するすべての不正操作・通信を停止してください。\n\n"
    "■ **今後の対応について**\n"
    "本通知以降も同様の不審な挙動または不正アクセスが確認された場合、事前の通告なくアカウントのアクセス遮断および関連サーバーからの恒久的な利用停止措置が執行されます。"
)

async def main():
    if not config.TOKEN:
        print("エラー: DISCORD_TOKEN が設定されていません。")
        sys.exit(1)

    database.init_db()
    targets = [config.TARGET_USER_WARN_ID, config.ADMIN_USER_ID]

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        for uid in targets:
            if not uid:
                continue
            warn_key = f"official_warned_{uid}"
            is_warned = database.get_config(warn_key)
            if is_warned:
                print(f"ユーザー {uid} には既に公式警告DMを送信済みです。(key: {warn_key})")
                continue

            try:
                user = client.get_user(uid) or await client.fetch_user(uid)
                if user:
                    msg = WARNING_TEXT_TEMPLATE.format(user_id=uid)
                    await user.send(msg)
                    database.set_config(warn_key, "1")
                    print(f"成功: ユーザー {uid} ({user}) へ公式警告DMを送信しました。")
                else:
                    print(f"エラー: ユーザー {uid} が見つかりませんでした。")
            except Exception as e:
                print(f"警告DM送信エラー ({uid}): {e}")
        await client.close()

    await client.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
