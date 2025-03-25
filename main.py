import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import datetime
from pytz import timezone

from db import (
    add_study_members,
    delete_study,
    get_all_studies,
    get_attendance_by_date,
    get_study_info,
    get_study_members,
    init_db,
    get_study_by_voice_channel_id,
    has_already_checked_in,
    record_attendance,
)
from ui import WeekdaySelectView

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True  # 슬래시 명령어 대신 prefix 명령어 쓸 때 필요

bot = commands.Bot(command_prefix='/', intents=intents)

init_db()

@bot.command(name="스터디")
async def show_help(ctx):
    embed = discord.Embed(
        title="📘 스터디 관리 봇 명령어 모음",
        description="스터디 생성부터 출석까지! 아래 명령어들을 참고하세요.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="/스터디생성 [이름] @참여자들",
        value=(
            "새로운 스터디를 생성하고 참여자도 함께 등록합니다.\n"
        ),
        inline=True
    )

    embed.add_field(
        name="/스터디참가 [스터디명] @참여자들",
        value=(
            "기존 스터디에 멘션한 유저들을 참여자로 추가합니다.\n"
        ),
        inline=True
    )

    embed.add_field(
        name="/스터디목록",
        value="현재 등록된 모든 스터디 목록을 보여줍니다.\n",
        inline=True
    )

    embed.add_field(
        name="/스터디삭제 [스터디명]",
        value="해당 이름의 스터디를 삭제합니다. 출석기록, 참여자도 함께 삭제됩니다.\n",
        inline=True
    )

    embed.add_field(
        name="/출석현황 [스터디명]",
        value=(
            "해당 스터디의 날짜별 출석 현황을 확인할 수 있습니다.\n"
        ),
        inline=True
    )

    embed.add_field(
        name="/스터디",
        value="이 도움말을 출력합니다.",
        inline=True
    )

    embed.set_footer(text="💡 음성 채널 입장 시 자동으로 출석이 기록되며, 출석 알림은 #출석체크 채널로 전송됩니다.")

    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument) and ctx.command.name == "스터디생성":
        usage = "📌 사용법: `/스터디생성 [이름] [요일] [시간] [채널이름]`\n" \
                "예: `/스터디생성 알고리즘스터디 월,수,금 08:00 스터디채널`"
        await ctx.send(f"⚠️ 인자가 부족합니다.\n{usage}")

# 🏗️ 스터디 생성 명령어
@bot.command(name="스터디생성")
async def create_study_command(ctx, 이름: str, *참여자: discord.Member):
    user_id = ctx.author.id
    participant_names = [m.name for m in 참여자]
    await ctx.send("📅 스터디 요일을 선택해주세요:", view=WeekdaySelectView(user_id, 이름, participant_names))

@bot.command(name="스터디참가")
async def add_members_to_study(ctx, 스터디명: str, *유저들: discord.Member):
    if not 유저들:
        await ctx.send("⚠️ 추가할 유저를 멘션해주세요. 예: `/스터디참가 알고리즘스터디 @user1 @user2`")
        return

    user_names = [m.name for m in 유저들]
    added_users = add_study_members(스터디명, user_names)

    if not added_users:
        await ctx.send(f"ℹ️ 이미 등록된 유저입니다. 아무도 추가되지 않았어요.")
    else:
        await ctx.send(f"✅ **{스터디명}**에 다음 유저들이 추가되었습니다: {', '.join(added_users)}")

@bot.command(name="스터디목록")
async def show_study_list(ctx):
    studies = get_all_studies()
    if not studies:
        await ctx.send("📭 등록된 스터디가 없습니다.")
        return

    msg = "📚 현재 등록된 스터디 목록:\n"
    for s in studies:
        weekday_str = ",".join(["월", "화", "수", "목", "금", "토", "일"][int(d)] for d in s["weekdays"].split(','))
        participants = ", ".join(s["participants"]) if s["participants"] else "없음"
        msg += (
            f"\n• **{s['name']}**\n"
            f"   🗓️ 요일: {weekday_str} | ⏰ 시간: {s['time']}\n"
            f"   🙋 참여자: {participants}\n"
        )

    await ctx.send(msg[:2000])  # 메시지 제한 고려

@bot.command(name="스터디삭제")
async def delete_study_command(ctx, 스터디명: str = None):
    if not 스터디명:
        await ctx.send("❌ 삭제할 스터디명을 입력해주세요.")
        return

    delete_study(스터디명)
    await ctx.send(f"🗑️ 스터디 **{스터디명}**가 삭제되었습니다.")

# 출석 현황 보기
@bot.command()
async def 출석현황(ctx, 스터디명: str = None):
    if not 스터디명:
        await ctx.send("❌ 스터디명을 입력해주세요.")
        return

    attendance_data = get_attendance_by_date(스터디명)
    members = get_study_members(스터디명)

    if not attendance_data:
        await ctx.send(f"'{스터디명}'의 출석 기록이 없습니다.")
        return

    msg = f"📋 **{스터디명} 출석 현황:**\n"
    for date, records in attendance_data.items():
        msg += f"\n🗓️ {date}:\n"
        for member in members:
            if member in records:
                rec = records[member]
                msg += f"  - {member} ({rec['time']}, {rec['status']})\n"
            else:
                msg += f"  - {member} (❌ 결석)\n"

    await ctx.send(msg[:2000])


# 🎙️ 음성채널 입장 시 출석 자동 기록
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is None:
        return

    now = datetime.datetime.now(timezone('Asia/Seoul'))
    today = now.strftime('%Y-%m-%d')
    now_time = now.strftime('%H:%M')
    weekday_today = now.weekday()
    study_names = get_study_by_voice_channel_id(after.channel.id)

    for study_name in study_names:
        study_info = get_study_info(study_name)
        if not study_info:
            continue

        if weekday_today not in study_info["weekdays"]:
            continue

        # 기준 시간 설정
        try:
            start_hour, start_minute = map(int, study_info["time"].split(":"))
            seoul_tz = timezone('Asia/Seoul')
            study_start_naive = datetime.datetime.combine(now.date(), datetime.time(start_hour, start_minute))
            study_start = seoul_tz.localize(study_start_naive)  # 이 부분이 핵심!

        except:
            continue

        delta = (now - study_start).total_seconds()

        # 다른 스터디원에게 DM으로 출석 여부 알림
        study_members = get_study_members(study_name)

        for study_member in study_members:
            if study_member == member.name or has_already_checked_in(study_name, study_member, today):
                continue

            study_member_obj = discord.utils.get(member.guild.members, name=study_member)
            if study_member_obj:
                await study_member_obj.send(f"📢 {member.name}이 왔는데 넌 모함?")
        

        if delta < -3600:  # 1시간 전부터 출석
            status = "출석"
        elif 0 < delta <= 1800:  # 30분
            status = "지각"
        else:
            status = "결석"  # 하지만 실제론 기록 X
            print(f"{member.name} - {study_name}: {status} 처리 안됨 (시간 초과)")
            continue

        if not has_already_checked_in(study_name, member.name, today):
            record_attendance(study_name, member.name, today, now_time, status)
            print(f"{member.name} {status} 처리됨: {study_name} @ {now_time}")

            text_channel = discord.utils.get(member.guild.text_channels, name="출석체크")
            if text_channel:
                await text_channel.send(f"✅ {member.name}님이 **{study_name}** {status}했습니다! ({now_time})")

        

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인: {bot.user.name}")



bot.run(BOT_TOKEN)
