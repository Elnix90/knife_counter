import io
import json
import discord
import re
from datetime import datetime, timezone
from discord.ext import commands
from discord import app_commands
from save_data import save_data
from DATA.CONSTANTS import *
from init_logger import setup_logger

logger = setup_logger("knife_tracker")

try:
    from DATA.keys import BOT_TOKEN
except ModuleNotFoundError:
    logger.warning("Unable to load BOT_TOKEN")


async def clean_invalid_messages():
    channels_to_check = [GRAVED_CHANNEL_ID, FOUND_CHANNEL_ID]
    for channel_id in channels_to_check:
        channel = bot.get_channel(channel_id)
        async for message in channel.history(limit=None):
            if message.author != bot.user:
                if not message.content.startswith("?") or not message.content[1:].split()[0] in bot.all_commands:
                    logger.info(f"Deleting invalid message in channel {message.channel.id}: {message.content}")
                    await message.delete()



async def process_offline_sent_commands():
    graved_channel = bot.get_channel(GRAVED_CHANNEL_ID)
    
    async for message in graved_channel.history(limit=None):
        if message.content.startswith("?graved"):
            ctx = await bot.get_context(message)
            logger.info(f"Processing: {ctx}")
            
            if bot.get_command('graved'):
                await bot.invoke(ctx)

    found_channel = bot.get_channel(FOUND_CHANNEL_ID)
    
    async for message in found_channel.history(limit=None):
        if message.content.startswith("?found"):
            parts = message.content.split()
            if len(parts) == 2 and parts[1].isdigit():
                ctx = await bot.get_context(message)

                if bot.get_command('found'):
                    await bot.invoke(ctx)
            else:
                logger.warning(f"Invalid message in channel {message.channel.id}: {message.content}")
                await message.delete()



@bot.event
async def on_ready():
    await clean_invalid_messages()
    await process_offline_sent_commands()
    await bot.tree.sync()
    logger.info("Bot connected!")




@bot.tree.command()
async def graved(interaction: discord.Interaction):
    """Announce that you graved a new knife. The number is automatically updated."""
    global KNIFE_NUMBER
    global GRAVED_LOGS
    
    role_ids = [TRUSTED_GRAVERS_ID]
    if interaction.channel.id == GRAVED_CHANNEL_ID:
        if any(role.id in role_ids for role in interaction.user.roles):
            logger.info(f"Current knife number: {KNIFE_NUMBER}")
            KNIFE_NUMBER += 1
            logger.info(f"1 knife added; current knife count: {KNIFE_NUMBER}")

            message_timestamp = interaction.created_at.isoformat()

            GRAVED_LOGS.append({
                "user_id": interaction.user.id,
                "knife_graved": KNIFE_NUMBER,
                "timestamp": message_timestamp
            })

            save_data(knives=KNIFE_NUMBER, graved=GRAVED_LOGS)

            logger.info("Command graved: data updated")
            await interaction.response.send_message(f"{interaction.user.mention} used `/graved` : knife number is now **{KNIFE_NUMBER}**!")
        
        else:
            logger.warning(f"User {interaction.user} doesn't have the required role to engrave a knife.")
            await interaction.response.send_message(f"**You don't have permission to use this command**\nI've sent a message to all members who have the permissions to warn them that you may have engraved a knife.\nPlease let them know if you have done anything, otherwise the count could be wrong.", ephemeral=True)
            await notify_admins(interaction.user, "graved",interaction.created_at.isoformat())
    else:
        logger.warning(f"User {interaction.user} doesn't send the command in the right channel")
        await interaction.response.send_message(f"You don't send your command in the right channel, the right channel is <#{GRAVED_CHANNEL_ID}>",ephemeral=True)


@bot.tree.command()
async def found(interaction: discord.Interaction, number: int):
    """Announce that you found a knife"""
    global KNIFE_NUMBER
    global FOUND_LOGS
    
    if (0 >= number) or (number > KNIFE_NUMBER):
        logger.warning(f"Number of knives found ({number}) is greater than the number of knives graved ({KNIFE_NUMBER}).")
        await interaction.response.send_message("Invalid knife number.", ephemeral=True)
        return

    role_ids = [TRUSTED_GRAVERS_ID, TRUSTED_FOUNDER_ID]
    message_timestamp = interaction.created_at.isoformat()

    if interaction.channel.id == FOUND_CHANNEL_ID:
        if any(role.id in role_ids for role in interaction.user.roles):
            FOUND_LOGS.append({
                "user_id": interaction.user.id,
                "knife_found":  number,
                "timestamp": message_timestamp})
            
            save_data(found=FOUND_LOGS)

            await interaction.response.send_message(f"{interaction.user.mention} used `/found` : knife number **{number}** found!")
            logger.info(f"User {interaction.user} found knife number {number}")

        else:
            logger.warning(f"User {interaction.user} doesn't have the required role to find a knife.")
            await interaction.response.send_message(f"**You don't have permission to use this command**\nI've sent a message to all members who have the permissions to warn them that you may have found a knife.\nPlease let them know if you have done anything, otherwise the count could be wrong.", ephemeral=True)
            await notify_admins(interaction.user, "found",interaction.created_at.isoformat())
    else:
        logger.warning(f"User {interaction.user} doesn't send the command in the right channel")
        await interaction.response.send_message(f"You don't send your command in the right channel, the right channel is <#{FOUND_CHANNEL_ID}>",ephemeral=True)
    await backup(interaction)

