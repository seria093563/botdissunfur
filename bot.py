import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio
import json
import discord.ui as ui

class MyClass:
    pass 
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.presences = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ บอททำงานในชื่อ {bot.user}")
    activity = discord.Streaming(
        name="Youtube",
        url="https://youtu.be/fLexgOxsZu0?si=FDsmMCgM367IY6c0"
    )
    await bot.change_presence(status=discord.Status.online, activity=acacacaclogggiin)

@bot.tree.command(name="join", description="ให้บอทเข้าห้องเสียงเดียวกับคุณ")
async def join(interaction: discord.Interaction):
    voice_state = interaction.user.voice

    if not voice_state or not voice_state.channel:
        await interaction.response.send_message(
            "❌ คุณต้องอยู่ในห้องเสียงก่อนถึงจะใช้คำสั่งนี้ได้",
            ephemeral=True
        )
        return

    channel = voice_state.channel

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()

    await channel.connect()
    await interaction.response.send_message(
        f"✅ เข้าห้องเสียง `{channel.name}` เรียบร้อยแล้ว",
        ephemeral=True
    )

@bot.tree.command(name="leave", description="ให้บอทออกจากห้องเสียง")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message(
            "👋 บอทออกจากห้องเสียงแล้ว",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ บอทยังไม่ได้อยู่ในห้องเสียง",
            ephemeral=True
        )


voice_data = {}

DATA_FILE = "voice_data.json"
CATEGORY_NAME = "🔒・｡ﾟ ห้องส่วนตัว"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(voice_data, f)

@bot.event
async def on_ready():
    global voice_data
    voice_data = load_data()
    await bot.tree.sync()

@bot.tree.command(name="setuproom", description="Setup ระบบห้องเสียง")
async def setuproom(interaction: discord.Interaction):
    embed = discord.Embed(
        title="\U0001f5e1️ ระบบห้องเสียงส่วนตัว",
        description=(
            "\U0001f464 สร้างห้องที่คุณเข้าได้คนเดียว\n"
            "➕ เพิ่มสมาชิกเข้าได้ตามต้องการ\n"
            "⌛ ห้องจะลบอัตโนมัติหากไม่มีใครอยู่นาน 20 วินาที"
        ),
        color=discord.Color.purple()
    )
    view = RoomSetupView()
    await interaction.response.send_message(embed=embed, view=view)

class RoomSetupView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="\U0001f4c0 สร้างห้อง", style=discord.ButtonStyle.success)
    async def create_room(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if not category:
            category = await guild.create_category(CATEGORY_NAME)

        user_id = str(user.id)
        data = voice_data.get(user_id, {})

        if "channel_id" in data:
            existing_channel = guild.get_channel(data["channel_id"])
            if existing_channel:
                await interaction.response.send_message(f"คุณมีห้องอยู่แล้ว: {existing_channel.mention}", ephemeral=True)
                return

        members = data.get("members", [user.id])
        name = data.get("name", f"\U0001f512 ห้องของ {user.display_name}")
        user_limit = data.get("limit", 0)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            user: discord.PermissionOverwrite(connect=True, manage_channels=True),
        }
        for m_id in members:
            member = guild.get_member(m_id)
            if member:
                overwrites[member] = discord.PermissionOverwrite(connect=True)

        channel = await guild.create_voice_channel(name=name, category=category, overwrites=overwrites, user_limit=user_limit)

        voice_data[user_id] = {
            "channel_id": channel.id,
            "name": name,
            "limit": user_limit,
            "members": members,
            "owner": user.id
        }
        save_data()

        await interaction.response.send_message(f"✅ สร้างห้องแล้ว: {channel.mention}", ephemeral=True)

        def check(m, b, a):
            return m.id == user.id and a.channel == channel

        try:
            await bot.wait_for("voice_state_update", check=check, timeout=60)
        except asyncio.TimeoutError:
            if guild.get_channel(channel.id):
                await channel.delete()
            voice_data[user_id]["channel_id"] = None
            save_data()

    @ui.button(label="📝 เปลี่ยนชื่อห้อง", style=discord.ButtonStyle.primary)
    async def rename_room(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ChangeRoomNameModal())

    @ui.button(label="\U0001f46b ตั้งจำนวนคน", style=discord.ButtonStyle.primary)
    async def set_user_limit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(UserLimitModal())

    @ui.button(label="➕ เพิ่มสมาชิก", style=discord.ButtonStyle.secondary)
    async def add_members(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddMemberModal())

    @ui.button(label="❌ ลบสมาชิก", style=discord.ButtonStyle.danger)
    async def remove_members(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RemoveMemberModal())

