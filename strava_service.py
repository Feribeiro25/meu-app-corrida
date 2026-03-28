"""
CORRENDO PELA VIDA — Strava Service
=====================================
Módulo de integração com o Strava.
Fase atual: simulação realista de OAuth + atividade.
Fase futura: OAuth real com client_id/secret do app Strava.

Arquitetura preparada para drop-in real:
  StravaConfig     → credenciais OAuth
  AtividadeStrava  → estrutura de uma atividade
  StravaService    → cliente (simulado agora, real depois)
"""

from __future__ import annotations
import random
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd

CSV_PATH = Path("data/treinos.csv")

# Seed variável para simular dados novos a cada sync
_rng = random.Random()


# ─────────────────────────────────────────────
# Estruturas de dados
# ─────────────────────────────────────────────

@dataclass
class StravaConfig:
    """Credenciais OAuth do Strava (placeholder para fase real)."""
    client_id:     str = ""
    client_secret: str = ""
    access_token:  str = ""
    refresh_token: str = ""
    athlete_id:    int = 0
    athlete_name:  str = ""

    @property
    def autenticado(self) -> bool:
        return bool(self.access_token)


@dataclass
class AtividadeStrava:
    """
    Representa uma atividade importada do Strava.
    Campos espelham a API real do Strava v3.
    """
    id:              int
    nome:            str
    tipo:            str              # "Run", "VirtualRun", etc.
    data:            date
    distancia_m:     float            # metros
    tempo_seg:       int              # segundos totais
    elevation_m:     float            # ganho de elevação
    fc_media:        Optional[int]    # bpm médio
    fc_maxima:       Optional[int]    # bpm máximo
    pse_strava:      Optional[int]    # RPE no app Strava (1–10)
    descricao:       str
    cidade:          str

    @property
    def distancia_km(self) -> float:
        return round(self.distancia_m / 1000.0, 2)

    @property
    def tempo_min(self) -> float:
        return round(self.tempo_seg / 60.0, 1)

    @property
    def pace_min_km(self) -> float:
        if self.distancia_km == 0:
            return 0.0
        return round(self.tempo_min / self.distancia_km, 2)

    @property
    def pace_str(self) -> str:
        p = self.pace_min_km
        m = int(p)
        s = round((p - m) * 60)
        return f"{m}'{s:02d}\"/km"

    @property
    def pse_estimado(self) -> int:
        """Estima PSE a partir do pace relativo ao limiar."""
        if self.pse_strava:
            return self.pse_strava
        # Heurística: pace < 4:30 → PSE 9, > 7:00 → PSE 3
        p = self.pace_min_km
        if p < 4.5:  return 9
        if p < 5.0:  return 8
        if p < 5.5:  return 7
        if p < 6.0:  return 6
        if p < 6.5:  return 5
        if p < 7.0:  return 4
        return 3

    def to_csv_row(self, nivel: str) -> dict:
        return {
            "data":         self.data.isoformat(),
            "distancia_km": self.distancia_km,
            "tempo_min":    self.tempo_min,
            "pse":          self.pse_estimado,
            "dor":          0,
            "local_dor":    "",
            "nivel":        nivel,
            "pace_min_km":  self.pace_min_km,
            "carga":        round(self.distancia_km * self.pse_estimado, 2),
        }


# ─────────────────────────────────────────────
# Gerador de simulação realista
# ─────────────────────────────────────────────

_NOMES_TREINO = [
    "Corrida matinal", "Rodagem leve", "Treino intervalado",
    "Fartlek na pista", "Longão de fim de semana", "Treino de recovery",
    "Corrida no parque", "Treino de tempo run",
]

_CIDADES = ["São Paulo, SP", "Ibirapuera, SP", "Marginal Pinheiros, SP"]


