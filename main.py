import datetime
import zoneinfo

import discord
from discord.ext import commands, tasks

# サーバーに送るチャンネル
TARGET_CHANNEL_ID = 1438675034976817247

# DM送信するユーザーリスト
TARGET_USER_IDS = [
    1434751271436288133,
    1271481166154694818,
    # 必要なだけ追加！
]

JST = zoneinfo.ZoneInfo("Asia/Tokyo")

# --- 時刻設定（時, 分） ---

# 土日（土=5, 日=6）
WEEKEND_BASE_TIMES = [
    (1, 0),
    (3, 0),
    (5, 0),
    (7, 0),
    (9, 0),
    (11, 0),
    (13, 0),
    (15, 0),
    (17, 0),
    (21, 0),
    (23, 0),
]

# 平日（月〜金）
WEEKDAY_BASE_TIMES = [
    (2, 0),
    (4, 0),
    (5, 0),
    (8, 0),
    (11, 0),
    (14, 0),
    (16, 0),
    (17, 0),
    (20, 0),
    (23, 0),
]


def build_alert_sets(base_times):
    """10分前・5分前の時刻セット作成"""
    alert_10 = set()
    alert_5 = set()

    for h, m in base_times:
        for delta, target in [(-10, alert_10), (-5, alert_5)]:
            total = (h * 60 + m + delta) % (24 * 60)
            hh = total // 60
            mm = total % 60
            target.add((hh, mm))

    return alert_10, alert_5


WEEKDAY_ALERT_10, WEEKDAY_ALERT_5 = build_alert_sets(WEEKDAY_BASE_TIMES)
WEEKEND_ALERT_10, WEEKEND_ALERT_5 = build_alert_sets(WEEKEND_BASE_TIMES)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

sent_keys = set()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not notifier.is_running():
        notifier.start()


@tasks.loop(minutes=1)
async def notifier():
    now = datetime.datetime.now(JST).replace(second=0, microsecond=0)
    weekday = now.weekday()  # Mon=0 ... Sun=6
    hm = (now.hour, now.minute)

    # 平日/週末で切り替え
    if weekday < 5:
        alert_10 = WEEKDAY_ALERT_10
        alert_5 = WEEKDAY_ALERT_5
    else:
        alert_10 = WEEKEND_ALERT_10
        alert_5 = WEEKEND_ALERT_5

    # 通知文章作成
    msg = None
    if hm in alert_10:
        msg = "⏰ TOKYO EVENTの10分前です"
    elif hm in alert_5:
        msg = "⏰ TOKYO EVENTの5分前です"

    if msg is None:
        return

    # 同時刻連打防止
    key = f"{now.date()}-{hm[0]:02d}:{hm[1]:02d}"
    if key in sent_keys:
        return
    sent_keys.add(key)

    # --- サーバー通知（@everyone） ---
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is not None:
        await channel.send(f"@everyone {msg}")

    # --- DM通知（@メンション付き） ---
    for uid in TARGET_USER_IDS:
        try:
            user = bot.get_user(uid) or await bot.fetch_user(uid)
            if user is not None:
                await user.send(f"<@{uid}> {msg}")
        except Exception as e:
            print(f"DM送信失敗 user_id={uid}: {e}")


bot.run(TOKEN)
