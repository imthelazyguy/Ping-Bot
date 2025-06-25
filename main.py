import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from typing import Optional

# --- Keep Alive Setup ---
from flask import Flask
from threading import Thread
# ------------------------


# --- Configuration ---
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PREFIX = '!'
# -----------------------------


# --- Keep Alive Web Server ---
app = Flask('')

@app.route('/')
def home():
    """This route is pinged by UptimeRobot to keep the bot alive."""
    # This print statement is optional but useful for seeing pings in your logs.
    print(f"Keep-alive ping received at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    return "I'm alive!"

def run_web_server():
    """Runs the Flask web server."""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def start_keep_alive_thread():
    """Starts the web server in a new thread."""
    t = Thread(target=run_web_server)
    t.start()
# -----------------------------


# --- Bot Setup ---
intents = discord.Intents.default()
intents.messages = True; intents.guilds = True; intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# --- In-Memory Data Management ---
ping_tasks = {}
embed_templates = {} # Templates will be stored here temporarily.

def load_embed_templates():
    """Initializes the in-memory dictionary. Called on startup."""
    global embed_templates
    embed_templates = {}
    print("Initialized in-memory storage for embed templates. Templates will be lost on restart.")

def save_embed_templates():
    """A placeholder function. In this version, saving does not persist data."""
    # This function doesn't need to do anything since data is only in memory.
    pass

# --- UI Components (Modals & Views) ---
class EmbedCreateModal(discord.ui.Modal, title='Create a New Embed Template'):
    template_name = discord.ui.TextInput(label='Template Name', placeholder='e.g., "weekly-reminder"', required=True)
    embed_title = discord.ui.TextInput(label='Embed Title', placeholder='The main title', required=True)
    embed_description = discord.ui.TextInput(label='Embed Description', placeholder='The main text. Supports markdown.', required=True, style=discord.TextStyle.long)
    embed_color = discord.ui.TextInput(label='Embed Color (Hex Code)', placeholder='e.g., #FF5733', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        name = self.template_name.value.strip().lower()
        color_str = self.embed_color.value.strip() or "#7289DA"
        try:
            color_int = int(color_str.replace("#", "0x"), 16)
        except ValueError:
            await interaction.response.send_message("❌ Invalid hex color code.", ephemeral=True); return
        if guild_id not in embed_templates:
            embed_templates[guild_id] = {}
        embed_templates[guild_id][name] = {'title': self.embed_title.value, 'description': self.embed_description.value, 'color': color_int}
        save_embed_templates() # This call remains but does nothing.
        preview_embed = discord.Embed(title=self.embed_title.value, description=self.embed_description.value, color=color_int)
        await interaction.response.send_message(f"✅ Success! Embed template `{name}` has been saved for this session.", embed=preview_embed, ephemeral=True)

class EmbedBuilderView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=180); self.author = author
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the command author can use these buttons.", ephemeral=True); return False
        return True
        
    @discord.ui.button(label="Create", style=discord.ButtonStyle.green, emoji="✨")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button): # <--- THIS LINE IS NOW CORRECTED
        await interaction.response.send_modal(EmbedCreateModal())

    @discord.ui.button(label="List", style=discord.ButtonStyle.blurple, emoji="📋")
    async def list(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        if not embed_templates.get(guild_id):
            await interaction.response.send_message("No saved templates in the current session.", ephemeral=True); return
        template_list = "\n".join(f"- `{name}`" for name in embed_templates[guild_id].keys())
        await interaction.response.send_message(embed=discord.Embed(title="Session Templates", description=template_list, color=discord.Color.blurple()), ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red, emoji="🗑️")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        if not embed_templates.get(guild_id):
            await interaction.response.send_message("No templates to delete.", ephemeral=True); return
        options = [discord.SelectOption(label=name) for name in embed_templates[guild_id].keys()]
        select = discord.ui.Select(placeholder="Choose a template to delete...", options=options)
        async def cb(sel_interaction: discord.Interaction):
            name = sel_interaction.data['values'][0]
            del embed_templates[guild_id][name]
            save_embed_templates()
            await sel_interaction.response.edit_message(content=f"✅ Template `{name}` deleted for this session.", view=None)
        select.callback = cb
        view = discord.ui.View(timeout=60); view.add_item(select)
        await interaction.response.send_message("Which template to delete?", view=view, ephemeral=True)

# --- Bot Commands ---
@bot.event
async def on_ready():
    load_embed_templates()
    print(f'Logged in as {bot.user.name}'); print('Bot is ready.')

@bot.command()
@commands.has_permissions(administrator=True)
async def embedbuilder(ctx):
    await ctx.send(embed=discord.Embed(title="Embed Builder Menu (In-Memory)", description="Templates created will be lost on restart.", color=discord.Color.dark_gold()), view=EmbedBuilderView(ctx.author))

@bot.command()
@commands.has_permissions(administrator=True)
async def setping(ctx, channel: discord.TextChannel, role: discord.Role, interval_minutes: int, template_name: str):
    guild_id = str(ctx.guild.id)
    template_name = template_name.lower()
    if not embed_templates.get(guild_id) or template_name not in embed_templates[guild_id]:
        await ctx.send(f"❌ Error: Template `{template_name}` not found in the current session."); return
    if ctx.guild.id in ping_tasks:
        ping_tasks[ctx.guild.id]['task'].cancel()
    @tasks.loop(minutes=interval_minutes)
    async def ping_task():
        if embed_templates.get(guild_id) and template_name in embed_templates[guild_id]:
            template = embed_templates[guild_id][template_name]
            await channel.send(content=role.mention, embed=discord.Embed.from_dict(template))
        else:
            await channel.send(f"⚠️ The ping schedule for `{role.name}` is stopping because the embed template `{template_name}` is no longer in memory.")
            ping_task.cancel()
    ping_tasks[ctx.guild.id] = {'task': ping_task}; ping_task.start()
    await ctx.send(f"✅ Ping schedule started in {channel.mention} for `{role.name}` every `{interval_minutes}` minutes using template `{template_name}`.")

@bot.command()
@commands.has_permissions(administrator=True)
async def stopping(ctx):
    if ctx.guild.id in ping_tasks:
        ping_tasks[ctx.guild.id]['task'].cancel(); del ping_tasks[ctx.guild.id]
        await ctx.send('🛑 Ping schedule stopped.')
    else:
        await ctx.send('No active schedule to stop.')

# --- Main Execution ---
if __name__ == "__main__":
    from datetime import datetime, timezone
    if not BOT_TOKEN:
        print("!!! ERROR: BOT_TOKEN environment variable must be set.")
    else:
        start_keep_alive_thread()
        bot.run(BOT_TOKEN)

