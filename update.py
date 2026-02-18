import requests
import json
from datetime import datetime

# ===== CONFIG =====
OUTPUT_FILE = "gex_qqq.json"

# ===== FUNÇÃO SIMULANDO COLETA GEX =====
# (Depois podemos trocar por API real)
def coletar_gex():

    # Aqui você pode futuramente puxar API real
    dados = {
        "QQQ Put Wall": 600.0,
        "QQQ Call Wall": 630.0,
        "QQQ Gamma Flip": 174.78,
        "QQQ Max Gamma": 640.0,
        "QQQ Min Gamma": 600.0,
        "QQQ Max IV": 184.78,
        "QQQ Min IV": 676.0,
        "Atualizado": str(datetime.now())
    }

    return dados

# ===== SALVAR JSON =====
def salvar_json(dados):

    with open(OUTPUT_FILE, "w") as f:
        json.dump(dados, f, indent=2)

# ===== EXECUÇÃO =====
if __name__ == "__main__":

    dados = coletar_gex()
    salvar_json(dados)

    print("GEX atualizado com sucesso!")
