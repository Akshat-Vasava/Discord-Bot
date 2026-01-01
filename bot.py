import discord
from discord.ext import commands
import json
import os
import datetime

# --- CONFIGURATION ---
TOKEN = os.environ.get("TOKEN")

# --- FILE NAMES ---
DB_FILE = 'players.json'
MATCH_FILE = 'matches.json'

# --- DATA HANDLING FUNCTIONS ---
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {} if filename == DB_FILE else [] # Return dict for players, list for matches

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name}')
    print('GRx Manager is online! Waiting for commands...')

# ==========================================
# CATEGORY 1: PLAYER MANAGEMENT
# ==========================================

# 1. REGISTER
@bot.command()
async def register(ctx, ign: str, uid: str, rank: str, role: str):
    """Register your BGMI details. Usage: !register <IGN> <UID> <Rank> <Role>"""
    data = load_json(DB_FILE)
    user_id = str(ctx.author.id)

    data[user_id] = {
        "ign": ign,
        "uid": uid,
        "rank": rank,
        "role": role,
        "joined_at": str(datetime.date.today())
    }
    
    save_json(DB_FILE, data)
    
    embed = discord.Embed(title="✅ Registration Successful", color=discord.Color.green())
    embed.add_field(name="Player", value=ign, inline=True)
    embed.add_field(name="Role", value=role, inline=True)
    await ctx.send(embed=embed)

# 2. PROFILE
@bot.command()
async def profile(ctx, member: discord.Member = None):
    """View a player's profile. Usage: !profile OR !profile @User"""
    member = member or ctx.author
    data = load_json(DB_FILE)
    user_id = str(member.id)

    if user_id in data:
        p = data[user_id]
        embed = discord.Embed(title=f"📄 Profile: {p['ign']}", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 UID", value=p['uid'], inline=False)
        embed.add_field(name="🎖️ Rank", value=p['rank'], inline=True)
        embed.add_field(name="🔫 Role", value=p['role'], inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"⚠️ {member.display_name} is not registered! Use `!register`.")

# 3. UPDATE
@bot.command()
async def update(ctx, field: str, *, new_value: str):
    """Update your info. Usage: !update rank Ace Master"""
    data = load_json(DB_FILE)
    user_id = str(ctx.author.id)

    if user_id not in data:
        await ctx.send("⚠️ You are not registered.")
        return

    field = field.lower()
    allowed = ["ign", "uid", "rank", "role"]

    if field in allowed:
        data[user_id][field] = new_value
        save_json(DB_FILE, data)
        await ctx.send(f"✅ Updated your **{field.upper()}** to: **{new_value}**")
    else:
        await ctx.send(f"❌ You can only update: {', '.join(allowed)}")

# 4. TEAM ROSTER
@bot.command()
async def team(ctx):
    """List all registered players."""
    data = load_json(DB_FILE)
    if not data:
        await ctx.send("No players registered yet.")
        return

    embed = discord.Embed(title="🏆 TEAM ROSTER", color=discord.Color.gold())
    text = ""
    for info in data.values():
        text += f"• **{info['ign']}** - {info['role']} ({info['rank']})\n"
    
    embed.description = text
    await ctx.send(embed=embed)

# ==========================================
# CATEGORY 2: COMPETITIVE TOOLS
# ==========================================

# 5. LEADERBOARD (Sorted by Rank Tier)
@bot.command()
async def leaderboard(ctx):
    """Shows players ranked by their tier."""
    data = load_json(DB_FILE)
    if not data: return

    # Helper to score ranks
    def get_rank_score(p):
        r = p['rank'].lower()
        if 'conqueror' in r: return 100
        if 'dominator' in r: return 90
        if 'master' in r: return 85
        if 'ace' in r: return 80
        if 'crown' in r: return 70
        if 'diamond' in r: return 60
        if 'platinum' in r: return 50
        return 0

    sorted_players = sorted(data.values(), key=get_rank_score, reverse=True)

    embed = discord.Embed(title="🔥 RANK LEADERBOARD", color=discord.Color.red())
    text = ""
    for i, p in enumerate(sorted_players, 1):
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
        text += f"{medal} **{p['ign']}** — {p['rank']}\n"

    embed.description = text
    await ctx.send(embed=embed)

# 6. MATCH LOG (Calculates Points)
@bot.command()
async def matchlog(ctx, kills: int, place: int, *, map_name: str = "Erangel"):
    """Log a match result. Usage: !matchlog <kills> <place> <map>"""
    # BGIS Point System
    pts_map = {1:10, 2:6, 3:5, 4:4, 5:3, 6:2, 7:1, 8:1}
    place_pts = pts_map.get(place, 0)
    total_pts = place_pts + kills

    matches = load_json(MATCH_FILE)
    
    new_match = {
        "date": str(datetime.date.today()),
        "map": map_name,
        "kills": kills,
        "place": place,
        "total": total_pts
    }
    
    matches.append(new_match)
    save_json(MATCH_FILE, matches)

    embed = discord.Embed(title=f"📝 Match Recorded: {map_name}", color=discord.Color.green())

    # --- ERROR HANDLING ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        # If they forget to type the numbers
        await ctx.send("❌ **Format Error!** You missed some info.\n"
                       "Correct usage: `!matchlog <kills> <place> <map>`\n"
                       "Example: `!matchlog 10 1 Erangel`")
    elif isinstance(error, commands.BadArgument):
        # If they type text where a number is needed (e.g., "!matchlog ten 1")
        await ctx.send("❌ **Type Error!** Please use numbers for Kills and Place.")
    else:
        # Print other errors to console so you can see them
        print(f"Error: {error}")


bot.run(TOKEN)
