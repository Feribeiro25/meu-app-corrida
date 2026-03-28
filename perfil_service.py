"""
CORRENDO PELA VIDA — Serviço de Perfil e Zonas de Ritmo
=========================================================
Calcula zonas de treino a partir do Recorde Pessoal usando
a metodologia de Jack Daniels (VDOT / Running Formula).

Formula VDOT (Daniels & Gilbert, 1979):
  VO2 = -4.6 + 0.182258*(d/t) + 0.000104*(d/t)^2
  %VO2max = 0.8 + 0.1894393*e^(-0.012778*t) + 0.2989558*e^(-0.1932605*t)
  VDOT = VO2 / %VO2max

Zonas de ritmo (% da velocidade no VO2max):
  Z1 Recuperação   59–74%  vVO2max
  Z2 Rodagem leve  74–84%  vVO2max
  Z3 Longão        74–84%  vVO2max  (mesma faixa, percepção diferente)
  Z4 Limiar        83–88%  vVO2max
  Z5 Intervalado   95–100% vVO2max
  Z6 Repetições   105–112% vVO2max
"""

from __future__ import annotations
import json
import math
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

PERFIL_PATH = Path("data/perfil.json")


# ─────────────────────────────────────────────
# Dataclasses de ritmo e perfil
# ─────────────────────────────────────────────

@dataclass
class PaceZona:
    """Representa uma zona com ritmo mínimo e máximo."""
    nome:        str
    zona_hr:     str            # ex: "Z2"
    descricao:   str
    pace_min:    float          # min/km (mais lento)
    pace_max:    float          # min/km (mais rápido)
    pse_ref:     str            # ex: "4–5"
    cor:         str            # hex para UI

    @property
    def pace_min_str(self) -> str:
        return _fmt_pace(self.pace_min)

    @property
    def pace_max_str(self) -> str:
        return _fmt_pace(self.pace_max)

    @property
    def faixa_str(self) -> str:
        return f"{self.pace_max_str} – {self.pace_min_str}/km"

    @property
    def alvo_str(self) -> str:
        """Pace alvo central da zona."""
        alvo = (self.pace_min + self.pace_max) / 2
        return f"{_fmt_pace(alvo)}/km"


@dataclass
class ZonasRitmo:
    """Conjunto completo de zonas calculadas a partir do VDOT."""
    vdot:          float
    fonte_rp:      str          # ex: "5km em 22:30"
    recuperacao:   PaceZona
    rodagem_leve:  PaceZona
    longao:        PaceZona
    limiar:        PaceZona
    intervalado:   PaceZona
    repeticao:     PaceZona

    def zona_por_tipo(self, tipo_treino_value: str) -> Optional[PaceZona]:
        """Retorna a zona mais relevante para o tipo de treino."""
        mapa = {
            "recuperacao":          self.recuperacao,
            "rodagem_leve":         self.rodagem_leve,
            "rodagem_moderada":     self.rodagem_leve,
            "rodagem_pesada":       self.limiar,
            "progressivo_curto":    self.rodagem_leve,
            "progressivo_longo":    self.limiar,
            "tempo_run":            self.limiar,
            "fartlek_livre":        self.rodagem_leve,
            "fartlek_estruturado":  self.intervalado,
            "intervalado_curto":    self.intervalado,
            "intervalado_longo":    self.intervalado,
            "hill_repeats":         self.intervalado,
            "strides":              self.repeticao,
            "longao_leve":          self.longao,
            "longao_progressivo":   self.longao,
            "longao_especial":      self.longao,
            "descanso_ativo":       None,
            "mobilidade":           None,
        }
        return mapa.get(tipo_treino_value)

    def to_dict(self) -> dict:
        return {
            "vdot": self.vdot,
            "fonte_rp": self.fonte_rp,
            "recuperacao": asdict(self.recuperacao),
            "rodagem_leve": asdict(self.rodagem_leve),
            "longao": asdict(self.longao),
            "limiar": asdict(self.limiar),
            "intervalado": asdict(self.intervalado),
            "repeticao": asdict(self.repeticao),
        }


