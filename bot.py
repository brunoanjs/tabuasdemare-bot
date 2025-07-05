from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN
from utils import (
    get_coordinates, consultar_mare, gerar_grafico_com_imagem_de_fundo,
    salvar_historico, pegar_historico,
    salvar_alerta, verificar_alerta_automatico,
    consultar_clima
)
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import os
from datetime import datetime
import traceback

keyboard = [
    ["Salvador", "Recife", "Fortaleza"],
    ["Natal", "Rio de Janeiro", "Florianópolis"],
    [KeyboardButton("📍 Enviar minha localização", request_location=True)]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "🌊 *Bot de Marés e Clima do Brasil*\n\n"
        "Use os seguintes comandos para interagir:\n\n"
        "- *Consultar Maré e Clima por Cidade*: Digite o nome da cidade (ex: Salvador).\n"
        "- *Consultar Maré por Data Específica*: Ex: Recife 2025-07-05.\n"
        "- *Consultar por Localização Atual*: Use o botão 📍 *Enviar minha localização* abaixo.\n\n"
        "*Comandos adicionais:*\n"
        "- /historico — Ver seu histórico de consultas\n"
        "- /alerta cidade limite — Ex: /alerta salvador 0.6\n"
    )
    await update.message.reply_text(mensagem, parse_mode='Markdown', reply_markup=markup)

async def consulta_cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if texto.lower() in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]:
        await start(update, context)
        return

    partes = texto.split()
    if len(partes) == 2:
        try:
            lat = float(partes[0])
            lon = float(partes[1])
            cidade = f"Lat {lat}, Lon {lon}"
        except ValueError:
            lat, lon = get_coordinates(texto)
            cidade = texto
            data = None
    else:
        cidade = " ".join(partes[:-1]) if len(partes) > 1 and partes[-1].count("-") == 2 else texto
        data = partes[-1] if cidade != texto else None
        lat, lon = get_coordinates(cidade)

    if lat is None:
        await update.message.reply_text("Cidade ou coordenadas não encontradas.")
        return

    data_consulta = datetime.strptime(data, "%Y-%m-%d") if 'data' in locals() and data else None

    try:
        resposta_mare, horas, alturas = consultar_mare(lat, lon, data_consulta)
    except ValueError as e:
        await update.message.reply_text(f"⚠️ Erro ao consultar maré: {e}")
        return
    except Exception as e:
        erro_detalhado = traceback.format_exc()
        print(erro_detalhado)
        await update.message.reply_text(f"⚠️ Erro inesperado ao consultar a maré:\n`{str(e)}`", parse_mode="Markdown")
        return

    resposta_clima = consultar_clima(lat, lon)

    local = cidade.title()
    texto_resposta = (
        f"🌊 *Maré para {local}*:\n\n"
        + "\n".join(resposta_mare)
        + "\n\n☀️ *Clima Atual*:\n"
        + resposta_clima
    )
    await update.message.reply_text(texto_resposta, parse_mode="Markdown")

    caminho_imagem = r"C:\\Users\Bruno\\OneDrive\\Área de Trabalho\\@tabuasmare_bot\\imagens\\sand_and_sea.jpg"

    try:
        grafico_path = gerar_grafico_com_imagem_de_fundo(horas, alturas, local.replace(" ", "_"), caminho_imagem)
        if os.path.exists(grafico_path):
            with open(grafico_path, "rb") as f:
                await update.message.reply_photo(photo=f)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Erro ao gerar gráfico: {e}")

    salvar_historico(update.effective_user.id, cidade)

async def receber_localizacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude

        try:
            resposta_mare, horas, alturas = consultar_mare(lat, lon)
        except ValueError as e:
            await update.message.reply_text(f"⚠️ Erro ao consultar maré: {e}")
            return
        except Exception as e:
            erro_detalhado = traceback.format_exc()
            print(erro_detalhado)
            await update.message.reply_text(f"⚠️ Erro inesperado ao consultar a maré:\n`{str(e)}`", parse_mode="Markdown")
            return

        resposta_clima = consultar_clima(lat, lon)

        texto_resposta = (
            f"🌊 *Maré para sua localização*:\n\n"
            + "\n".join(resposta_mare)
            + "\n\n☀️ *Clima Atual*:\n"
            + resposta_clima
        )
        await update.message.reply_text(texto_resposta, parse_mode="Markdown")

        caminho_imagem = r"C:\\Users\Bruno\\OneDrive\\Área de Trabalho\\@tabuasmare_bot\\imagens\\sand_and_sea.jpg"
        local = f"Lat_{lat:.2f}_Lon_{lon:.2f}"

        try:
            grafico_path = gerar_grafico_com_imagem_de_fundo(horas, alturas, local, caminho_imagem)
            if os.path.exists(grafico_path):
                with open(grafico_path, "rb") as f:
                    await update.message.reply_photo(photo=f)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Erro ao gerar gráfico: {e}")
    else:
        await update.message.reply_text("Por favor, envie sua localização para consulta.")

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    historico = pegar_historico(update.effective_user.id)
    if not historico:
        await update.message.reply_text("Nenhuma consulta realizada ainda.")
    else:
        texto = "\n".join(f"- {cidade.title()}" for cidade in historico)
        await update.message.reply_text(f"📜 Histórico de consultas:\n{texto}")

async def alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /alerta cidade limite\nExemplo: /alerta salvador 0.6")
        return
    cidade = " ".join(context.args[:-1])
    try:
        limite = float(context.args[-1])
    except ValueError:
        await update.message.reply_text("O limite precisa ser um número. Ex: 0.5")
        return
    salvar_alerta(update.effective_user.id, cidade, limite)
    await update.message.reply_text(f"🔔 Alerta configurado para *{cidade.title()}* abaixo de *{limite}m*", parse_mode="Markdown")

async def verificar_todos_alertas(app):
    from telegram import Bot
    bot = Bot(token=TELEGRAM_TOKEN)
    from utils import user_alerts
    for user_id, alerta in user_alerts.items():
        lat, lon = get_coordinates(alerta['cidade'])
        if lat and lon:
            resposta_mare, horas, alturas = consultar_mare(lat, lon)
            if resposta_mare:
                mare_atual = float(resposta_mare[0].split()[1])
                if mare_atual < alerta['limite']:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 *Alerta de Maré* para {alerta['cidade']}! A maré atual é {mare_atual}m, abaixo do limite configurado de {alerta['limite']}m.",
                        parse_mode="Markdown"
                    )

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("historico", historico))
    app.add_handler(CommandHandler("alerta", alerta))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), consulta_cidade))
    app.add_handler(MessageHandler(filters.LOCATION, receber_localizacao))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.create_task(verificar_todos_alertas(app)), 'interval', minutes=10)
    scheduler.start()

    print("Bot rodando com sucesso. Aguardando mensagens...")
    app.run_polling()

if __name__ == "__main__":
    main()

