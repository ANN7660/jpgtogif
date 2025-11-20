import discord
from discord.ext import commands
from PIL import Image
from io import BytesIO
import os

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
    embed.add_field(name="+gif", value="Convertit une image envoyée en pièce jointe en GIF.", inline=False)
    embed.set_footer(text="Bot convertisseur GIF")
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latence : {latency_ms} ms")

@bot.command(name='gif')
@commands.cooldown(1, 5, commands.BucketType.user)
async def gif(ctx):
    if not ctx.message.attachments:
        await ctx.send("🔴 Tu dois envoyer une image **en pièce jointe** puis taper `+gif`.")
        return

    attachment = ctx.message.attachments[0]

    if not attachment.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        await ctx.send("❌ Le fichier doit être une image JPG ou PNG.")
        return

    async with ctx.typing():
        try:
            img_bytes = await attachment.read()
            img = Image.open(BytesIO(img_bytes))
        except Exception as e:
            await ctx.send(f"❌ Impossible d'ouvrir l'image : {e}")
            return

        try:
            # Conversion GIF propre
            rgb_img = img.convert('RGB')
            optimized = rgb_img.convert('P', palette=Image.ADAPTIVE, colors=255)

            gif_bytes = BytesIO()
            optimized.save(gif_bytes, format='GIF')
            gif_bytes.seek(0)

        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la conversion : {e}")
            return

    await ctx.send(file=discord.File(fp=gif_bytes, filename='converted.gif'))

@gif.error
async def gif_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Commande en cooldown. Réessaye dans {round(error.retry_after, 1)}s.")
    else:
        await ctx.send(f"❌ Erreur : {error}")

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError('⚠️ DISCORD_TOKEN manquant !')
    bot.run(TOKEN)
