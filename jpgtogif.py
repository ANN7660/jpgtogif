import discord
from discord.ext import commands
from PIL import Image
import requests
from io import BytesIO
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='+', intents=intents)
bot.remove_command('help')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (id: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Error syncing commands: {e.__class__.__name__}: {e}")

@bot.command(name='help')
async def custom_help(ctx):
    embed = discord.Embed(title="Aide du bot", description="Liste des commandes", color=0x2ecc71)
    embed.add_field(name="+ping", value="Répond avec Pong et la latence.", inline=False)
    embed.add_field(name="+jpg2gif <url>", value="Convertit une image JPG/PNG en GIF via URL.", inline=False)
    embed.add_field(name="+gif", value="Convertit une image envoyée en pièce jointe en GIF.", inline=False)
    embed.set_footer(text="N'oublie pas de configurer DISCORD_TOKEN dans les variables d'environnement.")
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f'Pong! Latence : {latency_ms} ms')

@bot.command(name='jpg2gif')
@commands.cooldown(1, 5, commands.BucketType.user)
async def jpg2gif(ctx, image_url: str = None):
    if not image_url:
        await ctx.send("🔴 Tu dois fournir une URL d'image. Exemple : `+jpg2gif https://.../image.jpg`")
        return

    await ctx.trigger_typing()

    try:
        resp = requests.get(image_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        await ctx.send(f"❌ Impossible de télécharger l'image : {e}")
        return

    try:
        img = Image.open(BytesIO(resp.content)).convert('RGBA')
    except Exception as e:
        await ctx.send(f"❌ Le fichier fourni n'est pas une image supportée ou est corrompu : {e}")
        return

    try:
        gif_bytes = BytesIO()
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
            img = background.convert('RGB')
        img.save(gif_bytes, format='GIF', save_all=True)
        gif_bytes.seek(0)
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la conversion en GIF : {e}")
        return

    filename = 'converted.gif'
    await ctx.send(file=discord.File(fp=gif_bytes, filename=filename))

@bot.command(name='gif')
@commands.cooldown(1, 5, commands.BucketType.user)
async def gif(ctx):
    if not ctx.message.attachments:
        await ctx.send("🔴 Tu dois envoyer une image **en pièce jointe** avec la commande `+gif`.")
        return

    attachment = ctx.message.attachments[0]

    if not attachment.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        await ctx.send("❌ Le fichier doit être une image JPG ou PNG.")
        return

    await ctx.trigger_typing()

    try:
        img_bytes = await attachment.read()
        img = Image.open(BytesIO(img_bytes)).convert('RGBA')
    except Exception as e:
        await ctx.send(f"❌ Impossible d'ouvrir l'image : {e}")
        return

    try:
        gif_bytes = BytesIO()
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
            img = background.convert('RGB')
        img.save(gif_bytes, format='GIF', save_all=True)
        gif_bytes.seek(0)
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la conversion : {e}")
        return

    await ctx.send(file=discord.File(fp=gif_bytes, filename="converted.gif"))

@jpg2gif.error
async def jpg2gif_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Commande en cooldown. Réessaye dans {round(error.retry_after, 1)}s.")
    else:
        await ctx.send(f"❌ Erreur : {error}")

@gif.error
async def gif_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Commande en cooldown. Réessaye dans {round(error.retry_after, 1)}s.")
    else:
        await ctx.send(f"❌ Erreur : {error}")

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("⚠️ DISCORD_TOKEN manquant! Configurez-le dans les variables d'environnement.")
    bot.run(TOKEN)