@bot.tree.command()
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int = None):
    """Clear messages in channel"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        if amount is None:
            deleted = await interaction.channel.purge()
        else:
            deleted = await interaction.channel.purge(limit=amount)
        
        logger.info(f"{len(deleted)} messages were deleted in '{interaction.channel.name}' ({interaction.channel.id})!")
        await interaction.followup.send(f"Cleared {len(deleted)} messages in {interaction.channel.mention}.", ephemeral=True)
    except discord.errors.Forbidden:
        await interaction.followup.send("You don't have permission to delete messages in this channel.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in clear command: {str(e)}")
        await interaction.followup.send("An error occurred while trying to clear messages.", ephemeral=True)
    await backup(interaction)


@bot.tree.command()
# @app_commands.checks.has_permissions(administrator=True)
async def backup(interaction: discord.Interaction):
    """Send a backup of the data.json file in the backup channel"""
    
    # if not interaction.user.guild_permissions.administrator:
    #     await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    #     logger.warning(f"User {interaction.user} attempted to use backup command without admin permissions")
    #     return

    await interaction.response.defer(ephemeral=True)

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
        
        await backup_channel.send("Data backup:", file=file)
        await interaction.followup.send("Backup successfully sent to the backup channel.", ephemeral=True)
        
        logger.info(f"Backup created and sent by {interaction.user}")
        
    except FileNotFoundError:
        await interaction.followup.send("Error: data.json file not found.", ephemeral=True)
        logger.error("data.json file not found during backup attempt")
    except ValueError as e:
        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
        logger.error(f"ValueError during backup attempt: {str(e)}")
    except Exception as e:
        await interaction.followup.send("An unexpected error occurred while creating the backup.", ephemeral=True)
        logger.error(f"Unexpected error during backup attempt: {str(e)}")


@bot.tree.command()
@app_commands.checks.has_permissions(administrator=True)
async def restore_backup(interaction: discord.Interaction):
    """Restore data from found and graved channels"""
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        logger.warning(f"User {interaction.user} attempted to use restore_backup command without admin permissions")
        return

    await interaction.response.defer(ephemeral=True)

    try:
        found_channel = interaction.guild.get_channel(1287810208646824057)
        graved_channel = interaction.guild.get_channel(1287736015963820113)

        if not found_channel or not graved_channel:
            raise ValueError("Found or graved channel not found")

        data = {
            "NUMBER": 0,
            "GRAVED": [],
            "FOUND": []
        }

        # Process found messages
        async for message in found_channel.history(limit=None):
            match = re.search(r'knife number (?:\*\*)?(\d+)(?:\*\*)? found', message.content)
            if match:
                knife_number = int(match.group(1))
                data["FOUND"].append({
                    "user_id": message.author.id,
                    "knife_found": knife_number,
                    "timestamp": message.created_at.isoformat()
                })
                data["NUMBER"] = max(data["NUMBER"], knife_number)

        # Process graved messages
        async for message in graved_channel.history(limit=None):
            match = re.search(r'knife number (?:is now |now )?\*\*(\d+)\*\*', message.content)
            if match:
                knife_number = int(match.group(1))
                data["GRAVED"].append({
                    "user_id": message.author.id,
                    "knife_graved": knife_number,
                    "timestamp": message.created_at.isoformat()
                })
                data["NUMBER"] = max(data["NUMBER"], knife_number)

        # Sort logs by timestamp
        data["FOUND"].sort(key=lambda x: x["timestamp"])
        data["GRAVED"].sort(key=lambda x: x["timestamp"])

        # Save to data.json
        with open(data_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Update global variables
        global KNIFE_NUMBER, GRAVED_LOGS, FOUND_LOGS
        KNIFE_NUMBER = data["NUMBER"]
        GRAVED_LOGS = data["GRAVED"]
        FOUND_LOGS = data["FOUND"]

        await interaction.followup.send("Backup successfully restored from channel messages.", ephemeral=True)
        logger.info(f"Backup restored by {interaction.user}")

    except ValueError as e:
        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
        logger.error(f"ValueError during restore attempt: {str(e)}")
    except Exception as e:
        await interaction.followup.send("An unexpected error occurred while restoring the backup.", ephemeral=True)
        logger.error(f"Unexpected error during restore attempt: {str(e)}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        logger.warning(f"Command not found: {ctx.message.content}")
    else:
        logger.error(f"Command error: {error}")
    
    await ctx.author.send("This bot now uses slash commands. Please use / to access the commands.")
    await ctx.message.delete()



async def notify_admins(user, command, timestamp):
    role_ids = [TRUSTED_GRAVERS_ID, TRUSTED_FOUNDER_ID]
    for guild in bot.guilds:
        for member in guild.members:
            if any(role.id in role_ids for role in member.roles):
                try:
                    await member.send(f"> At : **{timestamp}**\n> User : **{user.mention}**\n> Command: `/{command}`\nThe user don't have permission tu use the command. Please check with them if they actually {command} a knife.")
                except discord.errors.Forbidden:
                    logger.warning(f"Couldn't send DM to {member}")



@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content.startswith("?"):
        command_name = message.content[1:].split(" ")[0]

        if command_name in ["graved", "found", "clear", "help"]:
            await bot.process_commands(message)
        else:
            logger.warning(f"Deleting invalid message in channel {message.channel.name} ('{message.channel.id}'): {message.content}, reason = invalid command in channel")
            await message.delete()
            return
    else:
        if message.channel.id in [GRAVED_CHANNEL_ID, FOUND_CHANNEL_ID]:
            logger.warning(f"Deleting invalid message in channel {message.channel.name} ('{message.channel.id}'): {message.content}, reason = normal message in command channel")
            await message.delete()
            return

bot.run(BOT_TOKEN)
