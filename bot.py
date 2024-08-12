import discord
from discord.ext import commands, tasks
import json
import os
import aiohttp
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
INVITE_LINK = "hier dein discord bot invit link"

# Intents konfigurieren
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Erstelle den Bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Bot Status
activity = discord.Streaming(name="Globalchateinrichten mit !setup", url="http://www.twitch.tv/sapcepascal")
bot.activity = activity

# Initialisiere die JSON-Datei für Globalchat
if not os.path.exists('globalchat.json'):
    with open('globalchat.json', 'w') as f:
        json.dump({"global_channels": [], "banned_users": [], "banned_servers": []}, f, indent=4)

def load_data():
    with open('globalchat.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('globalchat.json', 'w') as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f'Bot ist angemeldet als {bot.user}')
    fetch_status.start()  # Start the status update loop

# Check if user is the privileged user
def is_privileged_user(ctx):
    return ctx.author.id == 1108408817626124439

# Globalchat Setup Command
@bot.command(name='setup', help='Fügt diesen Kanal zum Globalchat hinzu')
@commands.has_permissions(administrator=True)
async def setup(ctx):
    data = load_data()
    if ctx.channel.id not in data['global_channels']:
        data['global_channels'].append(ctx.channel.id)
        save_data(data)
        await ctx.send(embed=discord.Embed(description='Dieser Kanal wurde erfolgreich zum Globalchat hinzugefügt.', color=discord.Color.green()))
    else:
        await ctx.send(embed=discord.Embed(description='Dieser Kanal ist bereits im Globalchat.', color=discord.Color.red()))

# Globalchat Remove Command
@bot.command(name='remove', help='Entfernt diesen Kanal vom Globalchat')
@commands.has_permissions(administrator=True)
async def remove(ctx):
    data = load_data()
    if ctx.channel.id in data['global_channels']:
        data['global_channels'].remove(ctx.channel.id)
        save_data(data)
        await ctx.send(embed=discord.Embed(description='Dieser Kanal wurde erfolgreich vom Globalchat entfernt.', color=discord.Color.green()))
    else:
        await ctx.send(embed=discord.Embed(description='Dieser Kanal ist nicht im Globalchat.', color=discord.Color.red()))

# Ban Command
@bot.command(name='ban', help='Bannt einen Benutzer oder Server vom Globalchat')
@commands.has_role(1271917530528747566)  # Ersetzen Sie durch die ID der entsprechenden Rolle
@commands.check(is_privileged_user)
async def ban(ctx, id: int):
    data = load_data()
    if id not in data['banned_users'] and id not in data['banned_servers']:
        if ctx.guild.get_member(id):
            data['banned_users'].append(id)
        else:
            data['banned_servers'].append(id)
        save_data(data)
        log_channel = bot.get_channel(1271917640473903237)
        if log_channel:
            await log_channel.send(embed=discord.Embed(description=f'ID {id} wurde vom Globalchat gebannt.', color=discord.Color.red()))
        await ctx.send(embed=discord.Embed(description=f'ID {id} wurde erfolgreich vom Globalchat gebannt.', color=discord.Color.green()))
    else:
        await ctx.send(embed=discord.Embed(description='Diese ID ist bereits gebannt.', color=discord.Color.red()))

# Unban Command
@bot.command(name='unban', help='Entbannt einen Benutzer oder Server vom Globalchat')
@commands.has_role(1271917530528747566)  # Ersetzen Sie durch die ID der entsprechenden Rolle
@commands.check(is_privileged_user)
async def unban(ctx, id: int):
    data = load_data()
    if id in data['banned_users']:
        data['banned_users'].remove(id)
        save_data(data)
        log_channel = bot.get_channel(1271917640473903237)
        if log_channel:
            await log_channel.send(embed=discord.Embed(description=f'ID {id} wurde vom Globalchat entbannt.', color=discord.Color.green()))
        await ctx.send(embed=discord.Embed(description=f'ID {id} wurde erfolgreich entbannt.', color=discord.Color.green()))
    elif id in data['banned_servers']:
        data['banned_servers'].remove(id)
        save_data(data)
        log_channel = bot.get_channel(1271917640473903237)
        if log_channel:
            await log_channel.send(embed=discord.Embed(description=f'ID {id} wurde vom Globalchat entbannt.', color=discord.Color.green()))
        await ctx.send(embed=discord.Embed(description=f'ID {id} wurde erfolgreich entbannt.', color=discord.Color.green()))
    else:
        await ctx.send(embed=discord.Embed(description='Diese ID ist nicht gebannt.', color=discord.Color.red()))

# Error Handling für fehlende Berechtigungen
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(description="Netter Versuch. Du versuchst wohl, mich ohne die notwendigen Berechtigungen zu benutzen. Das darfst du nicht.", color=discord.Color.red()))
    elif isinstance(error, commands.MissingRole):
        await ctx.send(embed=discord.Embed(description="Netter Versuch. Du versuchst wohl, mich ohne die notwendige Rolle zu benutzen. Das darfst du nicht.", color=discord.Color.red()))
    else:
        raise error

