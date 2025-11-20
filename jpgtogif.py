import discord
from discord.ext import commands
from PIL import Image
import os
import aiohttp
import asyncio
from aiohttp import web

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def download_image(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(filename, 'wb') as f:
                    f.write(await resp.read())
                return filename
    return None

def jpg_to_gif(jpg_path, gif_path):
    img = Image.open(jpg_path)
    img.save(gif_path, 'GIF')

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

@bot.command()
async def togif(ctx):
    if not ctx.message.attachments:
        await ctx.send("Veuillez envoyer une image JPG.")
        return

    attachment = ctx.message.attachments[0]
    if not attachment.filename.lower().endswith('.jpg'):
        await ctx.send("Le fichier doit être un JPG.")
        return

    jpg_path = "input.jpg"
    gif_path = "output.gif"

    await download_image(attachment.url, jpg_path)
    jpg_to_gif(jpg_path, gif_path)

    await ctx.send(file=discord.File(gif_path))

    os.remove(jpg_path)
    os.remove(gif_path)

async def handle(request):
    return web.Response(text="Bot running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Serveur web actif sur le port {port}")

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN is None:
        print("❌ Erreur : variable DISCORD_TOKEN manquante")
        return

    webserver = asyncio.create_task(start_webserver())
    bot_task = asyncio.create_task(bot.start(TOKEN))
    await asyncio.gather(webserver, bot_task)

if __name__ == "__main__":
    asyncio.run(main())
