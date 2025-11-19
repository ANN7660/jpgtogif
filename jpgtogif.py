import discord
from discord.ext import commands
from PIL import Image
import requests
from io import BytesIO
import os

# Configuration du bot

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='+', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} est connecté!')

@bot.command(name='gif')
async def image_to_gif(ctx):
    """Convertit une image en GIF (statique)"""

    # Vérifier si un fichier est attaché
    if not ctx.message.attachments:
        await ctx.send("❌ Veuillez joindre une image à votre message!")
        return

    attachment = ctx.message.attachments[0]

    # Vérifier si c'est une image
    if not attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
        await ctx.send("❌ Le fichier doit être une image (PNG, JPG, JPEG, WEBP, BMP)")
        return

    await ctx.send("⏳ Conversion en cours...")

    try:
        # Télécharger l'image
        response = requests.get(attachment.url)
        img = Image.open(BytesIO(response.content))

        # Convertir en RGB si nécessaire (GIF ne supporte pas la transparence RGBA)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Sauvegarder en GIF (image statique)
        output = BytesIO()
        img.save(output, format='GIF', optimize=True)
        output.seek(0)

        # Envoyer le GIF
        await ctx.send(
            "✅ Voici votre image convertie en GIF!",
            file=discord.File(output, filename='image.gif')
        )

    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la conversion: {str(e)}")

@bot.command(name='help')
async def help_command(ctx):
    """Affiche l’aide pour le bot"""
    embed = discord.Embed(
        title="🖼️ Bot Convertisseur Image → GIF",
        description="Transformez vos images en format GIF!",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="+gif",
        value="Convertit une image en GIF (statique)\nJoignez une image à votre message",
        inline=False
    )

    embed.add_field(
        name="Formats supportés",
        value="PNG, JPG, JPEG, WEBP, BMP → GIF",
        inline=False
    )

    embed.add_field(
        name="Utilisation",
        value="1. Envoyez `+gif`\n2. Joignez votre image\n3. Recevez le GIF!",
        inline=False
    )

    await ctx.send(embed=embed)

# Lancement du bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("⚠️ DISCORD_TOKEN manquant! Configurez-le dans Render.")
    bot.run(TOKEN)