@dataclass
class PerfilCorredor:
    """Perfil completo do atleta, persistido em JSON."""
    nome:              str = "Corredor"
    nivel:             str = "Intermediário"
    rp_distancia:      str = "5km"          # "5km" ou "10km"
    rp_tempo_min:      int = 0              # minutos
    rp_tempo_seg:      int = 0              # segundos
    peso_kg:           float = 70.0
    fc_max:            int = 185
    data_nascimento:   str = ""
    objetivo_prova:    str = ""             # ex: "São Silvestre 2025"
    objetivo_tempo:    str = ""             # ex: "50:00 nos 10km"

    @property
    def rp_total_seg(self) -> int:
        return self.rp_tempo_min * 60 + self.rp_tempo_seg

    @property
    def rp_total_min(self) -> float:
        return self.rp_total_seg / 60.0

    @property
    def rp_dist_m(self) -> float:
        return 5000.0 if self.rp_distancia == "5km" else 10000.0

    @property
    def tem_rp(self) -> bool:
        return self.rp_total_seg > 0

    @property
    def rp_str(self) -> str:
        if not self.tem_rp:
            return "—"
        m, s = divmod(self.rp_total_seg, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h{m:02d}'{s:02d}\""
        return f"{m}'{s:02d}\""

    @property
    def pace_rp_str(self) -> str:
        """Pace do RP em min/km."""
        if not self.tem_rp:
            return "—"
        km = self.rp_dist_m / 1000.0
        pace = self.rp_total_min / km
        return f"{_fmt_pace(pace)}/km"


# ─────────────────────────────────────────────
# Helpers de formatação
# ─────────────────────────────────────────────

def _fmt_pace(pace_min_km: float) -> str:
    """Converte float min/km → 'M:SS'."""
    m = int(pace_min_km)
    s = round((pace_min_km - m) * 60)
    if s == 60:
        m += 1; s = 0
    return f"{m}:{s:02d}"


def _pace_from_pct_vdot(vdot: float, pct: float) -> float:
    """
    Retorna pace (min/km) para um dado % do VDOT.
    Usa solver iterativo de Newton para inverter a equação de Daniels.
    pct: fração decimal (ex: 0.74 para 74% VO2max)
    """
    vo2_alvo = vdot * pct
    # Chute inicial: v ≈ (vo2_alvo + 4.6) / 0.182
    v = (vo2_alvo + 4.6) / 0.182258
    for _ in range(20):  # Newton-Raphson
        f  = -4.6 + 0.182258 * v + 0.000104 * v**2 - vo2_alvo
        df =  0.182258 + 0.000208 * v
        v -= f / df
        if abs(f) < 1e-8:
            break
    # v está em m/min → pace em min/km
    return 1000.0 / v  # min/km


# ─────────────────────────────────────────────
# Cálculo de VDOT e Zonas
# ─────────────────────────────────────────────

def calcular_vdot(dist_m: float, tempo_min: float) -> float:
    """Calcula o VDOT de Daniels a partir de distância (m) e tempo (min)."""
    v = dist_m / tempo_min  # m/min
    vo2 = -4.6 + 0.182258 * v + 0.000104 * v**2
    pct = (0.8
           + 0.1894393 * math.exp(-0.012778 * tempo_min)
           + 0.2989558 * math.exp(-0.1932605 * tempo_min))
    return round(vo2 / pct, 2)


def calcular_zonas(perfil: PerfilCorredor) -> Optional[ZonasRitmo]:
    """
    Calcula as zonas de ritmo a partir do perfil.
    Retorna None se não há RP registrado.
    """
    if not perfil.tem_rp:
        return None

    vdot = calcular_vdot(perfil.rp_dist_m, perfil.rp_total_min)

    def zona(nome, hr, desc, pct_lento, pct_rapido, pse, cor):
        p_min = _pace_from_pct_vdot(vdot, pct_lento)
        p_max = _pace_from_pct_vdot(vdot, pct_rapido)
        return PaceZona(nome, hr, desc, p_min, p_max, pse, cor)

    # Percentuais baseados em Daniels' Running Formula (2ª ed.)
    return ZonasRitmo(
        vdot=vdot,
        fonte_rp=f"{perfil.rp_distancia} em {perfil.rp_str}",
        recuperacao = zona("Recuperação",  "Z1", "Muito fácil, conversa plena",
                           0.59, 0.74, "2–3", "#60a5fa"),
        rodagem_leve= zona("Rodagem Leve", "Z2", "Confortável, fala frases inteiras",
                           0.74, 0.84, "4–5", "#34d399"),
        longao      = zona("Longão",       "Z2/Z3", "Sustentável por horas",
                           0.72, 0.83, "4–5", "#a3e635"),
        limiar      = zona("Limiar",       "Z4", "Desconfortável mas controlado",
                           0.83, 0.88, "7–8", "#fbbf24"),
        intervalado = zona("Intervalado",  "Z5", "Difícil, 3–5 min sustentável",
                           0.95, 1.00, "8–9", "#f97316"),
        repeticao   = zona("Repetição",    "Z5+", "Quase máximo, tiros curtos",
                           1.05, 1.12, "9–10","#f43f5e"),
    )


# ─────────────────────────────────────────────
# Persistência
# ─────────────────────────────────────────────

def salvar_perfil(perfil: PerfilCorredor) -> None:
    PERFIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PERFIL_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(perfil), f, ensure_ascii=False, indent=2)


