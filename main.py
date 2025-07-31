import discord
from discord import app_commands, ui
from discord.ext import commands
import random, string, json, os

GUILD_ID = 1395849900612124784
ADMIN_ROLE_ID = 1395902040827236382

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_FILE = "keys.json"

# === DATABASE ===
def load_keys():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"keys": {}}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=25))

# === CREATE KEY VIEW ===
class KeyCreationView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.generated_key = generate_key()
        self.selected_roles = []
        self.message = None

    async def update_embed(self):
        embed = discord.Embed(title="🔐 Key Creation Panel", color=0x00ffcc)
        embed.add_field(name="🆔 Key", value=f"`{self.generated_key}`", inline=False)
        embed.add_field(name="📛 Assigned Roles", value=f"{', '.join([r.mention for r in self.selected_roles]) if self.selected_roles else '❌ Not set'}", inline=True)
        await self.message.edit(embed=embed, view=self)

    @ui.button(label="🔁 Generate Key", style=discord.ButtonStyle.primary)
    async def generate_key_button(self, interaction, button):
        self.generated_key = generate_key()
        await self.update_embed()
        await interaction.response.defer()

    @ui.button(label="📛 Assign Roles", style=discord.ButtonStyle.secondary)
    async def assign_roles_button(self, interaction, button):
        await interaction.response.send_message("Select roles 👇", ephemeral=True, view=RolesMultiSelect(self), delete_after=30)

    @ui.button(label="✅ Create Key", style=discord.ButtonStyle.success)
    async def create_key_button(self, interaction, button):
        if not self.selected_roles:
            await interaction.response.send_message("❌ Please assign at least one role!", ephemeral=True)
            return
        db = load_keys()
        db["keys"][self.generated_key] = {
            "role_ids": [r.id for r in self.selected_roles]
        }
        save_keys(db)
        await interaction.response.send_message("✅ Key created successfully!", ephemeral=True)
        await self.message.delete()

class RolesMultiSelect(ui.View):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    @ui.select(cls=discord.ui.RoleSelect, placeholder="Select roles", min_values=1, max_values=5)
    async def select_roles(self, interaction, select):
        self.parent.selected_roles = select.values
        await self.parent.update_embed()
        await interaction.response.defer()

# === UPDATE KEY VIEW ===
class UpdateKeyView(ui.View):
    def __init__(self, keys_dict):
        super().__init__(timeout=300)
        self.keys_dict = keys_dict
        self.selected_key = None
        self.new_roles = []
        self.message = None

    async def update_embed(self):
        embed = discord.Embed(title="🛠️ Key Update Panel", color=0x0099ff)
        embed.add_field(name="🔑 Selected Key", value=f"`{self.selected_key}`" if self.selected_key else "❌ Not selected", inline=False)
        embed.add_field(name="📛 New Roles", value=f"{', '.join([r.mention for r in self.new_roles]) if self.new_roles else '❌ Not selected'}", inline=True)
        await self.message.edit(embed=embed, view=self)

    @ui.button(label="🔑 Select Key", style=discord.ButtonStyle.primary)
    async def select_key(self, interaction, button):
        class KeyDropdown(ui.Select):
            def __init__(self, view):
                options = [discord.SelectOption(label=k) for k in list(view.keys_dict)[:25]]
                super().__init__(placeholder="Choose a key", options=options)
                self.view_ref = view

            async def callback(self, interaction):
                self.view_ref.selected_key = self.values[0]
                await self.view_ref.update_embed()
                await interaction.response.defer()

        await interaction.response.send_message("🔽 Select a key:", ephemeral=True, view=ui.View().add_item(KeyDropdown(self)))

    @ui.button(label="📛 Select New Roles", style=discord.ButtonStyle.secondary)
    async def select_roles(self, interaction, button):
        await interaction.response.send_message("Choose roles 👇", ephemeral=True, view=RolesMultiSelect(self), delete_after=30)

    @ui.button(label="✅ Update Key", style=discord.ButtonStyle.success)
    async def update_key(self, interaction, button):
        if not self.selected_key or not self.new_roles:
            await interaction.response.send_message("⚠️ Fill out all fields!", ephemeral=True)
            return

        db = load_keys()
        db["keys"][self.selected_key]["role_ids"] = [r.id for r in self.new_roles]
        save_keys(db)
        await interaction.response.send_message("✅ Key updated!", ephemeral=True)
        await self.message.delete()

# === /create_key ===
@bot.tree.command(name="create_key", description="🔑 Create a key for roles")
@app_commands.checks.has_role(discord.Object(id=ADMIN_ROLE_ID))
async def create_key_command(interaction: discord.Interaction):
    view = KeyCreationView()
    embed = discord.Embed(title="🔐 Key Creation Panel", color=0x00ffcc)
    embed.add_field(name="🆔 Key", value=f"`{view.generated_key}`", inline=False)
    embed.add_field(name="📛 Assigned Roles", value="❌ Not set", inline=True)
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# === /update_key ===
@bot.tree.command(name="update_key", description="♻️ Update an existing key")
@app_commands.checks.has_role(discord.Object(id=ADMIN_ROLE_ID))
async def update_key_command(interaction: discord.Interaction):
    db = load_keys()
    if not db["keys"]:
        await interaction.response.send_message("❌ No keys available.", ephemeral=True)
        return

    view = UpdateKeyView(db["keys"])
    embed = discord.Embed(title="🛠️ Key Update Panel", color=0x0099ff)
    embed.add_field(name="🔑 Selected Key", value="❌ Not selected", inline=False)
    embed.add_field(name="📛 New Roles", value="❌ Not selected", inline=True)
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# === /load_roles ===
@bot.tree.command(name="load_roles", description="🔓 Redeem a key to get your roles")
async def load_roles_command(interaction: discord.Interaction):
    class KeyInputModal(ui.Modal, title="🔑 Enter your role key"):
        key = ui.TextInput(label="Your Key", placeholder="Enter your role key...", required=True)

        async def on_submit(self, inner_interaction: discord.Interaction):
            db = load_keys()
            key_val = self.key.value.strip()
            entry = db["keys"].get(key_val)

            if not entry:
                await inner_interaction.response.send_message("❌ Invalid key!", ephemeral=True)
                return

            roles_given = []
            for role_id in entry["role_ids"]:
                role = interaction.guild.get_role(role_id)
                if role:
                    try:
                        await interaction.user.add_roles(role)
                        roles_given.append(role.mention)
                    except Exception as e:
                        print(f"❌ Fehler beim Rollen hinzufügen: {e}")

            del db["keys"][key_val]
            save_keys(db)

            embed = discord.Embed(title="🎉 Success!", description=f"You received: {', '.join(roles_given)}", color=0x00ff00)
            await inner_interaction.response.send_message(embed=embed, ephemeral=True)

    await interaction.response.send_modal(KeyInputModal())

# === BOT READY ===
@bot.event
async def on_ready():
    await bot.wait_until_ready()
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"🤖 Logged in as {bot.user}")

bot.run(os.getenv("DISCORD_TOKEN"))