# Globalchat Nachricht senden
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_data()

    if message.channel.id in data['global_channels']:
        if message.author.id in data['banned_users'] or message.guild.id in data['banned_servers']:
            # DM den gebannten Benutzer
            try:
                user = bot.get_user(message.author.id)
                if user:
                    await user.send(embed=discord.Embed(description="Du bist vom Globalchat gebannt worden und kannst hier nicht mehr posten.", color=discord.Color.red()))
            except Exception as e:
                print(f'Fehler beim Senden der DM: {e}')
            return
        
        for channel_id in data['global_channels']:
            if channel_id != message.channel.id:
                channel = bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(description=message.content, color=discord.Color.blue())
                    embed.set_author(name=f'{message.author} ({message.author.top_role.name})', icon_url=message.author.avatar.url)
                    embed.set_footer(text=f'Vom Server: {message.guild.name}', icon_url=message.guild.icon.url)
                    embed.add_field(name='Bot Invite', value=f'[Hier klicken]({INVITE_LINK})', inline=True)
                    invite = await message.channel.create_invite(max_age=0, max_uses=0, unique=False)
                    embed.add_field(name='Server Invite', value=f'[Hier klicken]({invite.url})', inline=True)
                    await channel.send(embed=embed)

    await bot.process_commands(message)

# Globalchat Info Command
@bot.command(name='globalchatinfo', help='Zeigt Informationen über den Globalchat an')
async def globalchatinfo(ctx):
    data = load_data()
    global_channels = len(data['global_channels'])
    banned_users = len(data['banned_users'])
    banned_servers = len(data['banned_servers'])
    await ctx.send(embed=discord.Embed(
        title='Globalchat Information',
        color=discord.Color.blue()
    ).add_field(name='Anzahl der Globalchat-Kanäle', value=str(global_channels), inline=False
    ).add_field(name='Anzahl der gebannten Benutzer', value=str(banned_users), inline=False
    ).add_field(name='Anzahl der gebannten Server', value=str(banned_servers), inline=False
    ).add_field(name='Bot Invite', value=f'[Hier klicken]({INVITE_LINK})', inline=False))

# Überprüfe Nickname bei Aktualisierung
@bot.event
async def on_member_update(before, after):
    if after.id == 127047895304346238 and after.nick != 'Gamerarea_globalchat':
        try:
            await after.edit(nick='Gamerarea_globalchat')
            print(f'Nickname von {after} wurde zurückgesetzt.')
        except discord.Forbidden:
            print(f'Keine Berechtigung, den Nickname von {after} zurückzusetzen.')

# Status Fetch Task
@tasks.loop(seconds=19)
async def fetch_status():
    url = 'dein uptime kuma push link'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                print('Status-Update erfolgreich gesendet')
            else:
                print(f'Fehler beim Senden des Status-Updates: {response.status}')

bot.run(TOKEN)
