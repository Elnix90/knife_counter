import io
import json
import discord
from datetime import datetime, timezone
from discord import ui
from save_data import save_data
from DATA.CONSTANTS import *
from init_logger import setup_logger

logger = setup_logger("knife_tracker")

try:
    from DATA.keys import BOT_TOKEN
except ModuleNotFoundError:
    logger.warning("Unable to load BOT_TOKEN")
    BOT_TOKEN = input("Please enter your bot token: ")

class KnifeButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Engrave", style=discord.ButtonStyle.primary)
    async def graved_button(self, interaction: discord.Interaction, button: ui.Button):
        await graved(interaction)

    @ui.button(label="Found", style=discord.ButtonStyle.success)
    async def found_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FoundKnifeModal())

    @ui.button(label="Cancel last action", style=discord.ButtonStyle.danger)
    async def undo_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.guild_permissions.administrator:
            await undo_last_action(interaction)
        else:
            await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)

class FoundKnifeModal(ui.Modal, title="Find a knife"):
    knife_number = ui.TextInput(label="Knife number", placeholder="Enter the knife's found number:")

    async def on_submit(self, interaction: discord.Interaction):
        number = self.knife_number.value
        await found(interaction, number)

async def setup_interaction_message():
    channel = bot.get_channel(BUTTONS_CHANNEL_ID)
    if not channel:
        category = bot.get_channel(COMMANDS_CATEGORY_ID)
        if not category:
            logger.error("No category")
            return
        channel = await category.create_text_channel('ɪɴᴛᴇʀᴀᴄᴛɪᴏɴꜱ')

    messages = [message async for message in channel.history(limit=1)]
    embed = discord.Embed(title="Instructions for engraving and finding knives", color=discord.Color.blue())
    embed.add_field(name="Engraving a knife", value="Make sure to send the command BEFORE engraving the knife. Click the 'Engrave' button below.", inline=False)
    embed.add_field(name="Finding a knife", value="If you find a knife, click the 'Found' button below and enter the number of the knife found.", inline=False)

    if messages:
        await messages[0].edit(embed=embed, view=KnifeButtons())
    else:
        await channel.send(embed=embed, view=KnifeButtons())

async def graved(interaction: discord.Interaction):
    global KNIFE_NUMBER
    global GRAVED_LOGS
    role_ids = [TRUSTED_GRAVERS_ID]
    
    if any(role.id in role_ids for role in interaction.user.roles):
        KNIFE_NUMBER += 1
        message_timestamp = interaction.created_at.isoformat()
        GRAVED_LOGS.append({
            "user_id": interaction.user.id,
            "knife_graved": KNIFE_NUMBER,
            "timestamp": message_timestamp
        })
        save_data(knives=KNIFE_NUMBER, graved=GRAVED_LOGS)
        
        graved_channel = bot.get_channel(GRAVED_CHANNEL_ID)
        await graved_channel.send(f"{interaction.user.mention} engraved knife number **{KNIFE_NUMBER}**!")
        await interaction.response.send_message(f"Successfully engraved knife **{KNIFE_NUMBER}**!", ephemeral=True)
        await backup()
    else:
        await interaction.response.send_message(f"You don't have permission to use this command. You can ask a <@&{TRUSTED_GRAVERS_ID}> if they can authorize you to engrave knives", ephemeral=True)

async def found(interaction: discord.Interaction, number):
    global KNIFE_NUMBER
    global FOUND_LOGS

    try:
        number = int(number)
    except Exception as e:
        logger.error(f"Invalid input: {number}; {e}")
        await interaction.response.send_message("Invalid input", ephemeral=True)
        return
    
    if (0 >= number) or (number > KNIFE_NUMBER):
        await interaction.response.send_message("Invalid knife number", ephemeral=True)
        return

    role_ids = [TRUSTED_GRAVERS_ID, TRUSTED_FOUNDER_ID]
    message_timestamp = interaction.created_at.isoformat()
    
    if any(role.id in role_ids for role in interaction.user.roles):
        FOUND_LOGS.append({
            "user_id": interaction.user.id,
            "knife_found": number,
            "timestamp": message_timestamp
        })
        save_data(found=FOUND_LOGS)
        
        found_channel = bot.get_channel(FOUND_CHANNEL_ID)
        await found_channel.send(f"{interaction.user.mention} found knife number **{number}**!")
        await interaction.response.send_message(f"Successfully found knife number **{number}**!", ephemeral=True)
        await backup()
    else:
        await interaction.response.send_message(f"You don't have permission to use this command. You can check with a <@&{TRUSTED_FOUNDER_ID}> if they can authorize you to find knives", ephemeral=True)


async def undo_last_action(interaction: discord.Interaction):
    global KNIFE_NUMBER, GRAVED_LOGS, FOUND_LOGS
    
    if GRAVED_LOGS and (not FOUND_LOGS or GRAVED_LOGS[-1]["timestamp"] > FOUND_LOGS[-1]["timestamp"]):
        last_action = GRAVED_LOGS.pop()
        KNIFE_NUMBER -= 1
        channel = bot.get_channel(GRAVED_CHANNEL_ID)
        action_type = "engraving"
    elif FOUND_LOGS:
        last_action = FOUND_LOGS.pop()
        channel = bot.get_channel(FOUND_CHANNEL_ID)
        action_type = "finding"
    else:
        await interaction.response.send_message("No action to undo.", ephemeral=True)
        return

    async for message in channel.history(limit=None):
        if str(last_action["knife_graved" if action_type == "engraving" else "knife_found"]) in message.content:
            await message.delete()
            break

    save_data(knives=KNIFE_NUMBER, graved=GRAVED_LOGS, found=FOUND_LOGS)
    await interaction.response.send_message(f"The last {action_type} action has been undone.", ephemeral=True)
    await backup()

@bot.event
async def on_ready():
    await setup_interaction_message()
    await bot.tree.sync()
    logger.info("Bot connected!")

async def backup():
    try:
        data = {
            "NUMBER": KNIFE_NUMBER,
            "GRAVED": GRAVED_LOGS,
            "FOUND": FOUND_LOGS
        }
        json_data = json.dumps(data, indent=4)
        file = discord.File(fp=io.StringIO(json_data), filename="data_backup.json")
        backup_channel = bot.get_channel(BACKUP_CHANNEL)
        if backup_channel is None:
            raise ValueError("Backup channel not found")
        message_timestamp = datetime.now(timezone.utc).isoformat()
        await backup_channel.send(f"Data backup from {message_timestamp}", file=file, silent=True)
        logger.info("Backup created and sent automatically")
    except Exception as e:
        logger.error(f"Unexpected error during backup attempt: {str(e)}")

bot.run(BOT_TOKEN)
