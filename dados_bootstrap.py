"""
CORRENDO PELA VIDA — Gerador de Dados Iniciais
================================================
Simula 28 dias de historico realista com evolucao gradual de carga.
Meta: ACWR final ~1.35 (zona de atencao) com tendencia visivel de subida.
"""

from __future__ import annotations
import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

CSV_PATH = Path("data/treinos.csv")
CSV_COLUNAS = [
    "data", "distancia_km", "tempo_min", "pse",
    "dor", "local_dor", "nivel", "pace_min_km", "carga",
]

random.seed(42)


def _pace(dist_km: float, pse: int) -> float:
    base = 6.5
    ajuste = (pse - 5) * 0.22
    ruido = random.uniform(-0.12, 0.12)
    return round(max(3.8, base - ajuste + ruido), 2)


def _tempo(dist_km: float, pace: float) -> int:
    return max(10, round(dist_km * pace))


def _plano_28_dias() -> list[tuple]:
    """
    28 dias calibrados para ACWR final ~1.35 (zona de atencao visivel).

    Base cronica solida (~252 u.a./semana) construida ao longo das 4 semanas.
    Semana 1 recente tem 3 dias de PSE alta => Carga aguda ~340 u.a.
    ACWR = 340 / 252 ~ 1.35

    (dist_km, pse, dor, local_dor) | 0,0 = descanso
    """
    D = (0, 0, 0, "")
    return [
        # Semana 4 — base (28..22 dias atras)
        # Carga alvo: ~178 u.a.
        D,
        (8,  5, 0, ""),   # 40
        D,
        (7,  5, 0, ""),   # 35
        D,
        (9,  5, 0, ""),   # 45
        (12, 5, 0, ""),   # 60  => 180

        # Semana 3 — construcao (21..15 dias atras)
        # Carga alvo: ~228 u.a.
        D,
        (8,  5, 0, ""),   # 40
        (9,  6, 0, ""),   # 54
        D,
        (8,  5, 0, ""),   # 40
        D,
        (12, 5, 0, ""),   # 60
        (7,  5, 0, ""),   # 35  => 229

        # Semana 2 — desenvolvimento (14..8 dias atras)
        # Carga alvo: ~255 u.a.
        D,
        (9,  6, 0, ""),   # 54
        D,
        (8,  6, 0, ""),   # 48
        (9,  7, 0, ""),   # 63
        (14, 5, 0, ""),   # 70
        (6,  4, 0, ""),   # 24  => 259

        # Semana 1 — pico recente (7..1 dias atras)
        # 3 dias PSE 8 => carga aguda alta => ACWR ~1.35
        D,
        (10, 8, 0, ""),                      # 80 — treino forte
        (8,  6, 1, "panturrilha esquerda"),  # 48 — dor leve
        (12, 8, 0, ""),                      # 96 — outro treino forte
        (6,  4, 0, ""),                      # 24 — leve
        (16, 6, 0, ""),                      # 96 — longao moderado
        D,                                   # => 344
    ]


def popular_dados_iniciais(nivel: str = "Intermediario", forcar: bool = False) -> dict:
    """
    Popula o CSV com 28 dias de historico simulado.

    Args:
        nivel:  nivel do corredor salvo em cada registro
        forcar: se True, apaga dados existentes e recria

    Returns:
        dict com estatisticas e ACWR calculado
    """
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CSV_PATH.exists():
        df_check = pd.read_csv(CSV_PATH)
        if not df_check.empty and not forcar:
            return {
                "status": "ja_existe",
                "registros": len(df_check),
                "mensagem": "CSV ja possui dados. Use forcar=True para sobrescrever.",
            }

    plano = _plano_28_dias()
    hoje  = date.today()
    inicio = hoje - timedelta(days=27)

    registros = []
    for i, (dist, pse, dor, local_dor) in enumerate(plano):
        dia = inicio + timedelta(days=i)
        if dist == 0 or pse == 0:
            continue
        dist_f = round(dist * random.uniform(0.96, 1.04), 1)
        pace   = _pace(dist_f, pse)
        tempo  = _tempo(dist_f, pace)
        carga  = round(dist_f * pse, 2)
        registros.append({
            "data":         dia.isoformat(),
            "distancia_km": dist_f,
            "tempo_min":    tempo,
            "pse":          pse,
            "dor":          dor,
            "local_dor":    local_dor,
            "nivel":        nivel,
            "pace_min_km":  pace,
            "carga":        carga,
        })

    df = pd.DataFrame(registros, columns=CSV_COLUNAS)
    df.to_csv(CSV_PATH, index=False)

    # Calculo do ACWR final via rolling window
    df["data"] = pd.to_datetime(df["data"])
    df_d = df.set_index("data").resample("D")["carga"].sum().reset_index()
    df_d["aguda"]   = df_d["carga"].rolling(7,  min_periods=1).sum()
    df_d["cronica"] = df_d["carga"].rolling(28, min_periods=1).sum() / 4
    last = df_d.iloc[-1]
    acwr_final = round(last["aguda"] / last["cronica"], 3) if last["cronica"] > 0 else 1.0

    return {
        "status":     "gerado",
        "registros":  len(registros),
        "total_km":   round(df["distancia_km"].sum(), 1),
        "media_pse":  round(df["pse"].mean(), 1),
        "acwr_final": acwr_final,
        "carga_aguda":  round(float(last["aguda"]), 1),
        "carga_cronica": round(float(last["cronica"]), 1),
        "mensagem":   f"{len(registros)} sessoes geradas em 28 dias. ACWR: {acwr_final:.3f}",
    }


def calcular_serie_acwr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe o DataFrame do CSV e retorna serie temporal de ACWR,
    Carga Aguda e Carga Cronica para cada dia.
    Usado pelo grafico de tendencia no app.
    """
    if df.empty:
        return pd.DataFrame(columns=["data", "aguda", "cronica", "acwr"])

    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    df_d = df.set_index("data").resample("D")["carga"].sum().reset_index()
    df_d["aguda"]   = df_d["carga"].rolling(7,  min_periods=1).sum()
    df_d["cronica"] = df_d["carga"].rolling(28, min_periods=1).sum() / 4
    df_d["cronica"] = df_d["cronica"].replace(0, float("nan"))
    df_d["acwr"]    = (df_d["aguda"] / df_d["cronica"]).round(3)
    return df_d[["data", "aguda", "cronica", "acwr"]]


if __name__ == "__main__":
    import os
    # limpa para testar do zero
    if os.path.exists("data/treinos.csv"):
        os.remove("data/treinos.csv")
    r = popular_dados_iniciais(forcar=True)
    print(r)

    serie = calcular_serie_acwr(pd.read_csv("data/treinos.csv"))
    print("\nTendencia ACWR (ultimos 14 dias):")
    print(serie[["data", "aguda", "cronica", "acwr"]].tail(14).to_string(index=False))