def carregar_perfil() -> PerfilCorredor:
    if not PERFIL_PATH.exists():
        return PerfilCorredor()
    try:
        with open(PERFIL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return PerfilCorredor(**{k: v for k, v in data.items()
                                  if k in PerfilCorredor.__dataclass_fields__})
    except Exception:
        return PerfilCorredor()


# ─────────────────────────────────────────────
# Teste rápido
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Exemplo: corredor com RP de 22:30 nos 5km
    p = PerfilCorredor(rp_distancia="5km", rp_tempo_min=22, rp_tempo_seg=30)
    z = calcular_zonas(p)
    print(f"VDOT: {z.vdot}")
    print(f"Fonte: {z.fonte_rp}")
    print()
    for zona in [z.recuperacao, z.rodagem_leve, z.longao, z.limiar, z.intervalado, z.repeticao]:
        print(f"  {zona.zona_hr:5} {zona.nome:15} → {zona.faixa_str:22}  PSE {zona.pse_ref}")


# ─────────────────────────────────────────────
# Preditor de Provas (baseado em VDOT)
# ─────────────────────────────────────────────

@dataclass
class PrevisaoProva:
    distancia_nome: str         # "5km", "10km", "Meia", "Maratona"
    distancia_m:    float
    tempo_seg:      int
    pace_min_km:    float
    vdot_ref:       float

    @property
    def tempo_str(self) -> str:
        m, s = divmod(self.tempo_seg, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h{m:02d}'{s:02d}\""
        return f"{m}'{s:02d}\""

    @property
    def pace_str(self) -> str:
        return _fmt_pace(self.pace_min_km)


# Fatores de pace relativo ao VDOT por distância
# Calibrados contra tabelas de Daniels (Running Formula 2ª ed.)
# Representa o %VO2max sustentável em cada prova
_PROVA_PCT_VO2: dict[str, tuple[float, float]] = {
    # (distancia_m, pct_vo2max)
    "1500m":    (1500,   0.98),
    "1milha":   (1609,   0.975),
    "3km":      (3000,   0.96),
    "5km":      (5000,   0.944),
    "10km":     (10000,  0.914),
    "15km":     (15000,  0.895),
    "21km":     (21097,  0.872),
    "42km":     (42195,  0.836),
}


def prever_tempos(vdot: float) -> list[PrevisaoProva]:
    """
    Prevê tempos em provas padrão com base no VDOT atual.
    Usa Newton-Raphson para inverter a equação de Daniels.
    """
    provas_exibir = ["5km", "10km", "21km", "42km"]
    resultado = []

    for nome, (dist_m, pct) in _PROVA_PCT_VO2.items():
        if nome not in provas_exibir:
            continue

        vo2_alvo = vdot * pct
        # Chute inicial
        v = (vo2_alvo + 4.6) / 0.182258
        for _ in range(30):
            f  = -4.6 + 0.182258 * v + 0.000104 * v**2 - vo2_alvo
            df = 0.182258 + 0.000208 * v
            v -= f / df
            if abs(f) < 1e-9:
                break

        tempo_min = dist_m / v
        tempo_seg = int(round(tempo_min * 60))
        pace      = round(tempo_min / (dist_m / 1000), 3)

        nomes_display = {"5km": "5 km", "10km": "10 km", "21km": "Meia Maratona", "42km": "Maratona"}
        resultado.append(PrevisaoProva(
            distancia_nome=nomes_display[nome],
            distancia_m=dist_m,
            tempo_seg=tempo_seg,
            pace_min_km=pace,
            vdot_ref=vdot,
        ))

    return resultado


def ajustar_vdot(vdot_atual: float, nota: str) -> tuple[float, str]:
    """
    Analisa nota de treino e sugere ajuste do VDOT.
    Retorna (novo_vdot, justificativa).
    Chamado pelo Coach IA.
    """
    nota_lower = nota.lower()
    for c in "ãáâàéêíóôúç":
        nota_lower = nota_lower.replace(c, {
            "ã":"a","á":"a","â":"a","à":"a","é":"e","ê":"e",
            "í":"i","ó":"o","ô":"o","ú":"u","ç":"c"
        }[c])

    # Sinais de VDOT acima do real (muito cansativo)
    sinais_baixar = [
        "cansaco excessivo", "exausto", "nao consegui", "muito pesado",
        "perna travada", "sem energia", "overtraining", "burnout",
        "quebrei", "abandono", "parei", "nao aguentei", "excessivamente dificil",
        "pe de chumbo", "coração acelerado"
    ]
    # Sinais de VDOT abaixo do real (muito fácil)
    sinais_subir = [
        "facil demais", "muito facil", "sobrou energia", "poderia ter ido mais",
        "subestimei", "leve demais", "sem esforco", "passeio", "abaixo do esperado",
        "ritmo muito baixo", "poderia acelerar"
    ]

    score_baixar = sum(1 for s in sinais_baixar if s in nota_lower)
    score_subir  = sum(1 for s in sinais_subir  if s in nota_lower)

    if score_baixar > score_subir and score_baixar >= 1:
        ajuste = -1.0 if score_baixar == 1 else -2.0
        novo = round(vdot_atual + ajuste, 1)
        return novo, (
            f"A nota indica cansaço excessivo — os paces podem estar acima do seu VDOT real. "
            f"Sugiro reduzir o VDOT de {vdot_atual:.1f} para {novo:.1f} temporariamente "
            f"e retreinar com paces mais conservadores por 1–2 semanas."
        )
    if score_subir > score_baixar and score_subir >= 1:
        ajuste = +1.0 if score_subir == 1 else +2.0
        novo = round(vdot_atual + ajuste, 1)
        return novo, (
            f"A nota sugere que os paces estão conservadores demais. "
            f"Você pode arriscar aumentar o VDOT de {vdot_atual:.1f} para {novo:.1f} "
            f"e testar os novos paces num fartlek ou progressivo."
        )

    return vdot_atual, ""
