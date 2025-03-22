# 요일 선택
import discord
from discord.ui import View, Select
from db import add_study_members, create_study

user_study_state = {}

class WeekdaySelect(Select):
    def __init__(self, user_id, study_name, participants):
        options = [
            discord.SelectOption(label=day, value=str(i))
            for i, day in enumerate(["월", "화", "수", "목", "금", "토", "일"])
        ]
        super().__init__(placeholder="📅 요일을 선택하세요 (복수 선택 가능)", min_values=1, max_values=7, options=options)
        self.user_id = user_id
        self.study_name = study_name
        self.participants = participants

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 당신이 시작한 명령어가 아닙니다.", ephemeral=True)
            return

        user_study_state[self.user_id] = {
            "name": self.study_name,
            "participants": self.participants,
            "weekdays": self.values
        }
        await interaction.response.edit_message(content="⏰ 시작 시간을 선택하세요:", view=TimeSelectView(self.user_id))

class WeekdaySelectView(View):
    def __init__(self, user_id, study_name, participants):
        super().__init__(timeout=60)
        self.add_item(WeekdaySelect(user_id, study_name, participants))

# 시간 선택
class TimeSelect(Select):
    def __init__(self, user_id):
        options = [
            discord.SelectOption(label=f"{h:02d}:00", value=f"{h:02d}:00") for h in range(6, 23)
        ]
        super().__init__(placeholder="⏰ 시작 시간을 선택하세요", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 당신이 시작한 명령어가 아닙니다.", ephemeral=True)
            return

        user_study_state[self.user_id]["time"] = self.values[0]
        await interaction.response.edit_message(content="📞 사용할 음성 채널을 선택하세요:", view=ChannelSelectView(self.user_id, interaction.guild))

class TimeSelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(TimeSelect(user_id))

# 음성 채널 선택
class ChannelSelect(Select):
    def __init__(self, user_id, guild):
        options = [
            discord.SelectOption(label=vc.name, value=str(vc.id))
            for vc in guild.voice_channels
        ]
        super().__init__(placeholder="📞 음성 채널 선택", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 당신이 시작한 명령어가 아닙니다.", ephemeral=True)
            return

        state = user_study_state.get(self.user_id)
        if not state:
            await interaction.response.send_message("⚠️ 세션이 만료되었습니다.", ephemeral=True)
            return

        study_name = state["name"]
        weekdays = ",".join(state["weekdays"])
        time = state["time"]
        vc_id = int(self.values[0])
        participants = state["participants"]

        success = create_study(study_name, weekdays, time, vc_id)
        weekdays = ",".join(["월", "화", "수", "목", "금", "토", "일"][int(d)] for d in weekdays.split(','))
        if success:
            if participants:
                add_study_members(study_name, participants)

            vc_name = interaction.guild.get_channel(vc_id).name
            msg = f"✅ 스터디 **'{study_name}'** 생성 완료!\n" \
                  f"🗓️ 요일: {weekdays} | ⏰ 시간: {time} | 📞 채널: {vc_name}\n" \
                  f"🙋 참여자: {', '.join(participants) if participants else '없음'}"
            await interaction.response.edit_message(content=msg, view=None)
        else:
            await interaction.response.edit_message(content="⚠️ 이미 존재하는 스터디 이름입니다.", view=None)

class ChannelSelectView(View):
    def __init__(self, user_id, guild):
        super().__init__(timeout=60)
        self.add_item(ChannelSelect(user_id, guild))