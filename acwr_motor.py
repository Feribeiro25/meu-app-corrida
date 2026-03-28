"""
CORRENDO PELA VIDA — Motor ACWR
================================
Motor de decisão central baseado na Razão de Carga Aguda/Crônica (ACWR).
Carga = Distância (km) × PSE (1–10)

Regras do Modelo Adaptativo:
  Zona Ótima   (0.8 – 1.3) → Treino normal
  Zona Atenção (1.3 – 1.5) → Manter se sem dor | Reduzir 25% se dor leve (1–3)
  Zona Perigo  (> 1.5)     → Bloquear treino
  Dor ≥ 4                  → Bloquear treino (veto independente do ACWR)
  ACWR < 0.8               → Alerta de subtreino (destreino)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math


# ─────────────────────────────────────────────
# Tipos e Enums
# ─────────────────────────────────────────────

class ZonaRisco(Enum):
    SUBTREINO  = "subtreino"
    OTIMA      = "ótima"
    ATENCAO    = "atenção"
    PERIGO     = "perigo"
    BLOQUEADO  = "bloqueado"   # ativado por dor ≥ 4, independente do ACWR


class AcaoTreino(Enum):
    TREINO_NORMAL    = "treino_normal"
    TREINO_MANTIDO   = "treino_mantido_com_aviso"   # ACWR alto, sem dor
    TREINO_REDUZIDO  = "treino_reduzido_25"          # dor leve
    TREINO_BLOQUEADO = "treino_bloqueado"


@dataclass
class SessaoTreino:
    """Representa uma sessão de corrida individual."""
    distancia_km: float          # distância percorrida
    pse: int                     # Percepção Subjetiva de Esforço (1–10)
    dor: int = 0                 # intensidade de dor reportada (0–10)
    localizacao_dor: str = ""    # ex: "joelho direito", "tendão de Aquiles"

    def __post_init__(self) -> None:
        if not (0.0 < self.distancia_km <= 100.0):
            raise ValueError(f"Distância inválida: {self.distancia_km} km")
        if not (1 <= self.pse <= 10):
            raise ValueError(f"PSE deve ser entre 1 e 10, recebido: {self.pse}")
        if not (0 <= self.dor <= 10):
            raise ValueError(f"Dor deve ser entre 0 e 10, recebida: {self.dor}")

    @property
    def carga(self) -> float:
        """Carga de treino = Distância × PSE."""
        return round(self.distancia_km * self.pse, 2)


@dataclass
class HistoricoSemanas:
    """
    Histórico de carga organizado por semanas.

    semana_atual  → lista de SessaoTreino dos últimos 7 dias
    semanas_prev  → lista de 3 semanas anteriores (cada uma = lista de SessaoTreino)
                    usado para calcular a média crônica (28 dias = 7 + 21)
    """
    semana_atual: list[SessaoTreino] = field(default_factory=list)
    semanas_prev: list[list[SessaoTreino]] = field(default_factory=list)  # idealmente 3 semanas

    def carga_semanal(self, sessoes: list[SessaoTreino]) -> float:
        return round(sum(s.carga for s in sessoes), 2)

    @property
    def carga_aguda(self) -> float:
        """Carga dos últimos 7 dias."""
        return self.carga_semanal(self.semana_atual)

    @property
    def carga_cronica(self) -> float:
        """
        Média das semanas disponíveis (até 4 semanas = atual + 3 prev).
        Com menos de 4 semanas, usa o que tem (fase de calibração).
        """
        todas_semanas = [self.semana_atual] + self.semanas_prev
        if not todas_semanas:
            return 0.0
        cargas = [self.carga_semanal(s) for s in todas_semanas]
        return round(sum(cargas) / len(cargas), 2)

    @property
    def semanas_disponiveis(self) -> int:
        return 1 + len(self.semanas_prev)

    @property
    def modo_calibracao(self) -> bool:
        """True se tiver menos de 4 semanas de histórico."""
        return self.semanas_disponiveis < 4


# ─────────────────────────────────────────────
# Resultado do Motor
# ─────────────────────────────────────────────

@dataclass
class ResultadoACWR:
    acwr: float
    carga_aguda: float
    carga_cronica: float
    zona: ZonaRisco
    acao: AcaoTreino
    dor_reportada: int
    volume_ajuste_pct: float          # 0.0 = sem ajuste, -0.25 = redução de 25%
    modo_calibracao: bool
    semanas_disponiveis: int

    # Mensagens geradas pelo motor
    titulo: str = ""
    mensagem_coach: str = ""
    aviso_dor: str = ""

    @property
    def volume_amanha_pct(self) -> int:
        """Volume de amanhã como % do planejado (ex: 75 = reduzir 25%)."""
        return int((1 + self.volume_ajuste_pct) * 100)

    def exibir(self) -> str:
        """Formata o resultado completo para exibição no terminal."""
        separador = "─" * 60
        linhas = [
            separador,
            f"  CORRENDO PELA VIDA — Análise de Risco",
            separador,
            f"  ACWR Calculado      : {self.acwr:.3f}",
            f"  Carga Aguda (7d)    : {self.carga_aguda:.1f} u.a.",
            f"  Carga Crônica (28d) : {self.carga_cronica:.1f} u.a.",
            f"  Zona de Risco       : {self.zona.value.upper()}",
            f"  Ação Recomendada    : {self.acao.value}",
            f"  Volume amanhã       : {self.volume_amanha_pct}% do planejado",
        ]

        if self.modo_calibracao:
            linhas.append(
                f"  [Calibração]        : {self.semanas_disponiveis}/4 semanas "
                f"— ACWR ainda estimado"
            )

        linhas += [
            separador,
            f"  {self.titulo}",
            separador,
        ]

        for linha in self.mensagem_coach.split("\n"):
            linhas.append(f"  {linha}")

        if self.aviso_dor:
            linhas.append(separador)
            linhas.append(f"  ALERTA DE DOR: {self.aviso_dor}")

        linhas.append(separador)
        return "\n".join(linhas)


# ─────────────────────────────────────────────
# Motor ACWR — lógica central
# ─────────────────────────────────────────────

class MotorACWR:
    """
    Motor de decisão principal do app.
    Recebe o histórico de treinos e retorna o status de risco
    e a sugestão para o treino de amanhã.
    """

    # Limites das zonas (configuráveis)
    LIMITE_SUBTREINO = 0.8
    LIMITE_ATENCAO   = 1.3
    LIMITE_PERIGO    = 1.5

    # Limiares de dor
    DOR_LEVE_MAX   = 3    # dor 1–3: leve, reduz volume
    DOR_VETO_MIN   = 4    # dor ≥ 4: bloqueia treino

    def calcular(
        self,
        historico: HistoricoSemanas,
        dor_hoje: int = 0,
        localizacao_dor: str = "",
    ) -> ResultadoACWR:
        """
        Executa o motor de decisão completo.

        Args:
            historico: objeto com semana atual e semanas anteriores
            dor_hoje: intensidade de dor reportada após o treino (0–10)
            localizacao_dor: onde está a dor (texto livre)

        Returns:
            ResultadoACWR com zona, ação e mensagens do coach
        """
        carga_aguda   = historico.carga_aguda
        carga_cronica = historico.carga_cronica

        # Evita divisão por zero (primeiras semanas, sem histórico crônico)
        if carga_cronica == 0:
            acwr = 1.0  # assume zona ótima quando não há base de comparação
        else:
            acwr = round(carga_aguda / carga_cronica, 3)

        # Determina zona e ação
        zona, acao, ajuste, titulo, mensagem, aviso_dor = self._aplicar_regras(
            acwr, dor_hoje, localizacao_dor,
            carga_aguda, carga_cronica,
            historico.modo_calibracao
        )

        return ResultadoACWR(
            acwr=acwr,
            carga_aguda=carga_aguda,
            carga_cronica=carga_cronica,
            zona=zona,
            acao=acao,
            dor_reportada=dor_hoje,
            volume_ajuste_pct=ajuste,
            modo_calibracao=historico.modo_calibracao,
            semanas_disponiveis=historico.semanas_disponiveis,
            titulo=titulo,
            mensagem_coach=mensagem,
            aviso_dor=aviso_dor,
        )

    def _aplicar_regras(
        self,
        acwr: float,
        dor: int,
        local_dor: str,
        carga_aguda: float,
        carga_cronica: float,
        modo_calibracao: bool,
    ) -> tuple:
        """
        Aplica as Regras de Ouro do Modelo Adaptativo.
        Retorna: (zona, acao, ajuste_volume, titulo, mensagem, aviso_dor)
        """
        variacao_pct = self._variacao_percentual(carga_aguda, carga_cronica)
        aviso_dor = ""

        # ── REGRA ZERO: Dor ≥ 4 tem veto absoluto ──────────────────────────
        if dor >= self.DOR_VETO_MIN:
            aviso_dor = self._texto_aviso_dor(dor, local_dor)
            return (
                ZonaRisco.BLOQUEADO,
                AcaoTreino.TREINO_BLOQUEADO,
                -1.0,
                "Treino bloqueado — dor requer atenção",
                self._msg_bloqueado_por_dor(dor, local_dor),
                aviso_dor,
            )

        # ── ZONA PERIGO: ACWR > 1.5 ─────────────────────────────────────────
        if acwr > self.LIMITE_PERIGO:
            return (
                ZonaRisco.PERIGO,
                AcaoTreino.TREINO_BLOQUEADO,
                -1.0,
                "Treino bloqueado — zona de perigo",
                self._msg_perigo(acwr, variacao_pct, dor),
                aviso_dor,
            )

        # ── ZONA ATENÇÃO: 1.3 < ACWR ≤ 1.5 ─────────────────────────────────
        if acwr > self.LIMITE_ATENCAO:

            # Sub-regra: dor leve (1–3) → reduzir 25%
            if 1 <= dor <= self.DOR_LEVE_MAX:
                aviso_dor = self._texto_aviso_dor(dor, local_dor)
                return (
                    ZonaRisco.ATENCAO,
                    AcaoTreino.TREINO_REDUZIDO,
                    -0.25,
                    "Treino reduzido — atenção com dor leve",
                    self._msg_atencao_com_dor(acwr, variacao_pct, dor, local_dor),
                    aviso_dor,
                )

            # Sub-regra ADAPTATIVA: sem dor → mantém com aviso (sua escolha!)
            return (
                ZonaRisco.ATENCAO,
                AcaoTreino.TREINO_MANTIDO,
                0.0,
                "Treino mantido — atenção ao ACWR",
                self._msg_atencao_sem_dor(acwr, variacao_pct),
                aviso_dor,
            )

        # ── ZONA SUBTREINO: ACWR < 0.8 ──────────────────────────────────────
        if acwr < self.LIMITE_SUBTREINO:
            return (
                ZonaRisco.SUBTREINO,
                AcaoTreino.TREINO_NORMAL,
                0.0,
                "Treino normal — carga abaixo do ideal",
                self._msg_subtreino(acwr, variacao_pct, modo_calibracao),
                aviso_dor,
            )

        # ── ZONA ÓTIMA: 0.8 ≤ ACWR ≤ 1.3 ────────────────────────────────────
        return (
            ZonaRisco.OTIMA,
            AcaoTreino.TREINO_NORMAL,
            0.0,
            "Tudo certo — zona ótima de treino",
            self._msg_otima(acwr, variacao_pct, dor),
            aviso_dor,
        )

    # ─────────────────────────────────────────
    # Mensagens do Coach IA (texto gerado)
    # ─────────────────────────────────────────

    def _msg_otima(self, acwr: float, var_pct: float, dor: int) -> str:
        var_str = f"+{var_pct:.0f}%" if var_pct >= 0 else f"{var_pct:.0f}%"
        base = (
            f"Sua carga está em equilíbrio perfeito (ACWR: {acwr:.2f}).\n"
            f"A variação em relação à média do mês é de {var_str}.\n"
            f"Execute o treino planejado normalmente amanhã."
        )
        if dor == 0:
            base += "\nNenhum desconforto relatado — ótimo sinal de recuperação."
        return base

    def _msg_subtreino(self, acwr: float, var_pct: float, calibracao: bool) -> str:
        var_str = f"{var_pct:.0f}%"
        msg = (
            f"Sua carga dos últimos 7 dias está abaixo da sua média ({var_str}).\n"
            f"ACWR de {acwr:.2f} indica possível destreino se mantido por mais de 2 semanas.\n"
            f"Amanhã: execute o treino planejado e considere aumentar levemente o volume."
        )
        if calibracao:
            msg += "\n[Fase de calibração — continue registrando para maior precisão]"
        return msg

    def _msg_atencao_sem_dor(self, acwr: float, var_pct: float) -> str:
        """Mensagem do modelo ADAPTATIVO — sua decisão de produto."""
        return (
            f"Seu volume subiu {var_pct:.0f}% em relação à média do mês (ACWR: {acwr:.2f}).\n"
            f"Isso está na zona de atenção, mas como você não relatou nenhum\n"
            f"desconforto, mantivemos o treino planejado para amanhã.\n\n"
            f"Atenção durante o treino: se sentir qualquer dor muscular fora\n"
            f"do normal, fadiga incomum nas pernas ou desconforto articular,\n"
            f"pare imediatamente e registre aqui.\n\n"
            f"Amanhã o treino será mais leve para reequilibrar a carga."
        )

    def _msg_atencao_com_dor(
        self, acwr: float, var_pct: float, dor: int, local: str
    ) -> str:
        local_str = f" ({local})" if local else ""
        return (
            f"Combinação de atenção: ACWR {acwr:.2f} + dor leve {dor}/10{local_str}.\n"
            f"O volume de amanhã foi reduzido em 25% como medida preventiva.\n\n"
            f"Substitua a parte de intensidade por rodagem leve ou exercícios\n"
            f"de técnica de corrida. Monitore a dor durante o aquecimento:\n"
            f"se piorar, interrompa e registre."
        )

    def _msg_perigo(self, acwr: float, var_pct: float, dor: int) -> str:
        msg = (
            f"Zona de perigo: ACWR {acwr:.2f} — sua carga subiu {var_pct:.0f}%\n"
            f"em relação à sua média. O risco de lesão por sobrecarga é alto.\n\n"
            f"Amanhã: descanso ativo recomendado (caminhada leve, mobilidade,\n"
            f"alongamento). Sem corrida até o ACWR retornar abaixo de 1.3.\n\n"
            f"Dica: hidratação, sono e massagem de recuperação acelerarão\n"
            f"a queda da carga aguda."
        )
        if dor > 0:
            msg += f"\nAtenção extra: você também relatou dor {dor}/10."
        return msg

    def _msg_bloqueado_por_dor(self, dor: int, local: str) -> str:
        local_str = f" em {local}" if local else ""
        return (
            f"Dor de intensidade {dor}/10{local_str} registrada.\n"
            f"Independente do ACWR, dor nesse nível pode indicar lesão em\n"
            f"desenvolvimento. O treino de corrida de amanhã está bloqueado.\n\n"
            f"Recomendações:\n"
            f"  • Aplique gelo na região dolorida (15 min, 3x ao dia)\n"
            f"  • Evite impacto nas próximas 24–48h\n"
            f"  • Se a dor persistir por mais de 48h, consulte um fisioterapeuta\n"
            f"  • Você pode fazer mobilidade suave e exercícios de core"
        )

    def _texto_aviso_dor(self, dor: int, local: str) -> str:
        local_str = f" em {local}" if local else ""
        nivel = "leve" if dor <= 3 else "moderada a intensa" if dor <= 6 else "severa"
        return f"Dor {nivel} ({dor}/10){local_str} registrada e considerada na decisão."

    @staticmethod
    def _variacao_percentual(aguda: float, cronica: float) -> float:
        if cronica == 0:
            return 0.0
        return round(((aguda - cronica) / cronica) * 100, 1)


# ─────────────────────────────────────────────
# Helpers para construção rápida de histórico
# ─────────────────────────────────────────────

def sessoes_da_semana(dados: list[tuple[float, int]]) -> list[SessaoTreino]:
    """
    Atalho para criar sessões a partir de lista de tuplas (distância, PSE).
    Exemplo: sessoes_da_semana([(10, 7), (0, 0), (12, 6)])
    Use (0, 0) para dias de descanso (não geram carga).
    """
    sessoes = []
    for dist, pse in dados:
        if dist > 0 and pse > 0:
            sessoes.append(SessaoTreino(distancia_km=dist, pse=pse))
    return sessoes


def construir_historico(
    semana_atual: list[tuple[float, int]],
    semana_2: list[tuple[float, int]] | None = None,
    semana_3: list[tuple[float, int]] | None = None,
    semana_4: list[tuple[float, int]] | None = None,
) -> HistoricoSemanas:
    """
    Constrói o histórico das últimas 4 semanas a partir de tuplas simples.
    Semana atual = últimos 7 dias (mais recente).
    Semana 2 = 8–14 dias atrás. Semana 3 = 15–21. Semana 4 = 22–28.
    """
    prev = []
    for semana in [semana_2, semana_3, semana_4]:
        if semana is not None:
            prev.append(sessoes_da_semana(semana))

    return HistoricoSemanas(
        semana_atual=sessoes_da_semana(semana_atual),
        semanas_prev=prev,
    )


# ─────────────────────────────────────────────
# Cenários de demonstração / testes
# ─────────────────────────────────────────────

def rodar_cenarios():
    motor = MotorACWR()

    cenarios = [
        {
            "nome": "Cenário 1 — Zona Ótima, sem dor",
            "semana_atual": [(10, 6), (0, 0), (8, 5), (0, 0), (12, 7), (0, 0), (6, 4)],
            "semana_2":     [(9, 6),  (0, 0), (7, 5), (0, 0), (11, 6), (0, 0), (5, 4)],
            "semana_3":     [(8, 5),  (0, 0), (8, 6), (0, 0), (10, 6), (0, 0), (6, 4)],
            "semana_4":     [(9, 6),  (0, 0), (7, 5), (0, 0), (10, 5), (0, 0), (5, 4)],
            "dor": 0,
        },
        {
            "nome": "Cenário 2 — Zona Atenção, sem dor (MODELO ADAPTATIVO)",
            # Semana atual moderadamente mais alta → ACWR ~1.4
            "semana_atual": [(12, 7), (0, 0), (10, 7), (0, 0), (13, 7), (8, 6), (0, 0)],
            "semana_2":     [(9, 6),  (0, 0), (8, 5),  (0, 0), (11, 6), (0, 0), (7, 5)],
            "semana_3":     [(8, 5),  (0, 0), (7, 5),  (0, 0), (10, 5), (0, 0), (6, 4)],
            "semana_4":     [(9, 5),  (0, 0), (8, 5),  (0, 0), (10, 5), (0, 0), (6, 4)],
            "dor": 0,
        },
        {
            "nome": "Cenário 3 — Zona Atenção com dor leve (3/10 no joelho)",
            "semana_atual": [(12, 7), (0, 0), (10, 7), (0, 0), (13, 7), (8, 6), (0, 0)],
            "semana_2":     [(9, 6),  (0, 0), (8, 5),  (0, 0), (11, 6), (0, 0), (7, 5)],
            "semana_3":     [(8, 5),  (0, 0), (7, 5),  (0, 0), (10, 5), (0, 0), (6, 4)],
            "semana_4":     [(9, 5),  (0, 0), (8, 5),  (0, 0), (10, 5), (0, 0), (6, 4)],
            "dor": 3,
            "local_dor": "joelho direito",
        },
        {
            "nome": "Cenário 4 — Zona de Perigo (sem dor)",
            "semana_atual": [(20, 9), (18, 8), (15, 8), (20, 9), (12, 7), (18, 8), (16, 8)],
            "semana_2":     [(9, 6),  (0, 0),  (8, 5), (0, 0),  (11, 6), (0, 0), (7, 5)],
            "semana_3":     [(8, 5),  (0, 0),  (7, 5), (0, 0),  (10, 5), (0, 0), (6, 4)],
            "semana_4":     [(9, 5),  (0, 0),  (8, 5), (0, 0),  (10, 5), (0, 0), (6, 4)],
            "dor": 0,
        },
        {
            "nome": "Cenário 5 — Dor 5/10 (veto de dor, ACWR normal)",
            "semana_atual": [(10, 6), (0, 0), (8, 5), (0, 0), (12, 6), (0, 0), (6, 4)],
            "semana_2":     [(9, 6),  (0, 0), (7, 5), (0, 0), (11, 6), (0, 0), (5, 4)],
            "semana_3":     [(8, 5),  (0, 0), (8, 6), (0, 0), (10, 6), (0, 0), (6, 4)],
            "semana_4":     [(9, 6),  (0, 0), (7, 5), (0, 0), (10, 5), (0, 0), (5, 4)],
            "dor": 5,
            "local_dor": "tendão de Aquiles esquerdo",
        },
    ]

    for c in cenarios:
        print(f"\n{'='*60}")
        print(f"  {c['nome']}")
        print(f"{'='*60}")

        historico = construir_historico(
            semana_atual=c["semana_atual"],
            semana_2=c.get("semana_2"),
            semana_3=c.get("semana_3"),
            semana_4=c.get("semana_4"),
        )

        resultado = motor.calcular(
            historico=historico,
            dor_hoje=c.get("dor", 0),
            localizacao_dor=c.get("local_dor", ""),
        )

        print(resultado.exibir())


# ─────────────────────────────────────────────
# Modo interativo (entrada manual)
# ─────────────────────────────────────────────

def modo_interativo():
    """Permite inserir dados manualmente via terminal."""
    print("\n" + "="*60)
    print("  CORRENDO PELA VIDA — Entrada Manual")
    print("="*60)
    print("  Insira sua distância (km) e PSE para cada dia.")
    print("  Digite 0 0 para dias de descanso.\n")

    def ler_semana(nome: str) -> list[tuple[float, int]]:
        print(f"\n  {nome}")
        dias = []
        for i in range(1, 8):
            while True:
                try:
                    entrada = input(f"    Dia {i} (distância PSE): ").strip()
                    partes = entrada.split()
                    dist, pse = float(partes[0]), int(partes[1])
                    if dist == 0:
                        dias.append((0, 0))
                    else:
                        dias.append((dist, pse))
                    break
                except (ValueError, IndexError):
                    print("    Formato inválido. Ex: 10 7  ou  0 0 para descanso")
        return dias

    semana_atual = ler_semana("Semana atual (últimos 7 dias)")

    print("\n  Quantas semanas anteriores você tem? (1–3, ou 0 se for a primeira semana)")
    n_prev = int(input("  → ").strip())
    n_prev = max(0, min(3, n_prev))

    semanas_prev = []
    for i in range(1, n_prev + 1):
        semanas_prev.append(ler_semana(f"Semana {i+1} atrás"))

    while True:
        try:
            dor = int(input("\n  Dor hoje (0 = sem dor, 1–10): ").strip())
            if 0 <= dor <= 10:
                break
        except ValueError:
            pass

    local_dor = ""
    if dor > 0:
        local_dor = input("  Onde está a dor? (ex: joelho direito): ").strip()

    historico = HistoricoSemanas(
        semana_atual=sessoes_da_semana(semana_atual),
        semanas_prev=[sessoes_da_semana(s) for s in semanas_prev],
    )

    motor = MotorACWR()
    resultado = motor.calcular(historico, dor_hoje=dor, localizacao_dor=local_dor)
    print(resultado.exibir())


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interativo":
        modo_interativo()
    else:
        print("Rodando cenários de demonstração...")
        print("(Use  python acwr_motor.py --interativo  para entrada manual)\n")
        rodar_cenarios()
