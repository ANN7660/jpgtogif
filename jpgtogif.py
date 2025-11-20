import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import os
import aiohttp
import asyncio
from io import BytesIO
from aiohttp import web

# ---------- Configuration ----------
PREFIX = "+"
INTENTS = discord.Intents.default()
INTENTS.message_content = True
BOT = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

# ---------- Utilities ----------
async def read_attachment(att):
    """Return a PIL Image or bytes for a GIF (preserve animated GIF bytes)."""
    data = await att.read()
    b = BytesIO(data)
    b.seek(0)
    try:
        img = Image.open(b)
        # Keep file pointer open for animated GIFs
        return img, data
    except Exception:
        return None, data

def pil_to_bytes(img, format="GIF", save_all=False, duration=100, loop=0):
    """Save PIL image (or frames) to bytes."""
    out = BytesIO()
    save_kwargs = {"format": format}
    if format.upper() == "GIF" and save_all:
        save_kwargs.update({"save_all": True, "append_images": img[1:], "duration": duration, "loop": loop})
        img[0].save(out, **save_kwargs)
    else:
        img.save(out, **save_kwargs)
    out.seek(0)
    return out

def save_frames_to_gif(frames, duration=100, loop=0):
    """Given a list of PIL Image frames, return BytesIO of GIF."""
    out = BytesIO()
    frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], duration=duration, loop=loop)
    out.seek(0)
    return out

def ensure_rgb(image):
    if image.mode in ("RGBA", "P", "LA"):
        return image.convert("RGBA")
    return image.convert("RGB")

# ---------- Commands ----------
@BOT.event
async def on_ready():
    print(f"Bot connecté : {BOT.user}")

@BOT.command(name="gif")
async def cmd_gif(ctx):
    """+gif : Convertit une image JPG (ou PNG) en GIF simple"""
    if not ctx.message.attachments:
        return await ctx.send("Envoie une image JPG/PNG attachée avec la commande `+gif`.")
    att = ctx.message.attachments[0]
    img, _ = await read_attachment(att)
    if img is None:
        return await ctx.send("Impossible d'ouvrir l'image.")
    # Convert to RGB and save single-frame GIF
    frame = ensure_rgb(img)
    out = BytesIO()
    frame.save(out, format="GIF")
    out.seek(0)
    await ctx.send(file=discord.File(out, filename="output.gif"))

@BOT.command(name="gifmulti")
async def cmd_gifmulti(ctx):
    """+gifmulti : Envoie plusieurs images (2+) en pièces jointes -> GIF animé"""
    if not ctx.message.attachments or len(ctx.message.attachments) < 2:
        return await ctx.send("Envoie au moins 2 images attachées pour `+gifmulti`.")
    frames = []
    for att in ctx.message.attachments:
        img, _ = await read_attachment(att)
        if img is None:
            continue
        frames.append(ensure_rgb(img))
    if not frames:
        return await ctx.send("Aucune image valide trouvée.")
    gif_bytes = save_frames_to_gif(frames, duration=200)
    await ctx.send(file=discord.File(gif_bytes, filename="animation.gif"))

