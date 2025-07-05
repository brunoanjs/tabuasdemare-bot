@echo off
cd /d %~dp0

echo [✓] Ativando ambiente virtual...
if not exist venv (
    echo [✓] Criando ambiente virtual...
    python -m venv venv
)
call venv\Scripts\activate

echo [✓] Instalando dependências...
pip install -r requisitos.txt

echo [✓] Iniciando o bot...
python bot.py

pause