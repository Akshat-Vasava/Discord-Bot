import discord
from discord.ext import commands
import json
import os
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# --- CONFIGURATION ---
TOKEN = os.environ.get("TOKEN")

# --- FILE NAMES ---
DB_FILE = 'players.json'
MATCH_FILE = 'matches.json'

# --- 1. THE "KEEP ALIVE" SERVER (Fixes Port 8000 Error) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"GRx Bot is Live!")

def start_server():
    # Koyeb expects the app to listen on port 8000
    server = HTTPServer(('0.0.0.0', 8000), SimpleHandler)
    server.serve_forever()

def keep_alive():
    t = Thread(target=start_server)
    t.start()

# --- 2. DATA HANDLING (Fixes JSON Error) ---
def load_json(filename):
    if not os.path.exists(filename):
        return {} if filename == DB_FILE else []
    
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # If file is empty or corrupted, return fresh data
        return {} if filename == DB_FILE else []

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

# --- COMMANDS ---

@bot.command()
async def register(ctx, ign: str, uid: str, rank: str, role: str):
    data = load_json(DB_FILE)
    user_id = str(ctx.author.id)
    data[user_id] = {"ign": ign, "uid": uid, "rank": rank, "role": role}
    save_json(DB_FILE, data)
    await ctx.send(f"✅ Registered **{ign}** successfully!")

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_json(DB_FILE)
    user_id = str(member.id)
    if user_id in data:
        p = data[user_id]
        embed = discord.Embed(title=f"Profile: {p['ign']}", color=discord.Color.blue())
        embed.add_field(name="UID", value=p['uid'])
        embed.add_field(name="Rank", value=p['rank'])
        embed.add_field(name="Role", value=p['role'])
        await ctx.send(embed=embed)
    else:
        await ctx.send("⚠️ Not registered!")

@bot.command()
async def matchlog(ctx, kills: int, place: int, *, map_name: str = "Erangel"):
    matches = load_json(MATCH_FILE)
    if isinstance(matches, dict): matches = [] # Safety fix
    
    pts_map = {1:10, 2:6, 3:5, 4:4, 5:3, 6:2, 7:1, 8:1}
    total = pts_map.get(place, 0) + kills
    
    matches.append({"date": str(datetime.date.today()), "map": map_name, "kills": kills, "place": place, "total": total})
    save_json(MATCH_FILE, matches)
    await ctx.send(f"📝 Match Logged: {total} Points")

@bot.command()
async def team(ctx):
    data = load_json(DB_FILE)
    if not data:
        await ctx.send("No players registered.")
        return
    text = "\n".join([f"• {v['ign']} ({v['role']})" for v in data.values()])
    await ctx.send(f"**Team Roster:**\n{text}")

# --- START BOTH SYSTEMS ---
if __name__ == '__main__':
    keep_alive()  # Starts the fake web server first
    bot.run(TOKEN) # Then starts the bot
