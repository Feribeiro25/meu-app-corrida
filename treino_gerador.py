"""
CORRENDO PELA VIDA — Gerador de Planilha Dinâmica
==================================================
Catálogo completo de treinos (Iniciante → Avançado) e lógica de
sugestão adaptativa integrada ao MotorACWR.

Tipos cobertos:
  Rodagem (Recuperação / Leve / Moderada / Pesada)
  Fartlek (Livre / Estruturado)
  Intervalado (Curto 200-400m / Longo 800-1600m)
  Progressivo / Tempo Run / Hill Repeats / Strides
  Longão (Leve Z2 / Com Progressão / Especial)
  Descanso Ativo / Mobilidade
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from acwr_motor import AcaoTreino, ResultadoACWR, ZonaRisco


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class TipoTreino(Enum):
    RECUPERACAO         = "recuperacao"
    RODAGEM_LEVE        = "rodagem_leve"
    RODAGEM_MODERADA    = "rodagem_moderada"
    RODAGEM_PESADA      = "rodagem_pesada"
    PROGRESSIVO_CURTO   = "progressivo_curto"
    PROGRESSIVO_LONGO   = "progressivo_longo"
    TEMPO_RUN           = "tempo_run"
    FARTLEK_LIVRE       = "fartlek_livre"
    FARTLEK_ESTRUTURADO = "fartlek_estruturado"
    INTERVALADO_CURTO   = "intervalado_curto"
    INTERVALADO_LONGO   = "intervalado_longo"
    HILL_REPEATS        = "hill_repeats"
    STRIDES             = "strides"
    LONGAO_LEVE         = "longao_leve"
    LONGAO_PROGRESSIVO  = "longao_progressivo"
    LONGAO_ESPECIAL     = "longao_especial"
    DESCANSO_ATIVO      = "descanso_ativo"
    MOBILIDADE          = "mobilidade"


class NivelCorredor(Enum):
    INICIANTE     = "Iniciante"
    INTERMEDIARIO = "Intermediário"
    AVANCADO      = "Avançado"


class Intensidade(Enum):
    MUITO_LEVE  = "Muito Leve"
    LEVE        = "Leve"
    MODERADA    = "Moderada"
    ALTA        = "Alta"
    MUITO_ALTA  = "Muito Alta"
    DESCANSO    = "Descanso"


# ─────────────────────────────────────────────
# Dataclass de Treino
# ─────────────────────────────────────────────

@dataclass
class TreinoSessao:
    tipo: TipoTreino
    nivel: NivelCorredor
    nome: str                  # nome curto (ex: "Rodagem Leve")
    zona_principal: str        # "Z2", "Z3/Z4", "Z4/Z5"
    intensidade: Intensidade
    distancia_ref_km: float    # km de referência (0 para descanso)
    duracao_ref_min: int       # minutos estimados
    pse_estimado: int          # PSE esperado (1–10)
    estrutura: str             # o treino detalhado (texto rico)
    dica_coach: str            # conselho do treinador

    @property
    def carga_estimada(self) -> float:
        return round(self.distancia_ref_km * self.pse_estimado, 1)

    @property
    def distancia_reduzida(self) -> float:
        """Distância após corte de 25% (zona atenção com dor)."""
        return round(self.distancia_ref_km * 0.75, 1)

    @property
    def emoji(self) -> str:
        mapa = {
            TipoTreino.RECUPERACAO:         "🔵",
            TipoTreino.RODAGEM_LEVE:        "🟢",
            TipoTreino.RODAGEM_MODERADA:    "🟡",
            TipoTreino.RODAGEM_PESADA:      "🟠",
            TipoTreino.PROGRESSIVO_CURTO:   "📈",
            TipoTreino.PROGRESSIVO_LONGO:   "📈",
            TipoTreino.TEMPO_RUN:           "⏱️",
            TipoTreino.FARTLEK_LIVRE:       "🌊",
            TipoTreino.FARTLEK_ESTRUTURADO: "⚡",
            TipoTreino.INTERVALADO_CURTO:   "🔥",
            TipoTreino.INTERVALADO_LONGO:   "🔥",
            TipoTreino.HILL_REPEATS:        "⛰️",
            TipoTreino.STRIDES:             "💨",
            TipoTreino.LONGAO_LEVE:         "🏃",
            TipoTreino.LONGAO_PROGRESSIVO:  "🏃",
            TipoTreino.LONGAO_ESPECIAL:     "🏅",
            TipoTreino.DESCANSO_ATIVO:      "🧘",
            TipoTreino.MOBILIDADE:          "🤸",
        }
        return mapa.get(self.tipo, "🏃")


# ─────────────────────────────────────────────
# Catálogo Completo de Treinos
# ─────────────────────────────────────────────
# Chave: (NivelCorredor, TipoTreino)

CATALOGO: dict[tuple, TreinoSessao] = {

    # ══════════════════════════════════════════
    # RECUPERAÇÃO
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.RECUPERACAO): TreinoSessao(
        tipo=TipoTreino.RECUPERACAO, nivel=NivelCorredor.INICIANTE,
        nome="Trote de Recuperação",
        zona_principal="Z1/Z2", intensidade=Intensidade.MUITO_LEVE,
        distancia_ref_km=3.0, duracao_ref_min=25, pse_estimado=3,
        estrutura="3 km contínuos num ritmo muito confortável (conversa fácil). "
                  "Passo leve, sem pressão. Se sentir desconforto, caminhe.",
        dica_coach="Recuperação ativa acelera a remoção de lactato. "
                   "Não tente forçar o ritmo hoje.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.RECUPERACAO): TreinoSessao(
        tipo=TipoTreino.RECUPERACAO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Rodagem de Recuperação",
        zona_principal="Z1/Z2", intensidade=Intensidade.MUITO_LEVE,
        distancia_ref_km=6.0, duracao_ref_min=40, pse_estimado=3,
        estrutura="6 km contínuos em ritmo regenerativo (Z1/Z2). "
                  "FC < 70% FCmax. Ideal após longão ou treino intenso.",
        dica_coach="Hoje é dia de restabelecer. Corra devagar o suficiente para "
                   "conversar frases completas com facilidade.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.RECUPERACAO): TreinoSessao(
        tipo=TipoTreino.RECUPERACAO, nivel=NivelCorredor.AVANCADO,
        nome="Rodagem de Recuperação Ativa",
        zona_principal="Z1/Z2", intensidade=Intensidade.MUITO_LEVE,
        distancia_ref_km=8.0, duracao_ref_min=50, pse_estimado=3,
        estrutura="8 km contínuos em Z1/Z2. Pode incluir 6×80 m de strides "
                  "soltos ao final para ativar o sistema neuromuscular.",
        dica_coach="Corredores avançados subestimam a recuperação. "
                   "A adaptação acontece no descanso, não no esforço.",
    ),

    # ══════════════════════════════════════════
    # RODAGEM LEVE (Z2)
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.RODAGEM_LEVE): TreinoSessao(
        tipo=TipoTreino.RODAGEM_LEVE, nivel=NivelCorredor.INICIANTE,
        nome="Rodagem Leve",
        zona_principal="Z2", intensidade=Intensidade.LEVE,
        distancia_ref_km=4.0, duracao_ref_min=30, pse_estimado=4,
        estrutura="4 km contínuos em ritmo confortável (Z2). Teste de conversa: "
                  "você deve conseguir falar frases completas sem ficar sem fôlego.",
        dica_coach="Z2 é onde você constrói a base aeróbica. "
                   "80% do seu volume total deve ser aqui.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.RODAGEM_LEVE): TreinoSessao(
        tipo=TipoTreino.RODAGEM_LEVE, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Rodagem Leve",
        zona_principal="Z2", intensidade=Intensidade.LEVE,
        distancia_ref_km=8.0, duracao_ref_min=48, pse_estimado=4,
        estrutura="8 km em Z2 puro. Mantenha a FC estável, sem acelerações. "
                  "Ótimo para dias entre sessões de qualidade.",
        dica_coach="Se a FC subir acima de Z2 em subidas, caminhe. "
                   "Hoje o objetivo é volume, não velocidade.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.RODAGEM_LEVE): TreinoSessao(
        tipo=TipoTreino.RODAGEM_LEVE, nivel=NivelCorredor.AVANCADO,
        nome="Rodagem Leve",
        zona_principal="Z2", intensidade=Intensidade.LEVE,
        distancia_ref_km=12.0, duracao_ref_min=65, pse_estimado=4,
        estrutura="12 km em Z2. Manter disciplina de ritmo. "
                  "Opcional: últimos 2 km com 4×100 m de strides ao final.",
        dica_coach="Dias de Z2 não são dias fáceis — são dias de trabalho aeróbico "
                   "fundamental. Mantenha a forma de corrida mesmo cansado.",
    ),

    # ══════════════════════════════════════════
    # RODAGEM MODERADA (Z3)
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.RODAGEM_MODERADA): TreinoSessao(
        tipo=TipoTreino.RODAGEM_MODERADA, nivel=NivelCorredor.INICIANTE,
        nome="Rodagem Moderada",
        zona_principal="Z3", intensidade=Intensidade.MODERADA,
        distancia_ref_km=5.0, duracao_ref_min=35, pse_estimado=6,
        estrutura="5 km em ritmo moderado (Z3). Você consegue falar, "
                  "mas frases curtas. FC entre 75–85% FCmax.",
        dica_coach="Z3 é a zona de transição aeróbica-anaeróbica. "
                   "Use com moderação — no máximo 2x por semana.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.RODAGEM_MODERADA): TreinoSessao(
        tipo=TipoTreino.RODAGEM_MODERADA, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Rodagem Moderada",
        zona_principal="Z3", intensidade=Intensidade.MODERADA,
        distancia_ref_km=10.0, duracao_ref_min=58, pse_estimado=6,
        estrutura="10 km em Z3 constante. Pace estável do início ao fim. "
                  "Evite oscilações — consistência é o objetivo.",
        dica_coach="Controle a largada. Corredores intermediários tendem a "
                   "sair rápido demais e pagar caro no segundo km.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.RODAGEM_MODERADA): TreinoSessao(
        tipo=TipoTreino.RODAGEM_MODERADA, nivel=NivelCorredor.AVANCADO,
        nome="Rodagem Moderada",
        zona_principal="Z3", intensidade=Intensidade.MODERADA,
        distancia_ref_km=14.0, duracao_ref_min=75, pse_estimado=6,
        estrutura="14 km em Z3 com excelente controle de pace. "
                  "Inclua variações de terreno se possível.",
        dica_coach="Em Z3 você treina eficiência metabólica sem destruir "
                   "a recuperação. Mantenha a cadência acima de 170 ppm.",
    ),

    # ══════════════════════════════════════════
    # RODAGEM PESADA (Z4)
    # ══════════════════════════════════════════
    (NivelCorredor.INTERMEDIARIO, TipoTreino.RODAGEM_PESADA): TreinoSessao(
        tipo=TipoTreino.RODAGEM_PESADA, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Rodagem Pesada (Limiar)",
        zona_principal="Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=8.0, duracao_ref_min=46, pse_estimado=8,
        estrutura="2 km aquecimento Z2 → 5 km em Z4 (limiar, ritmo de corrida "
                  "de 10 km/meia) → 1 km desaquecimento leve.",
        dica_coach="Z4 é desconfortável mas sustentável. Se não conseguir "
                   "manter o ritmo após 2 km, voltou cedo demais do descanso.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.RODAGEM_PESADA): TreinoSessao(
        tipo=TipoTreino.RODAGEM_PESADA, nivel=NivelCorredor.AVANCADO,
        nome="Rodagem Pesada (Limiar)",
        zona_principal="Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=12.0, duracao_ref_min=64, pse_estimado=8,
        estrutura="2 km aquecimento → 9 km em Z4 contínuo → 1 km "
                  "desaquecimento. Pace = ~10 seg mais lento que pace de 10 km.",
        dica_coach="Ao final você deve estar cansado mas não destruído. "
                   "Esse é o treino que mais melhora o VO2max de base.",
    ),

    # ══════════════════════════════════════════
    # PROGRESSIVO
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.PROGRESSIVO_CURTO): TreinoSessao(
        tipo=TipoTreino.PROGRESSIVO_CURTO, nivel=NivelCorredor.INICIANTE,
        nome="Progressivo Curto",
        zona_principal="Z2→Z3", intensidade=Intensidade.MODERADA,
        distancia_ref_km=4.0, duracao_ref_min=28, pse_estimado=5,
        estrutura="1 km Z2 (aquecimento) → 2 km Z3 (moderado) → 1 km Z2 (volta). "
                  "Cada km levemente mais rápido que o anterior.",
        dica_coach="O progressivo ensina seu corpo a acelerar com fadiga acumulada. "
                   "Comece mais devagar do que acha necessário.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.PROGRESSIVO_LONGO): TreinoSessao(
        tipo=TipoTreino.PROGRESSIVO_LONGO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Progressivo Longo",
        zona_principal="Z2→Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=10.0, duracao_ref_min=58, pse_estimado=7,
        estrutura="3 km Z2 → 4 km Z3 → 2 km Z4 → 1 km Z2 (desaquecimento). "
                  "Finalize os km de Z4 sem perder a forma.",
        dica_coach="Os 2 km finais de Z4 com pernas cansadas simulam o fim de uma "
                   "corrida. Mentalmente muito poderoso.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.PROGRESSIVO_LONGO): TreinoSessao(
        tipo=TipoTreino.PROGRESSIVO_LONGO, nivel=NivelCorredor.AVANCADO,
        nome="Progressivo Longo",
        zona_principal="Z2→Z4/Z5", intensidade=Intensidade.ALTA,
        distancia_ref_km=14.0, duracao_ref_min=74, pse_estimado=8,
        estrutura="4 km Z2 → 5 km Z3 → 3 km Z4 → 2 km Z5 (sprint final). "
                  "Controlado o tempo todo — o sprint final é controlado, não máximo.",
        dica_coach="Se você não conseguir acelerar nos últimos 2 km, "
                   "começou o Z3 rápido demais. Ajuste nas próximas sessões.",
    ),

    # ══════════════════════════════════════════
    # TEMPO RUN (Limiar sustentado)
    # ══════════════════════════════════════════
    (NivelCorredor.INTERMEDIARIO, TipoTreino.TEMPO_RUN): TreinoSessao(
        tipo=TipoTreino.TEMPO_RUN, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Tempo Run",
        zona_principal="Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=8.0, duracao_ref_min=44, pse_estimado=8,
        estrutura="2 km aquecimento Z2 → 20 min contínuos no limiar (Z4, "
                  "ritmo de 1h corrida) → 2 km desaquecimento Z2.",
        dica_coach="Desconfortável mas controlado. Se não conseguir manter "
                   "o ritmo por 20 min, reduza 5–10 seg/km e tente novamente.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.TEMPO_RUN): TreinoSessao(
        tipo=TipoTreino.TEMPO_RUN, nivel=NivelCorredor.AVANCADO,
        nome="Tempo Run",
        zona_principal="Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=12.0, duracao_ref_min=63, pse_estimado=8,
        estrutura="2 km aquecimento → 35 min contínuos no limiar → 2 km "
                  "desaquecimento. Alternativa: 2×20 min com 3 min Z2 entre.",
        dica_coach="O tempo run é o treino mais científico para melhorar VO2max. "
                   "Consistência semanal por 8 semanas = resultados dramáticos.",
    ),

    # ══════════════════════════════════════════
    # FARTLEK LIVRE
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.FARTLEK_LIVRE): TreinoSessao(
        tipo=TipoTreino.FARTLEK_LIVRE, nivel=NivelCorredor.INICIANTE,
        nome="Fartlek Livre",
        zona_principal="Z2/Z3/Z4", intensidade=Intensidade.MODERADA,
        distancia_ref_km=4.0, duracao_ref_min=30, pse_estimado=6,
        estrutura="30 min de corrida contínua. Sempre que sentir vontade, "
                  "acelere por 20–30 segundos (uma árvore, uma esquina como "
                  "referência), depois volte ao ritmo confortável. "
                  "Faça 4–6 acelerações no total.",
        dica_coach="Fartlek é a corrida mais divertida e eficaz para iniciantes. "
                   "Você decide quando acelerar — ouça o seu corpo.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.FARTLEK_LIVRE): TreinoSessao(
        tipo=TipoTreino.FARTLEK_LIVRE, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Fartlek Livre",
        zona_principal="Z2→Z4", intensidade=Intensidade.MODERADA,
        distancia_ref_km=8.0, duracao_ref_min=48, pse_estimado=6,
        estrutura="48 min com 8–10 variações de ritmo livres. Acelerações de "
                  "30 s a 2 min sempre que a vontade surgir. Recuperação ativa "
                  "entre acelerações (não parar, só desacelerar).",
        dica_coach="Use postes, placas ou trechos naturais do percurso como "
                   "referências para as acelerações. Isso mantém o fartlek "
                   "imprevisível e mentalmente estimulante.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.FARTLEK_LIVRE): TreinoSessao(
        tipo=TipoTreino.FARTLEK_LIVRE, nivel=NivelCorredor.AVANCADO,
        nome="Fartlek Livre",
        zona_principal="Z2→Z5", intensidade=Intensidade.ALTA,
        distancia_ref_km=12.0, duracao_ref_min=62, pse_estimado=7,
        estrutura="60 min com variações livres, incluindo esforços de Z5 "
                  "curtos (10–15 s sprint máximo) 4–6 vezes ao longo do treino. "
                  "Volumes e tempos definidos por sensação.",
        dica_coach="No fartlek avançado, inclua esforços máximos curtos. "
                   "Eles recrutam fibras rápidas que a corrida Z2/Z3 não toca.",
    ),

    # ══════════════════════════════════════════
    # FARTLEK ESTRUTURADO
    # ══════════════════════════════════════════
    (NivelCorredor.INTERMEDIARIO, TipoTreino.FARTLEK_ESTRUTURADO): TreinoSessao(
        tipo=TipoTreino.FARTLEK_ESTRUTURADO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Fartlek Estruturado",
        zona_principal="Z3/Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=9.0, duracao_ref_min=52, pse_estimado=7,
        estrutura="2 km aquecimento → 8×(2 min forte Z4 + 1 min fácil Z2) → "
                  "2 km desaquecimento. Total de 16 min de esforço estruturado.",
        dica_coach="A recuperação ativa (não parar!) é o segredo do fartlek "
                   "estruturado. Ela simula a fadiga real de corrida.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.FARTLEK_ESTRUTURADO): TreinoSessao(
        tipo=TipoTreino.FARTLEK_ESTRUTURADO, nivel=NivelCorredor.AVANCADO,
        nome="Fartlek Polonês",
        zona_principal="Z4/Z5", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=12.0, duracao_ref_min=62, pse_estimado=8,
        estrutura="2 km aquecimento → 10×(3 min forte Z4/Z5 + 2 min moderado Z3) "
                  "→ 2 km desaquecimento. Total de 30 min de esforço alternado.",
        dica_coach="Esse é o favorito de treinadores poloneses e kenianos. "
                   "A recuperação em Z3 (não Z1) mantém o metabolismo elevado.",
    ),

    # ══════════════════════════════════════════
    # INTERVALADO CURTO (200–400 m)
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.INTERVALADO_CURTO): TreinoSessao(
        tipo=TipoTreino.INTERVALADO_CURTO, nivel=NivelCorredor.INICIANTE,
        nome="Intervalado Curto (Intro)",
        zona_principal="Z4/Z5", intensidade=Intensidade.ALTA,
        distancia_ref_km=4.0, duracao_ref_min=35, pse_estimado=7,
        estrutura="2 km aquecimento Z2 → 6×200 m em ritmo forte (Z4/Z5) com "
                  "90 s de caminhada entre cada tiro → 1 km desaquecimento. "
                  "Foco em cadência e forma, não velocidade máxima.",
        dica_coach="Para iniciantes, o intervalado é sobre aprender a correr "
                   "rápido com boa forma, não sobre sofrimento. Menos é mais.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.INTERVALADO_CURTO): TreinoSessao(
        tipo=TipoTreino.INTERVALADO_CURTO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Intervalado 400 m",
        zona_principal="Z4/Z5", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=7.0, duracao_ref_min=48, pse_estimado=8,
        estrutura="2 km aquecimento → 8×400 m em ritmo de 5 km (Z5) com "
                  "90 s de trote Z1 entre tiros → 1–2 km desaquecimento. "
                  "Pace dos 400 m: ~5–8 s mais rápido que pace de 5 km.",
        dica_coach="O segredo do intervalado é a consistência dos tiros. "
                   "Se o 8º for muito mais lento que o 1º, você começou rápido demais.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.INTERVALADO_CURTO): TreinoSessao(
        tipo=TipoTreino.INTERVALADO_CURTO, nivel=NivelCorredor.AVANCADO,
        nome="Intervalado 400 m (Volume)",
        zona_principal="Z5", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=10.0, duracao_ref_min=60, pse_estimado=9,
        estrutura="2 km aquecimento → 12×400 m em pace de 3 km (Z5 alto) com "
                  "60 s trote entre tiros → 2 km desaquecimento. "
                  "Variação: 400/400/800/400/400 (ladder).",
        dica_coach="Intervalados de 400 m com 60 s de recuperação são brutais. "
                   "Use o cronômetro e seja honesto com o pace.",
    ),

    # ══════════════════════════════════════════
    # INTERVALADO LONGO (800–1600 m)
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.INTERVALADO_LONGO): TreinoSessao(
        tipo=TipoTreino.INTERVALADO_LONGO, nivel=NivelCorredor.INICIANTE,
        nome="Intervalado 800 m (Intro)",
        zona_principal="Z3/Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=5.0, duracao_ref_min=38, pse_estimado=7,
        estrutura="2 km aquecimento → 4×800 m em ritmo forte mas sustentável "
                  "(Z3/Z4) com 2 min de caminhada entre tiros → 1 km desaquecimento.",
        dica_coach="800 m é a distância perfeita para iniciantes aprenderem "
                   "a gerenciar o esforço em corrida. Pace dos tiros = ritmo de 10 km.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.INTERVALADO_LONGO): TreinoSessao(
        tipo=TipoTreino.INTERVALADO_LONGO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Intervalado 1000 m",
        zona_principal="Z4/Z5", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=9.0, duracao_ref_min=55, pse_estimado=8,
        estrutura="2 km aquecimento → 5×1000 m em pace de 10 km com 90 s trote "
                  "entre tiros → 2 km desaquecimento. "
                  "Variação: pirâmide 400/800/1000/800/400.",
        dica_coach="1000 m é o treino favorito da elite mundial. "
                   "Consistência nos tiros indica fitness real.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.INTERVALADO_LONGO): TreinoSessao(
        tipo=TipoTreino.INTERVALADO_LONGO, nivel=NivelCorredor.AVANCADO,
        nome="Intervalado 1600 m (Cruise)",
        zona_principal="Z4", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=13.0, duracao_ref_min=70, pse_estimado=8,
        estrutura="2 km aquecimento → 5×1600 m em pace de meia maratona com "
                  "1–2 min trote entre tiros → 2 km desaquecimento. "
                  "Alternativa: 3×2000 m com 2 min.",
        dica_coach="Intervalados de 1600 m constroem a economia de corrida "
                   "específica para provas de 10 km a meia maratona.",
    ),

    # ══════════════════════════════════════════
    # HILL REPEATS (Tiros de Morro)
    # ══════════════════════════════════════════
    (NivelCorredor.INTERMEDIARIO, TipoTreino.HILL_REPEATS): TreinoSessao(
        tipo=TipoTreino.HILL_REPEATS, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Hill Repeats",
        zona_principal="Z4/Z5", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=7.0, duracao_ref_min=50, pse_estimado=8,
        estrutura="2 km aquecimento → 8×200 m de subida em esforço forte (Z4/Z5), "
                  "descendo caminhando para recuperar → 2 km desaquecimento. "
                  "Inclinação ideal: 5–8%.",
        dica_coach="Morro fortalece glúteos, isquiotibiais e tornozelo. "
                   "Mantenha a postura ereta na subida — não se curve.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.HILL_REPEATS): TreinoSessao(
        tipo=TipoTreino.HILL_REPEATS, nivel=NivelCorredor.AVANCADO,
        nome="Hill Repeats (Volume)",
        zona_principal="Z4/Z5", intensidade=Intensidade.MUITO_ALTA,
        distancia_ref_km=10.0, duracao_ref_min=60, pse_estimado=9,
        estrutura="2 km aquecimento → 12×200 m de subida máxima + 4×400 m de "
                  "subida em Z4 → 2 km desaquecimento. Recuperação descendo ativo.",
        dica_coach="Tiros de morro são o melhor treino de força para corredores. "
                   "Substitui academia de perna na maior parte dos casos.",
    ),

    # ══════════════════════════════════════════
    # STRIDES
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.STRIDES): TreinoSessao(
        tipo=TipoTreino.STRIDES, nivel=NivelCorredor.INICIANTE,
        nome="Strides (Acelerações Curtas)",
        zona_principal="Z4/Z5", intensidade=Intensidade.MODERADA,
        distancia_ref_km=4.0, duracao_ref_min=25, pse_estimado=5,
        estrutura="3 km rodagem leve Z2 → 6×80 m de aceleração progressiva "
                  "(60% → 80% esforço) com 30–45 s de caminhada entre. "
                  "Foco: forma e passada, não velocidade máxima.",
        dica_coach="Strides melhoram a economia de corrida sem gerar fadiga. "
                   "Adicione ao final de rodagens leves 2x/semana.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.STRIDES): TreinoSessao(
        tipo=TipoTreino.STRIDES, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Strides",
        zona_principal="Z4/Z5", intensidade=Intensidade.MODERADA,
        distancia_ref_km=6.0, duracao_ref_min=35, pse_estimado=5,
        estrutura="4 km rodagem Z2 → 8×100 m progressivos (começar em Z3, "
                  "terminar quase em sprint) com 45 s de caminhada → 1 km trote.",
        dica_coach="Nos strides, a última etapa de cada aceleração deve ser "
                   "apenas 85–90% do esforço máximo. Controle a largada.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.STRIDES): TreinoSessao(
        tipo=TipoTreino.STRIDES, nivel=NivelCorredor.AVANCADO,
        nome="Strides + Drills",
        zona_principal="Z4/Z5", intensidade=Intensidade.MODERADA,
        distancia_ref_km=8.0, duracao_ref_min=40, pse_estimado=5,
        estrutura="5 km Z2 → Drills técnicos (skipping, butt kicks, high knees) "
                  "50 m cada → 8×100 m strides 90% esforço → 2 km Z2.",
        dica_coach="Drills técnicos antes dos strides potencializam o recrutamento "
                   "neuromuscular. Fundamental 2x/semana para corredores avançados.",
    ),

    # ══════════════════════════════════════════
    # LONGÃO LEVE (Z2)
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.LONGAO_LEVE): TreinoSessao(
        tipo=TipoTreino.LONGAO_LEVE, nivel=NivelCorredor.INICIANTE,
        nome="Longão Leve",
        zona_principal="Z2", intensidade=Intensidade.LEVE,
        distancia_ref_km=9.0, duracao_ref_min=72, pse_estimado=4,
        estrutura="9 km em Z2 contínuos. Ritmo de conversa durante todo o percurso. "
                  "Se precisar caminhar, tudo bem — mantenha o tempo em movimento.",
        dica_coach="O longão semanal constrói a base que sustenta tudo. "
                   "Mais importante que velocidade: completar o tempo em movimento.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.LONGAO_LEVE): TreinoSessao(
        tipo=TipoTreino.LONGAO_LEVE, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Longão Leve",
        zona_principal="Z2", intensidade=Intensidade.LEVE,
        distancia_ref_km=16.0, duracao_ref_min=100, pse_estimado=4,
        estrutura="16 km em Z2 puro. FC constante, ritmo confortável o tempo todo. "
                  "Hidrate a cada 20 min. Priorize percursos planos.",
        dica_coach="Para longões acima de 80 min, comece a pensar em nutrição: "
                   "gel ou banana a partir do km 10–12.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.LONGAO_LEVE): TreinoSessao(
        tipo=TipoTreino.LONGAO_LEVE, nivel=NivelCorredor.AVANCADO,
        nome="Longão Leve",
        zona_principal="Z2", intensidade=Intensidade.LEVE,
        distancia_ref_km=22.0, duracao_ref_min=126, pse_estimado=4,
        estrutura="22 km em Z2. Pode incluir variações de terreno. "
                  "Nutrição: gel a cada 45 min a partir do km 14.",
        dica_coach="Longões acima de 2h ensinam o corpo a oxidar gordura. "
                   "Saia mais devagar do que parece necessário.",
    ),

    # ══════════════════════════════════════════
    # LONGÃO COM PROGRESSÃO
    # ══════════════════════════════════════════
    (NivelCorredor.INTERMEDIARIO, TipoTreino.LONGAO_PROGRESSIVO): TreinoSessao(
        tipo=TipoTreino.LONGAO_PROGRESSIVO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Longão com Progressão",
        zona_principal="Z2→Z3", intensidade=Intensidade.MODERADA,
        distancia_ref_km=14.0, duracao_ref_min=88, pse_estimado=5,
        estrutura="12 km Z2 → últimos 2 km acelerando para Z3. "
                  "Você deve terminar cansado mas não destruído.",
        dica_coach="A progressão final simula o 'negative split' de corrida. "
                   "Treine a aceleração com pernas cansadas regularmente.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.LONGAO_PROGRESSIVO): TreinoSessao(
        tipo=TipoTreino.LONGAO_PROGRESSIVO, nivel=NivelCorredor.AVANCADO,
        nome="Longão com Progressão (MP)",
        zona_principal="Z2→Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=24.0, duracao_ref_min=142, pse_estimado=6,
        estrutura="16 km Z2 → 5 km Z3 → 3 km em ritmo de maratona (Z3/Z4). "
                  "Nutrição completa. Simula os km finais da maratona.",
        dica_coach="Longão especial para maratonistas. Se o pace de maratona "
                   "no final parecer impossível, ajuste a meta de prova.",
    ),

    # ══════════════════════════════════════════
    # LONGÃO ESPECIAL (Avançado)
    # ══════════════════════════════════════════
    (NivelCorredor.AVANCADO, TipoTreino.LONGAO_ESPECIAL): TreinoSessao(
        tipo=TipoTreino.LONGAO_ESPECIAL, nivel=NivelCorredor.AVANCADO,
        nome="Longão Marathon Pace",
        zona_principal="Z3/Z4", intensidade=Intensidade.ALTA,
        distancia_ref_km=28.0, duracao_ref_min=160, pse_estimado=6,
        estrutura="8 km Z2 → 16 km em ritmo de maratona alvo (Z3/Z4) → "
                  "4 km Z2 desaquecimento. Nutrição rigorosa: gel a cada 40 min.",
        dica_coach="O treino mais específico para maratona. Faça apenas 1x por "
                   "ciclo de 3–4 semanas. Recuperação mínima de 10 dias depois.",
    ),

    # ══════════════════════════════════════════
    # DESCANSO ATIVO
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.DESCANSO_ATIVO): TreinoSessao(
        tipo=TipoTreino.DESCANSO_ATIVO, nivel=NivelCorredor.INICIANTE,
        nome="Descanso Ativo",
        zona_principal="Z1", intensidade=Intensidade.MUITO_LEVE,
        distancia_ref_km=0.0, duracao_ref_min=30, pse_estimado=2,
        estrutura="20–30 min de caminhada leve ou ciclismo muito fácil. "
                  "Sem corrida hoje. Hidratação e sono são o treino.",
        dica_coach="Descanso não é fraqueza — é parte do plano. "
                   "A adaptação ao treino ocorre nas horas de recuperação.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.DESCANSO_ATIVO): TreinoSessao(
        tipo=TipoTreino.DESCANSO_ATIVO, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Descanso Ativo",
        zona_principal="Z1", intensidade=Intensidade.MUITO_LEVE,
        distancia_ref_km=0.0, duracao_ref_min=30, pse_estimado=2,
        estrutura="30 min de caminhada, natação leve ou bike Z1. "
                  "Priorize 8h de sono e hidratação adequada.",
        dica_coach="Corredores intermediários erram mais por excesso do que "
                   "por falta. Respeite os dias de descanso no plano.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.DESCANSO_ATIVO): TreinoSessao(
        tipo=TipoTreino.DESCANSO_ATIVO, nivel=NivelCorredor.AVANCADO,
        nome="Descanso Ativo",
        zona_principal="Z1", intensidade=Intensidade.MUITO_LEVE,
        distancia_ref_km=0.0, duracao_ref_min=45, pse_estimado=2,
        estrutura="45 min de natação leve, ciclismo Z1 ou caminhada. "
                  "Foam roller + gelo em regiões com tensão. "
                  "Sem carga musculoesquelética de impacto.",
        dica_coach="Atletas avançados usam o descanso ativo para manter "
                   "mobilidade articular sem comprometer a recuperação.",
    ),

    # ══════════════════════════════════════════
    # MOBILIDADE
    # ══════════════════════════════════════════
    (NivelCorredor.INICIANTE, TipoTreino.MOBILIDADE): TreinoSessao(
        tipo=TipoTreino.MOBILIDADE, nivel=NivelCorredor.INICIANTE,
        nome="Mobilidade e Alongamento",
        zona_principal="—", intensidade=Intensidade.DESCANSO,
        distancia_ref_km=0.0, duracao_ref_min=30, pse_estimado=1,
        estrutura="30 min: Foam roller (panturrilha, TI, glúteo) 10 min → "
                  "Alongamento estático (quadril flexor, isquiotibial, "
                  "panturrilha) 3×30 s cada → Fortalecimento básico: "
                  "3×15 de ponte de glúteo.",
        dica_coach="Mobilidade regular é a melhor prevenção de lesão para "
                   "iniciantes. Panturrilha e quadril flexor são prioritários.",
    ),
    (NivelCorredor.INTERMEDIARIO, TipoTreino.MOBILIDADE): TreinoSessao(
        tipo=TipoTreino.MOBILIDADE, nivel=NivelCorredor.INTERMEDIARIO,
        nome="Mobilidade + Força de Corrida",
        zona_principal="—", intensidade=Intensidade.DESCANSO,
        distancia_ref_km=0.0, duracao_ref_min=45, pse_estimado=1,
        estrutura="45 min: Foam roller completo 10 min → Mobilidade dinâmica "
                  "(leg swings, hip circles) 10 min → Fortalecimento: "
                  "3×20 de agachamento unilateral, 3×15 de elevação de panturrilha, "
                  "3×12 de dead bug.",
        dica_coach="Força monopodal é essencial para corredores. "
                   "Um agachamento pistol é mais útil do que qualquer leg press.",
    ),
    (NivelCorredor.AVANCADO, TipoTreino.MOBILIDADE): TreinoSessao(
        tipo=TipoTreino.MOBILIDADE, nivel=NivelCorredor.AVANCADO,
        nome="Mobilidade + Força Específica",
        zona_principal="—", intensidade=Intensidade.DESCANSO,
        distancia_ref_km=0.0, duracao_ref_min=60, pse_estimado=2,
        estrutura="60 min: Foam roller + massagem de bola 15 min → "
                  "Yoga flow específico para corredores 20 min → "
                  "Circuito: Nordic curl 3×8, drop jump 3×10, "
                  "RDL unilateral 3×12, plank rotacional 3×45 s.",
        dica_coach="Atletas avançados investem em pliometria e força excêntrica. "
                   "Nordic curls são o melhor exercício para prevenir lesão de isquio.",
    ),
}


# ─────────────────────────────────────────────
# Templates Semanais por Nível
# Índice: 0=Segunda, 1=Terça, ..., 6=Domingo
# ─────────────────────────────────────────────

TEMPLATE_SEMANAL: dict[NivelCorredor, dict[int, TipoTreino]] = {

    NivelCorredor.INICIANTE: {
        0: TipoTreino.DESCANSO_ATIVO,       # Segunda
        1: TipoTreino.RODAGEM_LEVE,          # Terça
        2: TipoTreino.FARTLEK_LIVRE,         # Quarta
        3: TipoTreino.DESCANSO_ATIVO,        # Quinta
        4: TipoTreino.RODAGEM_LEVE,          # Sexta
        5: TipoTreino.LONGAO_LEVE,           # Sábado
        6: TipoTreino.MOBILIDADE,            # Domingo
    },

    NivelCorredor.INTERMEDIARIO: {
        0: TipoTreino.RECUPERACAO,           # Segunda (pós longão)
        1: TipoTreino.INTERVALADO_CURTO,     # Terça
        2: TipoTreino.RODAGEM_MODERADA,      # Quarta
        3: TipoTreino.TEMPO_RUN,             # Quinta
        4: TipoTreino.RODAGEM_LEVE,          # Sexta
        5: TipoTreino.LONGAO_LEVE,           # Sábado
        6: TipoTreino.MOBILIDADE,            # Domingo
    },

    NivelCorredor.AVANCADO: {
        0: TipoTreino.RECUPERACAO,           # Segunda
        1: TipoTreino.INTERVALADO_LONGO,     # Terça
        2: TipoTreino.RODAGEM_MODERADA,      # Quarta
        3: TipoTreino.TEMPO_RUN,             # Quinta
        4: TipoTreino.RODAGEM_PESADA,        # Sexta
        5: TipoTreino.LONGAO_PROGRESSIVO,    # Sábado
        6: TipoTreino.MOBILIDADE,            # Domingo
    },
}

NOMES_DIA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


# ─────────────────────────────────────────────
# Gerador de Treino
# ─────────────────────────────────────────────

class GeradorTreino:
    """
    Consulta o MotorACWR e devolve o treino ajustado para amanhã.
    """

    def sugerir_amanha(
        self,
        nivel: NivelCorredor,
        resultado_acwr: Optional[ResultadoACWR] = None,
        data_amanha: Optional[date] = None,
    ) -> tuple[TreinoSessao, str, bool]:
        """
        Retorna (treino, justificativa, volume_reduzido).

        volume_reduzido = True indica que a distância deve usar
        treino.distancia_reduzida (−25%) em vez da referência.
        """
        if data_amanha is None:
            data_amanha = date.today() + timedelta(days=1)

        dia = data_amanha.weekday()
        tipo_base = TEMPLATE_SEMANAL[nivel][dia]
        volume_reduzido = False

        # ── Sem histórico ACWR suficiente ────────────────────────────────
        if resultado_acwr is None:
            treino = self._buscar(nivel, tipo_base)
            return treino, "Histórico insuficiente — treino baseado no plano semanal.", False

        acao = resultado_acwr.acao

        # ── BLOQUEADO (vermelho ou veto de dor) ──────────────────────────
        if acao == AcaoTreino.TREINO_BLOQUEADO:
            # Prefere mobilidade sobre descanso puro quando há dor articular
            if resultado_acwr.dor_reportada >= 4:
                tipo_final = TipoTreino.MOBILIDADE
                justif = (
                    f"Dor {resultado_acwr.dor_reportada}/10 ativa o protocolo de proteção. "
                    "Treino substituído por mobilidade terapêutica."
                )
            else:
                tipo_final = TipoTreino.DESCANSO_ATIVO
                justif = (
                    f"ACWR {resultado_acwr.acwr:.2f} — zona de perigo. "
                    "Corrida bloqueada. Descanso ativo para recuperação de carga."
                )
            treino = self._buscar(nivel, tipo_final)
            return treino, justif, False

        # ── REDUZIDO (atenção + dor leve) ────────────────────────────────
        if acao == AcaoTreino.TREINO_REDUZIDO:
            # Sempre converte para rodagem leve com volume −25%
            treino = self._buscar(nivel, TipoTreino.RODAGEM_LEVE)
            justif = (
                f"ACWR {resultado_acwr.acwr:.2f} + dor leve {resultado_acwr.dor_reportada}/10. "
                f"Convertido para Rodagem Leve com volume reduzido para "
                f"{treino.distancia_reduzida:.1f} km (−25%)."
            )
            return treino, justif, True

        # ── MANTIDO com aviso (modelo adaptativo — sua escolha) ──────────
        if acao == AcaoTreino.TREINO_MANTIDO:
            treino = self._buscar(nivel, tipo_base)
            justif = (
                f"Treino mantido conforme plano. ACWR {resultado_acwr.acwr:.2f} "
                f"na zona de atenção — monitore sinais de fadiga durante a sessão."
            )
            return treino, justif, False

        # ── NORMAL (zona ótima ou subtreino) ─────────────────────────────
        treino = self._buscar(nivel, tipo_base)
        if resultado_acwr.zona == ZonaRisco.SUBTREINO:
            justif = (
                f"ACWR {resultado_acwr.acwr:.2f} abaixo do ideal. "
                "Execute o treino e considere aumentar levemente o volume progressivamente."
            )
        else:
            justif = (
                f"Zona ótima (ACWR {resultado_acwr.acwr:.2f}). "
                "Execute o treino planejado com confiança."
            )
        return treino, justif, False

    def semana_completa(
        self,
        nivel: NivelCorredor,
        inicio: Optional[date] = None,
    ) -> list[tuple[date, TreinoSessao]]:
        """
        Retorna os 7 treinos da semana a partir de 'inicio' (padrão: próxima segunda).
        """
        if inicio is None:
            hoje = date.today()
            dias_ate_segunda = (7 - hoje.weekday()) % 7 or 7
            inicio = hoje + timedelta(days=dias_ate_segunda)

        semana = []
        for i in range(7):
            d = inicio + timedelta(days=i)
            tipo = TEMPLATE_SEMANAL[nivel][d.weekday()]
            treino = self._buscar(nivel, tipo)
            semana.append((d, treino))
        return semana

    def _buscar(self, nivel: NivelCorredor, tipo: TipoTreino) -> TreinoSessao:
        """Busca no catálogo. Fallback: rodagem leve do nível."""
        treino = CATALOGO.get((nivel, tipo))
        if treino is None:
            # Tenta nível intermediário como fallback universal
            treino = CATALOGO.get((NivelCorredor.INTERMEDIARIO, tipo))
        if treino is None:
            treino = CATALOGO[(NivelCorredor.INICIANTE, TipoTreino.RODAGEM_LEVE)]
        return treino