def _gerar_atividade_simulada(
    distancia_alvo_km: float,
    pace_alvo_min_km: float,
    nivel: str,
) -> AtividadeStrava:
    """
    Gera uma atividade simulada realista com:
    - Distância próxima ao alvo (±5%)
    - Pace coerente com o nível e distância
    - FC estimada a partir do pace
    - Variação de elevação e RPE realistas
    """
    _rng.seed(datetime.now().microsecond)

    dist_km  = round(distancia_alvo_km * _rng.uniform(0.93, 1.07), 2)
    dist_m   = dist_km * 1000.0

    # Pace com ruído ±4%
    pace     = round(pace_alvo_min_km * _rng.uniform(0.96, 1.04), 2)
    tempo_s  = int(dist_km * pace * 60)

    # FC estimada: heurística pelo pace (pace rápido → FC alta)
    fc_base  = 185 - int((pace - 4.0) * 10)
    fc_media = max(120, min(185, fc_base + _rng.randint(-8, 8)))
    fc_max   = min(200, fc_media + _rng.randint(8, 20))

    # PSE baseado no pace
    pse = None  # deixa pse_estimado calcular

    # Elevação realista para São Paulo
    elevation = round(_rng.uniform(15, 80), 1)

    return AtividadeStrava(
        id=          _rng.randint(10_000_000, 99_999_999),
        nome=        _rng.choice(_NOMES_TREINO),
        tipo=        "Run",
        data=        date.today(),
        distancia_m= dist_m,
        tempo_seg=   tempo_s,
        elevation_m= elevation,
        fc_media=    fc_media,
        fc_maxima=   fc_max,
        pse_strava=  pse,
        descricao=   "Atividade sincronizada via Strava",
        cidade=      _rng.choice(_CIDADES),
    )


# ─────────────────────────────────────────────
# Serviço principal
# ─────────────────────────────────────────────

