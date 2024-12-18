import discord
from discord.ext import commands
from load_data import load_data

# Knives data
KNIFE_NUMBER,GRAVED_LOGS,FOUND_LOGS = load_data()

# Intents de Discord
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="?", intents=intents)

# Path to where datas are saved
data_path = "DATA/data.json"

# Normal server
GRAVED_CHANNEL_ID = 1287736015963820113
FOUND_CHANNEL_ID = 1287810208646824057
BACKUP_CHANNEL = 1292868151943368774

TRUSTED_GRAVERS_ID = 1287802529018810458
TRUSTED_FOUNDER_ID = 1287834910735990875


# Test server
# GRAVED_CHANNEL_ID = 1292850072060559462
# FOUND_CHANNEL_ID = 1292850093153587303
# BACKUP_CHANNEL = 1292868099141402775

# TRUSTED_GRAVERS_ID = 1292849674289680465
# TRUSTED_FOUNDER_ID = 1292849756590047303


