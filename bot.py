import os
import logging
import tempfile
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ── Configuración ──────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise SystemExit(
        "❌ Faltan variables de entorno obligatorias.\n"
        "   Configura TELEGRAM_TOKEN y OPENAI_API_KEY antes de ejecutar el bot.\n"
        "   En local: export TELEGRAM_TOKEN=tu_token && export OPENAI_API_KEY=tu_key\n"
        "   En Railway: añádelas en la pestaña Variables del servicio."
    )

WHISPER_MODEL = "whisper-1"
MAX_FILE_SIZE_MB = 25
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ *Bot de Transcripción de Audio*\n\n"
        "Envíame una nota de voz o un archivo de audio (MP3, M4A, WAV, OGG…) "
        "y te devolveré la transcripción en texto usando Whisper de OpenAI.\n\n"
        "📌 *Límite:* 25 MB por archivo.\n"
        "🌐 *Idioma:* Detección automática.",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Ayuda*\n\n"
        "• Envía una *nota de voz* directamente.\n"
        "• Envía un *archivo de audio* (MP3, WAV, M4A, OGG, FLAC, WEBM).\n"
        "• Recibirás un mensaje de \"Procesando...\" y luego la transcripción.\n\n"
        "Si algo falla, recibirás el error detallado con pistas para solucionarlo.",
        parse_mode="Markdown",
    )


def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
        )
    return transcript.text.strip()


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.voice:
        file_obj = message.voice
        file_name = "voice.ogg"
        file_size = file_obj.file_size
    elif message.audio:
        file_obj = message.audio
        file_name = message.audio.file_name or "audio.mp3"
        file_size = file_obj.file_size
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("audio/"):
        file_obj = message.document
        file_name = message.document.file_name or "audio.bin"
        file_size = file_obj.file_size
    elif message.video_note:
        file_obj = message.video_note
        file_name = "video_note.mp4"
        file_size = file_obj.file_size
    else:
        return

    if file_size and file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.reply_text(
            f"⚠️ El archivo supera el límite de {MAX_FILE_SIZE_MB} MB permitido por Whisper.\n"
            f"Tamaño recibido: {file_size / (1024*1024):.1f} MB."
        )
        return

    processing_msg = await message.reply_text("⏳ *Procesando audio…*", parse_mode="Markdown")

    tmp_path = None
    try:
        tg_file = await file_obj.get_file()
        with tempfile.NamedTemporaryFile(suffix=f"_{file_name}", delete=False) as tmp:
            tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)

        text = transcribe_audio(tmp_path)

        if not text:
            await processing_msg.edit_text("⚠️ La transcripción está vacía. El audio podría no contener voz reconocible.")
            return

        MAX_MSG_LEN = 4000
        if len(text) <= MAX_MSG_LEN:
            await message.reply_text(text)
        else:
            parts = [text[i:i + MAX_MSG_LEN] for i in range(0, len(text), MAX_MSG_LEN)]
            for idx, part in enumerate(parts, 1):
                await message.reply_text(part)

        await processing_msg.delete()

    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}", exc_info=True)
        error_text = str(e)

        help_hint = ""
        if "401" in error_text or "Incorrect API key" in error_text:
            help_hint = (
                "\n\n🔎 *Posible causa:* API key de OpenAI inválida o expirada.\n"
                "💡 *Solución:* Verifica tu clave en https://platform.openai.com/api-keys"
            )
        elif "429" in error_text or "rate limit" in error_text.lower():
            help_hint = (
                "\n\n🔎 *Posible causa:* Has superado el límite de uso de la API.\n"
                "💡 *Solución:* Espera unos minutos o revisa tu plan en https://platform.openai.com/usage"
            )
        elif "413" in error_text or "too large" in error_text.lower():
            help_hint = (
                "\n\n🔎 *Posible causa:* El archivo es demasiado grande para Whisper (máx. 25 MB).\n"
                "💡 *Solución:* Comprime el audio o divídelo en partes más cortas."
            )
        elif "insufficient_quota" in error_text.lower():
            help_hint = (
                "\n\n🔎 *Posible causa:* No tienes créditos suficientes en OpenAI.\n"
                "💡 *Solución:* Añade saldo en https://platform.openai.com/settings/organization/billing/overview"
            )
        elif "timeout" in error_text.lower() or "timed out" in error_text.lower():
            help_hint = (
                "\n\n🔎 *Posible causa:* El audio es muy largo y la API tardó demasiado.\n"
                "💡 *Solución:* Intenta con un audio más corto (< 10 min recomendado)."
            )
        else:
            help_hint = (
                "\n\n🔎 *Para investigar:* Busca el error en Google con:\n"
                f"`OpenAI Whisper API {error_text[:80]}`"
            )

        await processing_msg.edit_text(
            f"❌ *Error al transcribir:*\n\n`{error_text[:500]}`{help_hint}",
            parse_mode="Markdown",
        )

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ Envíame una *nota de voz* o un *archivo de audio* para transcribirlo.",
        parse_mode="Markdown",
    )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(
        filters.Document.MimeType("audio/mpeg") |
        filters.Document.MimeType("audio/mp4") |
        filters.Document.MimeType("audio/ogg") |
        filters.Document.MimeType("audio/wav") |
        filters.Document.MimeType("audio/x-wav") |
        filters.Document.MimeType("audio/flac") |
        filters.Document.MimeType("audio/webm") |
        filters.Document.MimeType("audio/x-m4a") |
        filters.Document.MimeType("audio/aac") |
        filters.Document.MimeType("video/mp4"),
        handle_audio
    ))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    logger.info("🚀 Bot iniciado. Esperando mensajes...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
