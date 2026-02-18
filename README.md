# 🎙️ Telegram Whisper Bot

Bot de Telegram que transcribe notas de voz y archivos de audio a texto usando la API Whisper de OpenAI.

## Características

- Transcribe notas de voz de Telegram
- Transcribe archivos de audio (MP3, WAV, M4A, OGG, FLAC, AAC, WEBM)
- Transcribe video notas (mensajes de vídeo circulares)
- Detección automática de idioma
- Mensajes de error descriptivos con soluciones
- Divide transcripciones largas en múltiples mensajes

## Despliegue en Railway (recomendado, gratis)

### Paso 1: Subir a GitHub

```bash
cd telegram-whisper-bot
git init
git add .
git commit -m "Initial commit"
```

Crea un repositorio en https://github.com/new y luego:

```bash
git remote add origin https://github.com/TU_USUARIO/telegram-whisper-bot.git
git branch -M main
git push -u origin main
```

### Paso 2: Desplegar en Railway

1. Ve a **https://railway.app** e inicia sesión con GitHub.
2. Haz clic en **"New Project"** → **"Deploy from GitHub repo"**.
3. Selecciona el repositorio `telegram-whisper-bot`.
4. Una vez creado el servicio, ve a la pestaña **"Variables"** y añade:

| Variable | Valor |
|---|---|
| `TELEGRAM_TOKEN` | Tu token del bot de Telegram |
| `OPENAI_API_KEY` | Tu API key de OpenAI |

5. Railway desplegará automáticamente. ¡Listo!

### Paso 3: Verificar

Abre Telegram, busca tu bot y envíale un audio. Debería responderte con la transcripción.

---

## Ejecución local (alternativa)

### Requisitos
- Python 3.10+

### Instalación

```bash
pip install -r requirements.txt
```

### Configuración

Crea un archivo `.env` en la carpeta del proyecto (este archivo está en `.gitignore`, no se sube a GitHub):

```
TELEGRAM_TOKEN=tu_token_aqui
OPENAI_API_KEY=tu_api_key_aqui
```

### Ejecutar

```bash
# Carga las variables y arranca el bot
export $(cat .env | xargs) && python bot.py
```

## Formatos soportados

MP3, MP4, MPEG, MPGA, M4A, WAV, OGG, FLAC, WEBM, AAC

## Límites

- **Tamaño máximo:** 25 MB por archivo (límite de Whisper)
- **Telegram Bot API:** archivos de hasta 20 MB mediante `getFile`
