"""
CORRENDO PELA VIDA — Gamificação
==================================
Sistema de níveis de atleta, badges e métricas de consistência.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
import pandas as pd


# ─────────────────────────────────────────────
# Nível de Atleta
# ─────────────────────────────────────────────

@dataclass
class NivelAtleta:
    nome:          str
    emoji:         str
    cor:           str          # hex
    cor_bg:        str          # hex fundo
    min_semanas:   int          # semanas seguras para atingir
    descricao:     str
    proxima_meta:  str


NIVEIS = [
    NivelAtleta("Bronze",    "🥉", "#cd7f32", "#1a1208",  0,
                "Construindo consistência", "4 semanas seguras → Prata"),
    NivelAtleta("Prata",     "🥈", "#c0c0c0", "#14141a",  4,
                "Ritmo regular estabelecido", "8 semanas seguras → Ouro"),
    NivelAtleta("Ouro",      "🥇", "#ffd700", "#1a1800",  8,
                "Atleta consistente", "12 semanas seguras → Platina"),
    NivelAtleta("Platina",   "💎", "#e5e4e2", "#131318", 12,
                "Elite de consistência", "20 semanas seguras → Diamante"),
    NivelAtleta("Diamante",  "💠", "#b9f2ff", "#0a1a1f", 20,
                "Atleta de alto rendimento", "Você chegou ao topo!"),
]


def nivel_atual(semanas_seguras: int) -> NivelAtleta:
    atual = NIVEIS[0]
    for n in NIVEIS:
        if semanas_seguras >= n.min_semanas:
            atual = n
    return atual


# ─────────────────────────────────────────────
# Badge
# ─────────────────────────────────────────────

@dataclass
class Badge:
    id:       str
    emoji:    str
    nome:     str
    descricao: str
    desbloqueado: bool = False
    data:     Optional[date] = None


def avaliar_badges(
    df: pd.DataFrame,
    streak: int,
    semanas_seguras: int,
    total_km: float,
    acwr_atual: float,
) -> list[Badge]:
    """Retorna lista de todos os badges com status de desbloqueio."""
    badges_config = [
        # Consistência
        ("first_run",      "👟", "Primeira corrida",    "Registrou o primeiro treino",
         len(df) >= 1),
        ("week_warrior",   "📅", "Guerreiro semanal",   "7 dias de streak",
         streak >= 7),
        ("month_strong",   "🗓️", "Mês forte",           "30 dias de streak",
         streak >= 30),
        ("safe_zone_4w",   "🛡️", "4 semanas seguras",   "4 semanas consecutivas sem alerta vermelho",
         semanas_seguras >= 4),
        ("safe_zone_8w",   "🏰", "Fortaleza",           "8 semanas consecutivas sem alerta vermelho",
         semanas_seguras >= 8),
        # Volume
        ("km_50",          "🏅", "50 km",               "50 km acumulados",
         total_km >= 50),
        ("km_100",         "💯", "100 km",              "100 km acumulados",
         total_km >= 100),
        ("km_500",         "🚀", "500 km",              "500 km acumulados",
         total_km >= 500),
        ("km_1000",        "⭐", "1.000 km",            "1.000 km acumulados",
         total_km >= 1000),
        # Controle de carga
        ("acwr_master",    "📊", "Mestre da carga",     "ACWR na zona ótima por 2 semanas",
         semanas_seguras >= 2 and 0.8 <= acwr_atual <= 1.3),
        ("no_pain_4w",     "💪", "Sem dor por 4 semanas","4 semanas sem relato de dor",
         _semanas_sem_dor(df) >= 4),
        # Volume semanal
        ("weekly_40",      "🔥", "40 km numa semana",   "Treinou 40+ km em uma semana",
         _max_km_semanal(df) >= 40),
        ("weekly_60",      "⚡", "60 km numa semana",   "Treinou 60+ km em uma semana",
         _max_km_semanal(df) >= 60),
    ]

    result = []
    for bid, emoji, nome, desc, cond in badges_config:
        b = Badge(id=bid, emoji=emoji, nome=nome, descricao=desc, desbloqueado=bool(cond))
        if b.desbloqueado:
            b.data = date.today()
        result.append(b)
    return result


def _semanas_sem_dor(df: pd.DataFrame) -> int:
    if df.empty or "dor" not in df.columns:
        return 0
    df2 = df.copy()
    df2["data"] = pd.to_datetime(df2["data"])
    df2 = df2.sort_values("data", ascending=False)
    hoje = date.today()
    semanas = 0
    for i in range(12):
        ini = hoje - timedelta(days=(i+1)*7)
        fim = hoje - timedelta(days=i*7)
        mask = (df2["data"].dt.date >= ini) & (df2["data"].dt.date < fim)
        semana_df = df2[mask]
        if not semana_df.empty and semana_df["dor"].max() == 0:
            semanas += 1
        elif not semana_df.empty:
            break
    return semanas


def _max_km_semanal(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    df2 = df.copy()
    df2["data"] = pd.to_datetime(df2["data"])
    df2["semana"] = df2["data"].dt.to_period("W")
    return float(df2.groupby("semana")["distancia_km"].sum().max())


# ─────────────────────────────────────────────
# Métricas de consistência
# ─────────────────────────────────────────────

def calcular_semanas_seguras(df: pd.DataFrame, serie_acwr: pd.DataFrame) -> int:
    """
    Conta semanas consecutivas (a partir da mais recente) sem ACWR > 1.5.
    Uma semana 'segura' = nenhum dia da semana com ACWR > 1.5.
    """
    if serie_acwr.empty:
        return 0
    hoje = date.today()
    semanas = 0
    for i in range(24):
        ini = hoje - timedelta(days=(i+1)*7)
        fim = hoje - timedelta(days=i*7)
        mask = (pd.to_datetime(serie_acwr["data"]).dt.date >= ini) & \
               (pd.to_datetime(serie_acwr["data"]).dt.date < fim)
        s = serie_acwr[mask]
        if s.empty:
            if i == 0:
                continue
            break
        max_acwr = s["acwr"].dropna().max() if not s["acwr"].dropna().empty else 0.0
        if max_acwr <= 1.5:
            semanas += 1
        else:
            break
    return semanas


def calcular_pct_zona_otima(serie_acwr: pd.DataFrame) -> float:
    """% de dias nos últimos 28d que o ACWR estava na zona ótima (0.8–1.3)."""
    if serie_acwr.empty:
        return 0.0
    ultimos = serie_acwr.tail(28)
    acwr_vals = ultimos["acwr"].dropna()
    if len(acwr_vals) == 0:
        return 0.0
    otima = ((acwr_vals >= 0.8) & (acwr_vals <= 1.3)).sum()
    return round(otima / len(acwr_vals) * 100, 1)