class StravaService:
    """
    Cliente Strava.
    Fase 1 (atual): simulação de OAuth + dados.
    Fase 2: substituir _oauth_flow() e _buscar_ultima_atividade()
            por chamadas reais à API v3 do Strava.
    """

    def __init__(self, config: Optional[StravaConfig] = None):
        self.config = config or StravaConfig()
        self.modo_simulacao = True  # False quando OAuth real estiver pronto

    # ── Interface pública ────────────────────

    def sincronizar_ultima_atividade(
        self,
        nivel: str = "Intermediário",
        zonas=None,
    ) -> tuple[AtividadeStrava, str]:
        """
        Busca (ou simula) a última atividade do Strava.
        Retorna (AtividadeStrava, mensagem_status).

        Args:
            nivel:  nível do corredor para calibrar a simulação
            zonas:  ZonasRitmo do perfil para pace mais realista
        """
        if self.modo_simulacao:
            return self._simular_atividade(nivel, zonas)
        else:
            return self._buscar_api_real()  # fase 2

    def salvar_no_csv(self, atividade: AtividadeStrava, nivel: str) -> bool:
        """
        Persiste a atividade no CSV do app.
        Retorna True se salvou, False se já existe (mesmo dia + distância).
        """
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Verifica duplicata (mesmo dia e distância próxima)
        if CSV_PATH.exists():
            df = pd.read_csv(CSV_PATH)
            if not df.empty:
                df["data"] = pd.to_datetime(df["data"]).dt.date
                hoje = date.today()
                mask = (df["data"] == hoje) & \
                       (abs(df["distancia_km"] - atividade.distancia_km) < 0.5)
                if mask.any():
                    return False  # duplicata detectada

        row = pd.DataFrame([atividade.to_csv_row(nivel)])
        colunas = ["data","distancia_km","tempo_min","pse","dor",
                   "local_dor","nivel","pace_min_km","carga"]

        if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
            row.to_csv(CSV_PATH, mode="a", header=False, index=False)
        else:
            row[colunas].to_csv(CSV_PATH, index=False)

        return True

    # ── Simulação ────────────────────────────

    def _simular_atividade(
        self,
        nivel: str,
        zonas,
    ) -> tuple[AtividadeStrava, str]:
        """
        Gera atividade simulada calibrada pelo nível e zonas do perfil.
        """
        # Parâmetros por nível
        params_nivel = {
            "Iniciante":     {"dist_min": 4.0,  "dist_max": 7.0,  "pace_base": 7.0},
            "Intermediário": {"dist_min": 7.0,  "dist_max": 14.0, "pace_base": 5.8},
            "Avançado":      {"dist_min": 10.0, "dist_max": 20.0, "pace_base": 5.0},
        }
        params = params_nivel.get(nivel, params_nivel["Intermediário"])

        dist_km = round(_rng.uniform(params["dist_min"], params["dist_max"]), 1)

        # Usa pace da zona Z2 do perfil se disponível, senão usa base do nível
        if zonas is not None:
            alvo = (zonas.rodagem_leve.pace_min + zonas.rodagem_leve.pace_max) / 2
            # Adiciona variação por tipo de treino simulado
            tipo_sim = _rng.choice(["leve", "moderado", "forte"])
            if tipo_sim == "leve":
                pace_alvo = zonas.recuperacao.pace_min * _rng.uniform(0.97, 1.03)
            elif tipo_sim == "moderado":
                pace_alvo = alvo * _rng.uniform(0.98, 1.02)
            else:
                pace_alvo = zonas.limiar.pace_max * _rng.uniform(0.97, 1.03)
        else:
            pace_alvo = params["pace_base"] * _rng.uniform(0.95, 1.05)

        atividade = _gerar_atividade_simulada(dist_km, pace_alvo, nivel)

        msg = (
            f"✅ Atividade simulada importada com sucesso!\n"
            f"**{atividade.nome}** · {atividade.distancia_km} km · "
            f"{atividade.pace_str} · FC média {atividade.fc_media} bpm\n"
            f"_Modo simulação ativo — conecte sua conta Strava para dados reais._"
        )
        return atividade, msg

    def _buscar_api_real(self) -> tuple[AtividadeStrava, str]:
        """
        FASE 2 — Chamada real à API do Strava.
        Substituir o conteúdo abaixo quando tiver client_id e access_token.

        Endpoint: GET https://www.strava.com/api/v3/athlete/activities?per_page=1
        Headers:  Authorization: Bearer {access_token}
        """
        raise NotImplementedError(
            "API real não configurada. "
            "Configure STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET nas variáveis de ambiente."
        )

    # ── OAuth (placeholder) ──────────────────

    def gerar_url_autorizacao(self) -> str:
        """
        FASE 2 — Gera URL de autorização OAuth do Strava.
        Redirecionar o usuário para esta URL para iniciar o fluxo.
        """
        base = "https://www.strava.com/oauth/authorize"
        params = (
            f"?client_id={self.config.client_id}"
            f"&response_type=code"
            f"&redirect_uri=http://localhost:8501/strava_callback"
            f"&approval_prompt=force"
            f"&scope=activity:read_all"
        )
        return base + params


# ─────────────────────────────────────────────
# Teste
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from perfil_service import PerfilCorredor, calcular_zonas
    p = PerfilCorredor(rp_distancia="5km", rp_tempo_min=22, rp_tempo_seg=30)
    z = calcular_zonas(p)

    svc = StravaService()
    ativ, msg = svc.sincronizar_ultima_atividade("Intermediário", z)
    print(f"Atividade: {ativ.nome}")
    print(f"  Distância: {ativ.distancia_km} km")
    print(f"  Pace: {ativ.pace_str}")
    print(f"  FC: {ativ.fc_media}/{ativ.fc_maxima} bpm")
    print(f"  PSE estimado: {ativ.pse_estimado}/10")
    print(f"  Carga: {ativ.distancia_km * ativ.pse_estimado:.1f} u.a.")
    print()
    print(msg)