class ChangeRoomNameModal(ui.Modal, title="เปลี่ยนชื่อห้อง"):
    name = ui.TextInput(label="ชื่อใหม่", placeholder="ห้อง VIP ของฉัน")

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in voice_data:
            return await interaction.response.send_message("คุณยังไม่มีห้อง", ephemeral=True)

        channel = interaction.guild.get_channel(voice_data[user_id]["channel_id"])
        if channel:
            await channel.edit(name=self.name.value)
            voice_data[user_id]["name"] = self.name.value
            save_data()
            await interaction.response.send_message(f"✅ เปลี่ยนชื่อห้องเป็น `{self.name.value}`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ไม่พบห้องของคุณ", ephemeral=True)

class UserLimitModal(ui.Modal, title="ตั้งจำนวนคนสูงสุด"):
    limit = ui.TextInput(label="จำนวน", placeholder="1-99", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in voice_data:
            return await interaction.response.send_message("คุณยังไม่มีห้อง", ephemeral=True)

        try:
            limit = int(self.limit.value)
            channel = interaction.guild.get_channel(voice_data[user_id]["channel_id"])
            if channel:
                await channel.edit(user_limit=limit)
                voice_data[user_id]["limit"] = limit
                save_data()
                await interaction.response.send_message(f"✅ จำกัดคนเข้า {limit} คน", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบห้องของคุณ", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ต้องเป็นตัวเลข", ephemeral=True)

class AddMemberModal(ui.Modal, title="เพิ่มสมาชิก"):
    user_input = ui.TextInput(label="ใส่ ID สมาชิกเท่านั้น", placeholder="123456789")

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in voice_data:
            return await interaction.response.send_message("คุณยังไม่มีห้อง", ephemeral=True)

        try:
            target_id = int(self.user_input.value)
            member = interaction.guild.get_member(target_id)
            if not member:
                return await interaction.response.send_message("❌ ไม่พบผู้ใช้", ephemeral=True)

            channel = interaction.guild.get_channel(voice_data[user_id]["channel_id"])
            if channel:
                await channel.set_permissions(member, connect=True)
            if target_id not in voice_data[user_id]["members"]:
                voice_data[user_id]["members"].append(target_id)
            save_data()
            await interaction.response.send_message(f"✅ เพิ่ม {member.mention} เข้าใช้งานห้องแล้ว", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ID ไม่ถูกต้อง", ephemeral=True)

class RemoveMemberModal(ui.Modal, title="ลบสมาชิก"):
    user_input = ui.TextInput(label="ใส่ ID สมาชิกที่ต้องการลบ", placeholder="123456789")

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in voice_data:
            return await interaction.response.send_message("คุณยังไม่มีห้อง", ephemeral=True)

        try:
            target_id = int(self.user_input.value)
            member = interaction.guild.get_member(target_id)
            if not member:
                return await interaction.response.send_message("❌ ไม่พบผู้ใช้", ephemeral=True)

            if target_id in voice_data[user_id]["members"]:
                voice_data[user_id]["members"].remove(target_id)
                channel = interaction.guild.get_channel(voice_data[user_id]["channel_id"])
                if channel:
                    await channel.set_permissions(member, overwrite=None)
                save_data()
                await interaction.response.send_message(f"✅ ลบ {member.mention} จากห้องแล้ว", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ผู้ใช้นี้ไม่ได้อยู่ในห้องของคุณ", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ID ไม่ถูกต้อง", ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    if not before.channel:
        return
    for user_id, data in list(voice_data.items()):
        ch = member.guild.get_channel(data.get("channel_id"))
        if ch and ch.id == before.channel.id:
            await asyncio.sleep(20)
            if ch and len(ch.members) == 0:
                try:
                    await ch.delete()
                except discord.NotFound:
                    pass
                voice_data[user_id]["channel_id"] = None
                save_data()      
                
RADIO_URL = "http://streaming.tdiradio.com:8000/house.mp3"
@bot.tree.command(name="joinradio", description="📻 ให้บอทเข้าห้องเสียงและเล่นวิทยุ")
async def joinradio(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message("❌ คุณต้องอยู่ในห้องเสียงก่อน", ephemeral=True)

    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()

    vc = await channel.connect()

    source = await discord.FFmpegOpusAudio.from_probe(RADIO_URL)
    vc.play(source)
    await interaction.response.send_message(f"📻 กำลังเล่นวิทยุใน `{channel.name}`", ephemeral=True)

@bot.tree.command(name="leaveradio", description="🛑 ให้บอทออกจากห้องเสียง")
async def leaveradio(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("👋 บอทออกจากห้องเสียงแล้ว", ephemeral=True)
    else:
        await interaction.response.send_message("❌ บอทยังไม่ได้อยู่ในห้องเสียง", ephemeral=True)
        
bot.run(os.environ["TOKEN"])
      
