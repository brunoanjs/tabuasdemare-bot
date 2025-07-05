import requests
import matplotlib.pyplot as plt
import numpy as np
import datetime
import matplotlib.image as mpimg
from config import WORLD_TIDES_API_KEY, OPENWEATHER_API_KEY

user_history = {}
user_alerts = {}

def get_coordinates(cidade):
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={cidade}"
        response = requests.get(url, headers={"User-Agent": "mare-bot"})
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        return None, None

def consultar_mare(lat, lon, data=None):
    if data is None:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.combine(data, datetime.datetime.min.time())

    timestamp = int(now.timestamp())
    url = (
        f"https://www.worldtides.info/api/v2?heights&extremes"
        f"&lat={lat}&lon={lon}&start={timestamp}&length=43200"
        f"&key={WORLD_TIDES_API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    # Verificação de erros
    if "error" in data:
        raise ValueError(f"Erro da API WorldTides: {data['error']}")

    if "heights" not in data or "extremes" not in data:
        raise ValueError("Dados de maré incompletos retornados pela API.")

    alturas = [h["height"] for h in data["heights"]]
    horas = [datetime.datetime.fromtimestamp(h["dt"]).strftime("%H:%M") for h in data["heights"]]
    resposta = [
        f"{datetime.datetime.fromtimestamp(e['dt']).strftime('%H:%M')} - {e['type']} ({e['height']:.2f}m)"
        for e in data["extremes"]
    ]

    return resposta, horas, alturas


def gerar_grafico_com_imagem_de_fundo(horas, alturas, local, caminho_imagem):
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    import os

    if not os.path.exists(caminho_imagem):
        raise FileNotFoundError(f"Imagem de fundo não encontrada: {caminho_imagem}")

    img = mpimg.imread(caminho_imagem)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(img, extent=[0, len(horas)-1, min(alturas)-0.5, max(alturas)+0.5], aspect='auto')
    ax.plot(range(len(horas)), alturas, color='blue', marker='o', label='Altura da Maré')

    ax.set_title(f'Previsão da Maré - {local}', fontsize=14)
    ax.set_xlabel('Horário', fontsize=12)
    ax.set_ylabel('Altura (m)', fontsize=12)
    ax.set_xticks(range(len(horas)))
    ax.set_xticklabels(horas, rotation=45, ha='right')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend()

    # Maré máxima
    max_mare = max(alturas)
    idx_max = alturas.index(max_mare)
    ax.annotate(f"Maré Alta ({max_mare:.2f}m)", xy=(idx_max, max_mare),
                xytext=(idx_max + 0.5, max_mare + 0.2),
                arrowprops=dict(arrowstyle="->", color='red'),
                fontsize=10, color='red')

    # Maré mínima
    min_mare = min(alturas)
    idx_min = alturas.index(min_mare)
    ax.annotate(f"Maré Baixa ({min_mare:.2f}m)", xy=(idx_min, min_mare),
                xytext=(idx_min + 0.5, min_mare - 0.2),
                arrowprops=dict(arrowstyle="->", color='green'),
                fontsize=10, color='green')

    nome_arquivo = f"grafico_mare_{local.replace(' ', '_')}.png"
    caminho_saida = os.path.join("graficos", nome_arquivo)
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=300)
    plt.close(fig)

    return caminho_saida

def salvar_historico(user_id, cidade):
    if user_id not in user_history:
        user_history[user_id] = []
    if cidade not in user_history[user_id]:
        user_history[user_id].append(cidade)

def pegar_historico(user_id):
    return user_history.get(user_id, [])

def salvar_alerta(user_id, cidade, limite):
    user_alerts[user_id] = (cidade, limite)

def verificar_alerta_automatico(user_id):
    if user_id in user_alerts:
        cidade, limite = user_alerts[user_id]
        lat, lon = get_coordinates(cidade)
        if lat is None:
            return None
        _, _, alturas = consultar_mare(lat, lon)
        if any(altura <= limite for altura in alturas):
            return f"⚠️ Alerta: Maré abaixo de {limite}m em {cidade.title()}!"
    return None

def consultar_clima(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    response = requests.get(url)
    data = response.json()

    descricao = data['weather'][0]['description'].capitalize()
    temperatura = data['main']['temp']
    sensacao = data['main']['feels_like']
    umidade = data['main']['humidity']

    texto = (
        f"Descrição: {descricao}\n"
        f"Temperatura: {temperatura}°C\n"
        f"Sensação Térmica: {sensacao}°C\n"
        f"Umidade: {umidade}%"
    )
    return texto
