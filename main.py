import discord
from discord.ext import commands, tasks
import os
import json
from dotenv import load_dotenv
from typing import Optional

# --- Configuration ---
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PREFIX = '!'
EMBED_FILE = 'embeds.json' # File to store embed templates

# --- Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# --- Data Management ---
ping_tasks = {}
embed_templates = {}

def load_embed_templates():
    """Loads embed templates from the JSON file."""
    global embed_templates
    try:
        with open(EMBED_FILE, 'r') as f:
            embed_templates = json.load(f)
    except FileNotFoundError:
        embed_templates = {} # Create it if it doesn't exist
    except json.JSONDecodeError:
        embed_templates = {} # Reset if file is corrupted
        print("Warning: embeds.json was corrupted and has been reset.")


def save_embed_templates():
    """Saves embed templates to the JSON file."""
    with open(EMBED_FILE, 'w') as f:
        json.dump(embed_templates, f, indent=4)

# --- UI Components (Modals & Views) ---

class EmbedCreateModal(discord.ui.Modal, title='Create a New Embed Template'):
    """A Modal for creating a new embed template."""
    template_name = discord.ui.TextInput(
        label='Template Name',
        placeholder='e.g., "weekly-reminder" or "event-announcement"',
        required=True,
        style=discord.TextStyle.short
    )
    embed_title = discord.ui.TextInput(
        label='Embed Title',
        placeholder='The main title of the embed',
        required=True,
        style=discord.TextStyle.short
    )
    embed_description = discord.ui.TextInput(
        label='Embed Description',
        placeholder='The main text content. Supports **markdown**.',
        required=True,
        style=discord.TextStyle.long
    )
    embed_color = discord.ui.TextInput(
        label='Embed Color (Hex Code)',
        placeholder='e.g., #FF5733 or 0xFF5733 (Default is blurple)',
        required=False,
        max_length=7
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        name = self.template_name.value.strip().lower()
        color_str = self.embed_color.value.strip() or "#7289DA" # Default to Discord Blurple

        # Validate hex color
        try:
            color_int = int(color_str.replace("#", "0x"), 16)
        except ValueError:
            await interaction.response.send_message("❌ Invalid hex color code. Please use a format like `#FF5733`.", ephemeral=True)
            return

        if guild_id not in embed_templates:
            embed_templates[guild_id] = {}

        embed_templates[guild_id][name] = {
            'title': self.embed_title.value,
            'description': self.embed_description.value,
            'color': color_int
        }
        save_embed_templates()

        # Create a preview
        preview_embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=color_int
        )
        await interaction.response.send_message(f"✅ Success! Embed template `{name}` has been saved.", embed=preview_embed, ephemeral=True)

class EmbedBuilderView(discord.ui.View):
    """The main view for the embed builder command."""
    def __init__(self, author):
        super().__init__(timeout=180)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id

    @discord.ui.button(label="Create New Embed", style=discord.ButtonStyle.green, emoji="✨")
    async def create_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedCreateModal())

    @discord.ui.button(label="List My Embeds", style=discord.ButtonStyle.blurple, emoji="📋")
    async def list_embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        if guild_id not in embed_templates or not embed_templates[guild_id]:
            await interaction.response.send_message("You have no saved embed templates on this server.", ephemeral=True)
            return

        template_list = "\n".join(f"- `{name}`" for name in embed_templates[guild_id].keys())
        embed = discord.Embed(
            title="Saved Embed Templates",
            description=template_list,
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Delete an Embed", style=discord.ButtonStyle.red, emoji="🗑️")
    async def delete_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        if guild_id not in embed_templates or not embed_templates[guild_id]:
            await interaction.response.send_message("There are no templates to delete.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label=name, description=f"Delete the '{name}' template.")
            for name in embed_templates[guild_id].keys()
        ]
        select = discord.ui.Select(placeholder="Choose a template to delete...", options=options)

        async def select_callback(select_interaction: discord.Interaction):
            template_name = select_interaction.data['values'][0]
            del embed_templates[guild_id][template_name]
            save_embed_templates()
            await select_interaction.response.send_message(f"✅ Template `{template_name}` has been deleted.", ephemeral=True)
            # Disable the select menu after use
            self.clear_items()
            await interaction.edit_original_response(view=self)


        select.callback = select_callback
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Which template would you like to delete?", view=view, ephemeral=True)

# --- Bot Commands ---

@bot.event
async def on_ready():
    """Runs when the bot is ready."""
    load_embed_templates()
    print(f'Logged in as {bot.user.name}')
    print('Bot is ready.')
    print('------')

@bot.command(name='embedbuilder')
@commands.has_permissions(administrator=True)
async def embed_builder(ctx):
    """The main command to manage embed templates."""
    embed = discord.Embed(
        title="Embed Builder Menu",
        description="Use the buttons below to create, list, or delete embed templates for your pings.",
        color=discord.Color.dark_gold()
    )
    await ctx.send(embed=embed, view=EmbedBuilderView(ctx.author))

@bot.command(name='setping')
@commands.has_permissions(administrator=True)
async def set_ping(ctx, role: discord.Role, interval_minutes: int, template_name: str):
    """Sets up a recurring ping using a saved embed template."""
    guild_id = str(ctx.guild.id)
    template_name = template_name.lower()

    if guild_id not in embed_templates or template_name not in embed_templates[guild_id]:
        await ctx.send(f"❌ Error: An embed template named `{template_name}` was not found. Use `!embedbuilder` to create one first.")
        return

    # Cancel existing task if any
    if ctx.guild.id in ping_tasks:
        ping_tasks[ctx.guild.id]['task'].cancel()

    @tasks.loop(minutes=interval_minutes)
    async def ping_role_task():
        template = embed_templates[guild_id][template_name]
        embed_to_send = discord.Embed.from_dict(template)
        # Send the role mention in the content field to ensure a notification
        await ctx.send(content=role.mention, embed=embed_to_send)
        print(f"Pinged {role.name} in {ctx.guild.name} using template '{template_name}'.")


    ping_tasks[ctx.guild.id] = {'task': ping_role_task}
    ping_role_task.start()
    await ctx.send(f"✅ **Ping schedule started!**\nI will ping `{role.name}` every `{interval_minutes}` minutes using the `{template_name}` embed.")

@bot.command(name='stopping')
@commands.has_permissions(administrator=True)
async def stop_ping(ctx):
    """Stops the recurring ping schedule for this server."""
    if ctx.guild.id in ping_tasks:
        ping_tasks[ctx.guild.id]['task'].cancel()
        del ping_tasks[ctx.guild.id]
        await ctx.send('🛑 **Ping schedule stopped.**')
    else:
        await ctx.send('There is no active ping schedule to stop.')

# --- Error Handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return # Ignore invalid commands
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Error:** You do not have administrator permissions to run this command.", ephemeral=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Error:** You are missing a required argument. Check the command's usage in the `!help` or `README`.", ephemeral=True)
    else:
        print(f"An unhandled error occurred in {ctx.guild.name}: {error}")
        await ctx.send("❌ An unexpected error occurred. I've logged it for my developer.", ephemeral=True)

# --- Main Execution ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("!!! ERROR: BOT_TOKEN environment variable not found.")
    else:
        bot.run(BOT_TOKEN)