@BOT.command(name="giftext")
async def cmd_giftext(ctx, *, text: str = None):
    """+giftext <texte> : Ajoute du texte sur l'image attachée"""
    if text is None:
        return await ctx.send("Usage: `+giftext ton texte` (et join une image).")
    if not ctx.message.attachments:
        return await ctx.send("Attach une image pour `+giftext`.")
    att = ctx.message.attachments[0]
    img, _ = await read_attachment(att)
    if img is None:
        return await ctx.send("Impossible d'ouvrir l'image.")
    base = ensure_rgb(img)
    draw = ImageDraw.Draw(base)
    try:
        # Try to load a truetype font if available
        font = ImageFont.truetype("arial.ttf", size=max(20, base.width // 15))
    except Exception:
        font = ImageFont.load_default()
    text_w, text_h = draw.textsize(text, font=font)
    # Place text at bottom center with semi-transparent box
    padding = 10
    x = (base.width - text_w) // 2
    y = base.height - text_h - padding
    # draw rectangle
    rect_y0 = y - padding // 2
    rect_y1 = y + text_h + padding // 2
    draw.rectangle([(0, rect_y0), (base.width, rect_y1)], fill=(0,0,0,180))
    draw.text((x, y), text, font=font, fill=(255,255,255))
    out = BytesIO()
    base.save(out, format="GIF")
    out.seek(0)
    await ctx.send(file=discord.File(out, filename="text.gif"))

@BOT.command(name="gifbounce")
async def cmd_gifbounce(ctx):
    """+gifbounce : Crée un GIF bounce à partir de plusieurs images ou d'un GIF"""
    if not ctx.message.attachments:
        return await ctx.send("Attach une image/GIF pour `+gifbounce`.")
    att = ctx.message.attachments[0]
    img, raw = await read_attachment(att)
    frames = []
    if img is None:
        return await ctx.send("Impossible d'ouvrir le fichier.")
    # If animated GIF, extract frames
    try:
        for frame in ImageSequence.Iterator(img):
            frames.append(ensure_rgb(frame.copy()))
    except Exception:
        frames.append(ensure_rgb(img))
    # Create bounce: forward + reversed (excluding last to avoid duplicate)
    bounce = frames + frames[-2:0:-1] if len(frames) > 1 else frames
    gif_bytes = save_frames_to_gif(bounce, duration=100)
    await ctx.send(file=discord.File(gif_bytes, filename="bounce.gif"))

@BOT.command(name="gifspeed")
async def cmd_gifspeed(ctx, factor: float = 1.0):
    """+gifspeed <factor> : Change la vitesse d'un GIF attaché (factor <1 = slower, >1 = faster)"""
    if not ctx.message.attachments:
        return await ctx.send("Attach un GIF pour `+gifspeed factor`.")
    att = ctx.message.attachments[0]
    img, raw = await read_attachment(att)
    if img is None:
        return await ctx.send("Impossible d'ouvrir l'image.")
    # Default frame duration: try to read from info, fallback 100ms
    durations = []
    frames = []
    try:
        for frame in ImageSequence.Iterator(img):
            frames.append(ensure_rgb(frame.copy()))
            durations.append(frame.info.get("duration", 100))
    except Exception:
        return await ctx.send("Le fichier n'est pas un GIF animé.")
    # Compute new duration per frame
    new_durations = [max(10, int(d * (1.0 / factor))) for d in durations]
    avg = int(sum(new_durations) / len(new_durations))
    gif_bytes = save_frames_to_gif(frames, duration=avg)
    await ctx.send(file=discord.File(gif_bytes, filename=f"speed_{factor}.gif"))

@BOT.command(name="tojpg")
async def cmd_tojpg(ctx):
    """+tojpg : Convertit un GIF attaché (ou image) en JPG (première frame)"""
    if not ctx.message.attachments:
        return await ctx.send("Attach un GIF ou une image pour `+tojpg`.")
    att = ctx.message.attachments[0]
    img, raw = await read_attachment(att)
    if img is None:
        return await ctx.send("Impossible d'ouvrir le fichier.")
    # Take first frame
    try:
        frame = next(ImageSequence.Iterator(img)).convert("RGB")
    except Exception:
        frame = img.convert("RGB")
    out = BytesIO()
    frame.save(out, format="JPEG")
    out.seek(0)
    await ctx.send(file=discord.File(out, filename="frame.jpg"))

@BOT.command(name="gifbw")
async def cmd_gifbw(ctx):
    """+gifbw : Transforme une image/GIF en noir et blanc"""
    if not ctx.message.attachments:
        return await ctx.send("Attach un fichier pour `+gifbw`.")
    att = ctx.message.attachments[0]
    img, raw = await read_attachment(att)
    if img is None:
        return await ctx.send("Impossible d'ouvrir le fichier.")
    frames = []
    try:
        for frame in ImageSequence.Iterator(img):
            gray = frame.convert("L").convert("RGB")
            frames.append(gray)
    except Exception:
        frames.append(img.convert("L").convert("RGB"))
    gif_bytes = save_frames_to_gif(frames, duration=100)
    await ctx.send(file=discord.File(gif_bytes, filename="bw.gif"))

@BOT.command(name="gifwatermark")
async def cmd_gifwatermark(ctx, *, watermark: str = None):
    """+gifwatermark <texte> : Ajoute un watermark texte sur image/GIF"""
    if watermark is None:
        return await ctx.send("Usage: `+gifwatermark ton_texte` (et join une image/GIF).")
    if not ctx.message.attachments:
        return await ctx.send("Attach un image/GIF pour `+gifwatermark`.")
    att = ctx.message.attachments[0]
    img, raw = await read_attachment(att)
    if img is None:
        return await ctx.send("Impossible d'ouvrir le fichier.")
    frames = []
    try:
        for frame in ImageSequence.Iterator(img):
            base = ensure_rgb(frame.copy())
            draw = ImageDraw.Draw(base)
            try:
                font = ImageFont.truetype("arial.ttf", size=max(12, base.width // 20))
            except Exception:
                font = ImageFont.load_default()
            text_w, text_h = draw.textsize(watermark, font=font)
            draw.text((base.width - text_w - 10, base.height - text_h - 10), watermark, font=font, fill=(255,255,255))
            frames.append(base)
    except Exception:
        base = ensure_rgb(img)
        draw = ImageDraw.Draw(base)
        font = ImageFont.load_default()
        text_w, text_h = draw.textsize(watermark, font=font)
        draw.text((base.width - text_w - 10, base.height - text_h - 10), watermark, font=font, fill=(255,255,255))
        frames.append(base)
    gif_bytes = save_frames_to_gif(frames, duration=100)
    await ctx.send(file=discord.File(gif_bytes, filename="watermark.gif"))

# ---------- Minimal Webserver for Render (keeps service alive) ----------
async def handle(request):
    return web.Response(text="Bot running")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Webserver listening on {port}")

# ---------- Main ----------
async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Erreur: DISCORD_TOKEN introuvable dans les variables d'environnement.")
        return
    ws = asyncio.create_task(start_webserver())
    bot_task = asyncio.create_task(BOT.start(token))
    await asyncio.gather(ws, bot_task)

if __name__ == "__main__":
    asyncio.run(main())
