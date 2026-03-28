"""
CORRENDO PELA VIDA — Coach IA Contextual v2
============================================
Motor de respostas baseado em templates inteligentes que leem:
  - ACWR + zona de risco
  - Perfil do corredor (RP, zonas de pace, nível)
  - Histórico de dor, streak e tendência de carga
  - Última atividade (para comparação de pace real vs sugerido)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from acwr_motor import ResultadoACWR, ZonaRisco, AcaoTreino

if TYPE_CHECKING:
    from perfil_service import ZonasRitmo, PerfilCorredor


# ─────────────────────────────────────────────
# Contexto do atleta (enriquecido com perfil)
# ─────────────────────────────────────────────

@dataclass
class CoachContexto:
    resultado:           Optional[ResultadoACWR]
    nivel:               str
    total_sessoes:       int
    total_km:            float
    media_pse:           float
    streak_dias:         int
    dor_local:           str
    tendencia_acwr:      str
    acwr_semana_ant:     float
    semanas_disponiveis: int
    # Novos campos v2
    zonas:               Optional["ZonasRitmo"] = None
    perfil:              Optional["PerfilCorredor"] = None
    ultimo_pace:         float = 0.0   # pace real da última sessão (min/km)
    ultimo_distancia:    float = 0.0   # km da última sessão
    ultimo_pse:          int   = 0     # PSE real da última sessão

    @property
    def acwr(self) -> float:
        return self.resultado.acwr if self.resultado else 0.0

    @property
    def zona(self) -> Optional[ZonaRisco]:
        return self.resultado.zona if self.resultado else None

    @property
    def dor(self) -> int:
        return self.resultado.dor_reportada if self.resultado else 0

    @property
    def carga_aguda(self) -> float:
        return self.resultado.carga_aguda if self.resultado else 0.0

    @property
    def carga_cronica(self) -> float:
        return self.resultado.carga_cronica if self.resultado else 0.0

    @property
    def variacao_carga_pct(self) -> float:
        if self.carga_cronica == 0:
            return 0.0
        return round(((self.carga_aguda - self.carga_cronica) / self.carga_cronica) * 100, 1)

    @property
    def em_calibracao(self) -> bool:
        return self.semanas_disponiveis < 4

    @property
    def tem_zonas(self) -> bool:
        return self.zonas is not None

    @property
    def tem_perfil_completo(self) -> bool:
        return self.perfil is not None and self.perfil.tem_rp


# ─────────────────────────────────────────────
# Classificador de Intenção
# ─────────────────────────────────────────────

class AnalisadorIntent:
    INTENTS: dict[str, list[str]] = {
        "meu_treino":   ["como foi meu treino", "meu treino foi", "o que achaste",
                          "avalie meu treino", "minha corrida", "como corri",
                          "meu pace", "meu ritmo real"],
        "acwr":         ["acwr", "carga", "aguda", "cronica", "ratio"],
        "dor":          ["doi", "dor", "lesao", "lesionar", "machucar", "machuco",
                         "joelho", "tornozelo", "tendao", "aquiles", "panturrilha",
                         "canela", "quadril", "lombar", "costas", "inflamado"],
        "amanha":       ["amanha", "proximo treino", "proxima sessao", "treinar amanha",
                         "hoje", "descanso", "treinar"],
        "zonas_pace":   ["pace", "ritmo", "zonas de ritmo", "qual ritmo", "que pace",
                         "velocidade de treino", "meu pace de treino"],
        "longao":       ["longao", "longona", "longo", "resistencia", "fim de semana"],
        "velocidade":   ["velocidade", "rapido", "tiro", "sprint", "intervalado",
                         "fartlek", "treino rapido", "5km", "10km"],
        "recuperacao":  ["recuperacao", "recuperar", "descansar", "descanso",
                         "cansaco", "cansado", "fadiga", "sono", "dormir"],
        "nutricao":     ["comer", "comida", "nutricao", "gel", "carboidrato",
                         "hidratacao", "beber", "agua", "eletrolito", "proteina"],
        "prova":        ["prova", "corrida", "race", "maratona", "meia maratona",
                         "10k", "5k", "competicao", "evento", "largada"],
        "progresso":    ["progresso", "evoluindo", "melhorando", "resultado",
                         "recorde", "pr", "personal", "evolucao"],
        "semana":       ["semana", "plano", "planejamento", "calendario"],
        "iniciante":    ["comecar", "inicio", "iniciante", "primeiro treino",
                         "nunca corri", "comecando"],
        "motivacao":    ["motivacao", "animo", "desanimado", "vontade", "preguica",
                         "nao quero", "dificil", "persistir"],
        "zona_hr":      ["zona", "frequencia cardiaca", "fc", "z1", "z2", "z3",
                         "z4", "z5", "aerobico", "anaerobico"],
        "volume":       ["volume", "quilometragem", "km por semana", "quanto correr"],
        "vdot":         ["vdot", "daniels", "rp", "recorde pessoal", "meu vdot"],
        "saudacao":     ["ola", "oi", "hey", "bom dia", "boa tarde", "boa noite",
                         "tudo bem", "como vai"],
    }

    def classificar(self, texto: str) -> list[str]:
        t = texto.lower()
        for o, d in [("ã","a"),("á","a"),("â","a"),("é","e"),("ê","e"),
                     ("í","i"),("ó","o"),("ô","o"),("ú","u"),("ç","c")]:
            t = t.replace(o, d)

        # "meu treino" tem frases completas — checar primeiro
        for frase in self.INTENTS.get("meu_treino", []):
            if frase in t:
                return ["meu_treino"] + [k for k in self._score_outros(t) if k != "meu_treino"]

        return self._score_outros(t)

    def _score_outros(self, t: str) -> list[str]:
        out = []
        for intent, palavras in self.INTENTS.items():
            score = sum(1 for p in palavras if p in t)
            if score > 0:
                out.append((intent, score))
        out.sort(key=lambda x: x[1], reverse=True)
        return [i for i, _ in out]


# ─────────────────────────────────────────────
# Coach IA
# ─────────────────────────────────────────────

class CoachIA:

    def __init__(self):
        self.analisador = AnalisadorIntent()

    # ── Análise proativa ──────────────────────

    def analise_proativa(self, ctx: CoachContexto) -> str:
        if ctx.resultado is None:
            intro = (
                "Olá! Sou seu Coach IA.\n\n"
                "Ainda não tenho dados suficientes. "
                "Registre seus primeiros treinos — ou use o botão de bootstrap na sidebar.\n\n"
            )
            if ctx.tem_perfil_completo:
                intro += (
                    f"Já vi seu perfil: **{ctx.perfil.rp_distancia} em {ctx.perfil.rp_str}** "
                    f"(VDOT {ctx.zonas.vdot:.1f}). Assim que tiver histórico, "
                    f"vou comparar seu pace real com as zonas ideais.\n\n"
                )
            intro += "O que você quer saber?"
            return intro

        partes = []
        z, acwr, var = ctx.zona, ctx.acwr, ctx.variacao_carga_pct

        # Status de carga
        if z == ZonaRisco.OTIMA:
            partes.append(f"Tudo em equilíbrio! ACWR {acwr:.2f} — zona ótima de adaptação.")
        elif z == ZonaRisco.SUBTREINO:
            partes.append(f"Carga baixa (ACWR {acwr:.2f}). Seu corpo pode estar se desadaptando.")
        elif z == ZonaRisco.ATENCAO:
            partes.append(
                f"⚠️ Atenção: carga dos últimos 7 dias subiu **{var:.0f}%** acima da média "
                f"(ACWR {acwr:.2f}). Zona de atenção."
            )
        else:
            partes.append(
                f"🚨 Zona de perigo! ACWR {acwr:.2f} — carga **{var:.0f}%** acima da base. "
                f"Risco real de lesão por sobrecarga."
            )

        # Dor
        if ctx.dor > 0 and ctx.dor_local:
            partes.append(
                f"Dor de **{ctx.dor}/10** em {ctx.dor_local} registrada. "
                f"{'Protocolo de proteção ativo.' if ctx.dor >= 4 else 'Monitore no próximo treino.'}"
            )

        # Comparação de pace (novidade v2)
        if ctx.tem_zonas and ctx.ultimo_pace > 0:
            z2 = ctx.zonas.rodagem_leve
            diff = ctx.ultimo_pace - (z2.pace_min + z2.pace_max) / 2
            def fmt(p):
                m = int(p); s = round((p-m)*60)
                return f"{m}:{s:02d}"
            if abs(diff) < 0.25:
                partes.append(
                    f"Sua última corrida ({fmt(ctx.ultimo_pace)}/km) ficou dentro da zona Z2 — ritmo ideal."
                )
            elif diff > 0.25:
                partes.append(
                    f"Seu último pace ({fmt(ctx.ultimo_pace)}/km) ficou **{diff*60:.0f}s/km mais lento** "
                    f"que o alvo Z2 ({z2.alvo_str}). Pode ser fadiga acumulada."
                )
            else:
                partes.append(
                    f"Seu último pace ({fmt(ctx.ultimo_pace)}/km) ficou **{abs(diff)*60:.0f}s/km mais rápido** "
                    f"que o alvo Z2 ({z2.alvo_str}). Verifique se não está saindo forte demais."
                )

        # Tendência
        if ctx.tendencia_acwr == "subindo" and acwr > 1.2:
            partes.append("A tendência de carga está em alta. Inclua um dia extra de recuperação.")
        elif ctx.tendencia_acwr == "caindo" and z == ZonaRisco.SUBTREINO:
            partes.append("Carga em queda — aumente progressivamente o volume.")

        # Streak
        if ctx.streak_dias >= 5:
            partes.append(
                f"Você está em {ctx.streak_dias} dias consecutivos! "
                "Inclua pelo menos 1 dia de descanso total esta semana."
            )
        elif ctx.streak_dias >= 3:
            partes.append(f"Série ativa de {ctx.streak_dias} dias — ótimo ritmo!")

        # Perfil
        if ctx.tem_perfil_completo:
            partes.append(
                f"Perfil calibrado: **{ctx.perfil.rp_distancia} em {ctx.perfil.rp_str}** "
                f"(VDOT {ctx.zonas.vdot:.1f}). Paces de treino personalizados ativos."
            )

        if ctx.em_calibracao:
            partes.append(
                f"_(Calibração: {ctx.semanas_disponiveis}/4 semanas. ACWR fica mais preciso com mais dados.)_"
            )

        partes.append("\nO que você quer saber?")
        return "\n\n".join(partes)

    # ── Resposta para pergunta livre ──────────

    def responder(self, pergunta: str, ctx: CoachContexto) -> str:
        intents = self.analisador.classificar(pergunta)
        if not intents:
            return self._generica(ctx)

        handlers = {
            "meu_treino":  self._resp_meu_treino,
            "saudacao":    self._resp_saudacao,
            "acwr":        self._resp_acwr,
            "dor":         self._resp_dor,
            "amanha":      self._resp_amanha,
            "zonas_pace":  self._resp_zonas_pace,
            "longao":      self._resp_longao,
            "velocidade":  self._resp_velocidade,
            "recuperacao": self._resp_recuperacao,
            "nutricao":    self._resp_nutricao,
            "prova":       self._resp_prova,
            "progresso":   self._resp_progresso,
            "semana":      self._resp_semana,
            "iniciante":   self._resp_iniciante,
            "motivacao":   self._resp_motivacao,
            "zona_hr":     self._resp_zona_hr,
            "volume":      self._resp_volume,
            "vdot":        self._resp_vdot,
        }
        return handlers.get(intents[0], self._generica)(ctx, pergunta)

    # ─────────────────────────────────────────
    # Handlers — todos recebem (ctx, pergunta)
    # ─────────────────────────────────────────

    def _resp_meu_treino(self, ctx: CoachContexto, _: str) -> str:
        """Análise do treino mais recente comparando com zones do perfil."""
        if ctx.ultimo_pace == 0:
            return "Ainda não tenho dados da última sessão. Registre um treino para eu analisar!"

        def fmt(p: float) -> str:
            m = int(p); s = round((p-m)*60)
            return f"{m}:{s:02d}/km"

        pace_real = ctx.ultimo_pace
        dist_real = ctx.ultimo_distancia
        pse_real  = ctx.ultimo_pse
        carga     = round(dist_real * pse_real, 1)

        linhas = [
            f"**Análise da última sessão:** {dist_real:.1f} km · {fmt(pace_real)} · PSE {pse_real}/10",
            f"Carga gerada: **{carga} u.a.**",
        ]

        if ctx.tem_zonas:
            z = ctx.zonas
            # Encontra a zona mais próxima
            zonas_ord = [
                ("Recuperação",  z.recuperacao.pace_min,  z.recuperacao.pace_max),
                ("Rodagem Leve", z.rodagem_leve.pace_min, z.rodagem_leve.pace_max),
                ("Longão",       z.longao.pace_min,       z.longao.pace_max),
                ("Limiar",       z.limiar.pace_min,       z.limiar.pace_max),
                ("Intervalado",  z.intervalado.pace_min,  z.intervalado.pace_max),
                ("Repetição",    z.repeticao.pace_min,    z.repeticao.pace_max),
            ]
            zona_real = None
            for nome, p_rapido, p_lento in zonas_ord:
                if p_rapido <= pace_real <= p_lento:
                    zona_real = nome
                    break

            if zona_real:
                linhas.append(f"Seu pace ficou na zona de **{zona_real}** — exatamente onde deveria estar.")
            elif pace_real < z.repeticao.pace_min:
                linhas.append(
                    f"Pace de {fmt(pace_real)} é **mais rápido que Z5+**. "
                    "Para esse esforço, verifique se era um treino de tiros mesmo."
                )
            elif pace_real > z.recuperacao.pace_max:
                diff_s = round((pace_real - z.recuperacao.pace_max) * 60)
                linhas.append(
                    f"Pace de {fmt(pace_real)} ficou **{diff_s}s/km mais lento** que o alvo de recuperação "
                    f"({fmt(z.recuperacao.pace_max)}). Fadiga ou terreno difícil?"
                )

            # PSE vs pace: detecta inconsistência
            pace_z2_alvo = (z.rodagem_leve.pace_min + z.rodagem_leve.pace_max) / 2
            if pse_real <= 5 and pace_real < z.limiar.pace_max:
                linhas.append(
                    "⚠️ PSE baixo mas pace de limiar — pode ser que o esforço percebido "
                    "esteja subestimado. Confie na frequência cardíaca como referência secundária."
                )
            elif pse_real >= 8 and pace_real > z.rodagem_leve.pace_min:
                linhas.append(
                    "PSE alto com pace de rodagem leve pode indicar fadiga acumulada ou "
                    "condições adversas (calor, umidade, terreno). Normal após dias de carga alta."
                )
        else:
            linhas.append(
                "_Cadastre seu RP no Perfil para eu comparar seu pace real com as zonas ideais do seu nível._"
            )

        # ACWR impacto
        linhas.append(
            f"\nEssa sessão somou **{carga} u.a.** à sua carga aguda (atual: {ctx.carga_aguda:.0f} u.a.). "
            f"ACWR: {ctx.acwr:.2f}."
        )

        return "\n\n".join(linhas)

    def _resp_zonas_pace(self, ctx: CoachContexto, _: str) -> str:
        if not ctx.tem_zonas:
            return (
                "Para ver suas zonas de pace personalizadas, cadastre seu Recorde Pessoal "
                "na aba **Perfil**. O app vai calcular seus ritmos usando a metodologia "
                "de Jack Daniels (VDOT)."
            )
        z = ctx.zonas
        def fmt(p): m=int(p); s=round((p-m)*60); return f"{m}:{s:02d}"
        return (
            f"**Suas zonas de pace** (VDOT {z.vdot:.1f} · {z.fonte_rp}):\n\n"
            f"| Zona | Nome | Faixa | PSE |\n"
            f"|------|------|-------|-----|\n"
            f"| Z1   | Recuperação | {fmt(z.recuperacao.pace_max)} – {fmt(z.recuperacao.pace_min)}/km | {z.recuperacao.pse_ref} |\n"
            f"| Z2   | Rodagem Leve | {fmt(z.rodagem_leve.pace_max)} – {fmt(z.rodagem_leve.pace_min)}/km | {z.rodagem_leve.pse_ref} |\n"
            f"| Z2/3 | Longão | {fmt(z.longao.pace_max)} – {fmt(z.longao.pace_min)}/km | {z.longao.pse_ref} |\n"
            f"| Z4   | Limiar | {fmt(z.limiar.pace_max)} – {fmt(z.limiar.pace_min)}/km | {z.limiar.pse_ref} |\n"
            f"| Z5   | Intervalado | {fmt(z.intervalado.pace_max)} – {fmt(z.intervalado.pace_min)}/km | {z.intervalado.pse_ref} |\n"
            f"| Z5+  | Repetição | {fmt(z.repeticao.pace_max)} – {fmt(z.repeticao.pace_min)}/km | {z.repeticao.pse_ref} |\n\n"
            f"Use essas faixas como referência nos treinos do card de amanhã."
        )

    def _resp_vdot(self, ctx: CoachContexto, _: str) -> str:
        if not ctx.tem_zonas:
            return (
                "VDOT é a medida de capacidade aeróbica desenvolvida por Jack Daniels "
                "(Running Formula). Cadastre seu RP no Perfil e eu calculo o seu!"
            )
        return (
            f"**Seu VDOT: {ctx.zonas.vdot:.1f}**\n\n"
            f"Calculado a partir do {ctx.zonas.fonte_rp}.\n\n"
            "O VDOT é uma estimativa do seu VO2max funcional em corrida. "
            "Não é o mesmo que o VO2max de laboratório, mas é excelente para "
            "calibrar ritmos de treino.\n\n"
            f"**Referência de VDOT por nível:**\n"
            "- Iniciante: 30–40\n"
            "- Intermediário: 40–52\n"
            "- Avançado: 52–65\n"
            "- Elite nacional: 65+\n\n"
            "Melhore o VDOT treinando consistentemente em Z2 (80% do volume) "
            "e adicionando 1–2 sessões de qualidade por semana."
        )

    def _resp_saudacao(self, ctx: CoachContexto, _: str) -> str:
        if ctx.resultado is None:
            return "Oi! Registre seu primeiro treino para ativar a análise de carga."
        extras = ""
        if ctx.tem_perfil_completo:
            extras = f" | VDOT {ctx.zonas.vdot:.1f}"
        return (
            f"Olá! ACWR {ctx.acwr:.2f} ({ctx.zona.value if ctx.zona else '—'}){extras} · "
            f"{ctx.total_sessoes} sessões · {ctx.total_km:.0f} km. O que vamos trabalhar?"
        )

    def _resp_acwr(self, ctx: CoachContexto, _: str) -> str:
        if ctx.resultado is None:
            return (
                "ACWR = Carga Aguda (7d) ÷ Carga Crônica (média 28d). "
                "Registre treinos para eu calcular o seu!"
            )
        return (
            f"**ACWR atual: {ctx.acwr:.3f}**\n\n"
            f"- Carga aguda (7d): {ctx.carga_aguda:.0f} u.a.\n"
            f"- Carga crônica (28d): {ctx.carga_cronica:.0f} u.a.\n"
            f"- Variação: {'+' if ctx.variacao_carga_pct>=0 else ''}{ctx.variacao_carga_pct:.0f}%\n"
            f"- Tendência: {ctx.tendencia_acwr}\n\n"
            f"{'⚠️ Monitore os próximos dias.' if ctx.acwr > 1.3 else '✅ Zona segura de adaptação.'}"
        )

    def _resp_dor(self, ctx: CoachContexto, pergunta: str) -> str:
        regioes = {
            "joelho":"joelho","tornozelo":"tornozelo","panturrilha":"panturrilha",
            "aquiles":"tendão de Aquiles","tibial":"canela","quadril":"quadril","lombar":"lombar",
        }
        regiao = next((v for k,v in regioes.items() if k in pergunta.lower()), None)
        if ctx.dor >= 4 or regiao == "tendão de Aquiles":
            return (
                f"Dor {ctx.dor}/10{(' em '+ctx.dor_local) if ctx.dor_local else ''} requer atenção.\n\n"
                "**Protocolo:**\n1. Pare o treino de impacto\n2. Gelo 15 min 3x/dia\n"
                "3. Sem corrida por 24–48h\n4. Se persistir, fisioterapeuta\n\n"
                "Amanhã será substituído por mobilidade no plano."
            )
        if regiao == "panturrilha":
            acwr_msg = f"ACWR {ctx.acwr:.2f} {'contribui — reduza volume.' if ctx.acwr>1.2 else 'está ok.'}"
            return (
                "**Dor em panturrilha:** causas comuns — volume alto, subida rápida de intensidade.\n\n"
                "**Protocolo:** ↓ volume 20% · elevação de calcanhar 3×15 · "
                f"alongamento 3×30s · hidrate bem.\n\n{acwr_msg}"
            )
        if ctx.dor == 0:
            return (
                "Ótimo — sem dor! Para manter:\n"
                "- Volume semanal máx +10%/semana\n"
                "- 1–2 dias de descanso total\n"
                "- Mobilidade 2×/semana\n"
                f"- ACWR entre 0.8–1.3 (hoje: {ctx.acwr:.2f})"
            )
        return (
            f"Dor leve {ctx.dor}/10. Aqueca 10 min antes. "
            "Se piorar durante — pare. Se mantiver — reduza 25% do volume. "
            "Registre a localização para eu adaptar o plano."
        )

    def _resp_amanha(self, ctx: CoachContexto, _: str) -> str:
        if ctx.resultado is None:
            return "Registre ao menos uma semana de treinos para sugestão personalizada."
        acao = ctx.resultado.acao
        pace_info = ""
        if ctx.tem_zonas:
            z = ctx.zonas
            pace_info = f"\n\n**Ritmo sugerido:** {z.rodagem_leve.faixa_str} (Z2)"
        if acao == AcaoTreino.TREINO_BLOQUEADO:
            return (
                f"Amanhã: **descanso ou mobilidade**.\n"
                f"{'Dor '+str(ctx.dor)+'/10.' if ctx.dor>=4 else 'ACWR '+str(ctx.acwr)+' na zona de perigo.'}\n\n"
                "Opções: mobilidade 30–45 min · caminhada · natação leve."
            )
        if acao == AcaoTreino.TREINO_REDUZIDO:
            return (
                f"Amanhã: **rodagem leve −25%** (ACWR {ctx.acwr:.2f} + dor {ctx.dor}/10)."
                + pace_info +
                "\n\nSe piorar a dor no aquecimento — pare."
            )
        if acao == AcaoTreino.TREINO_MANTIDO and ctx.acwr > 1.3:
            return (
                f"Amanhã: **treino mantido + atenção** (ACWR {ctx.acwr:.2f})."
                + pace_info +
                "\n\nMonitore: fadiga nas pernas, FC elevada, dor articular."
            )
        return (
            f"Amanhã: **treino normal** (ACWR {ctx.acwr:.2f} — zona ótima)."
            + pace_info +
            "\n\nExecute com confiança. Durma bem hoje!"
        )

    def _resp_longao(self, ctx: CoachContexto, _: str) -> str:
        pace_info = ""
        if ctx.tem_zonas:
            z = ctx.zonas.longao
            pace_info = f"\n\n**Seu pace de longão:** {z.faixa_str} (com base no VDOT {ctx.zonas.vdot:.1f})"
        bases = {
            "Iniciante":     "6–9 km. Combine corrida e caminhada. Objetivo: tempo em movimento.",
            "Intermediário": "14–18 km em Z2. Nutricao a partir do km 10–12.",
            "Avançado":      "20–28 km. Opcional: últimos 3–5 km em ritmo de maratona.",
        }
        base = bases.get(ctx.nivel, bases["Intermediário"])
        nutricao = "\n\n**Nutrição:** café 2h antes · gel a cada 45 min (>75 min) · água a cada 20 min."
        return f"**Longão para {ctx.nivel}:** {base}{pace_info}{nutricao}"

    def _resp_velocidade(self, ctx: CoachContexto, _: str) -> str:
        if ctx.acwr > 1.3:
            return (
                f"ACWR {ctx.acwr:.2f} — não é momento para velocidade. "
                "Tiros aumentam a carga aguda. Espere o ACWR < 1.2."
            )
        pace_info = ""
        if ctx.tem_zonas:
            z5 = ctx.zonas.intervalado
            z6 = ctx.zonas.repeticao
            pace_info = (
                f"\n\n**Seus paces personalizados:**\n"
                f"- Intervalado (Z5): {z5.faixa_str}\n"
                f"- Repetição/Sprint (Z5+): {z6.faixa_str}"
            )
        return (
            "**Progressão de velocidade:**\n"
            "1. Strides — 6–8×80 m após rodagem leve\n"
            "2. Fartlek livre — acelerações espontâneas\n"
            "3. Intervalado curto — 6–10×400 m\n"
            "4. Intervalado longo — 4–6×1000 m\n"
            "5. Tempo run — 20–35 min no limiar"
            + pace_info
        )

    def _resp_recuperacao(self, ctx: CoachContexto, _: str) -> str:
        base = (
            "**Pilares da recuperação:**\n\n"
            "- **Sono:** 7–9h. GH pico entre 23h–1h\n"
            "- **Nutrição pós-treino:** janela 30–45 min (proteína + carb)\n"
            "- **Hidratação:** urina amarela clara = ok\n"
            "- **Foam roller:** panturrilha, TI, glúteo — 60s/região\n"
            "- **Banho frio:** 10–15 min reduz inflamação\n"
        )
        if ctx.streak_dias >= 4:
            return f"Com {ctx.streak_dias} dias consecutivos, recuperação é prioridade!\n\n" + base
        return base

    def _resp_nutricao(self, ctx: CoachContexto, _: str) -> str:
        return (
            "**Nutrição para corredores:**\n\n"
            "**Pré-treino (1–2h):** aveia, pão integral, banana — baixo/médio IG\n\n"
            "**Durante (>60 min):** 30–60g carb/hora · 400–700 ml água/hora\n\n"
            "**Pós-treino (30–45 min):** 20–30g proteína + 40–60g carb\n\n"
            "**Hidratação geral:** 35 ml/kg/dia + repõe perdido no treino"
        )

    def _resp_prova(self, ctx: CoachContexto, pergunta: str) -> str:
        taper = (
            "\n\n**Taper:**\n"
            "- 2 semanas antes: volume −20%\n"
            "- 1 semana antes: volume −40%, mantém intensidade\n"
            "- 3 dias antes: rodagens leves 30–40 min Z2"
        )
        if ctx.acwr > 1.3:
            return f"ACWR {ctx.acwr:.2f} — priorize recuperação antes da prova." + taper
        pace_info = ""
        if ctx.tem_zonas and "maratona" in pergunta.lower():
            z3 = ctx.zonas.longao
            pace_info = f"\n\nSeu pace de maratona estimado: {z3.faixa_str}"
        return (
            "**Preparação para prova:**\n"
            "1. Base (4–8 sem): Z2 predominante\n"
            "2. Qualidade (4–8 sem): intervalados + tempo run\n"
            "3. Taper (1–2 sem): redução de volume"
            + pace_info + taper
        )

    def _resp_progresso(self, ctx: CoachContexto, _: str) -> str:
        if ctx.total_sessoes < 5:
            return "Continue registrando — em breve mostrarei sua evolução de carga e pace!"
        vdot_info = f" | VDOT {ctx.zonas.vdot:.1f}" if ctx.tem_zonas else ""
        return (
            f"**Seu progresso:**\n\n"
            f"- {ctx.total_sessoes} sessões · {ctx.total_km:.0f} km total\n"
            f"- PSE médio: {ctx.media_pse:.1f}/10\n"
            f"- Streak: {ctx.streak_dias} dias\n"
            f"- ACWR: {ctx.acwr:.2f} ({ctx.zona.value if ctx.zona else '—'}){vdot_info}\n\n"
            "Adaptações reais levam 6–8 semanas de consistência."
        )

    def _resp_semana(self, ctx: CoachContexto, _: str) -> str:
        pace_ref = ""
        if ctx.tem_zonas:
            z = ctx.zonas
            pace_ref = (
                f"\n\n**Referência de paces ({z.fonte_rp}):**\n"
                f"- Rodagem leve: {z.rodagem_leve.faixa_str}\n"
                f"- Longão: {z.longao.faixa_str}\n"
                f"- Limiar: {z.limiar.faixa_str}\n"
                f"- Intervalado: {z.intervalado.faixa_str}"
            )
        return (
            f"**Plano semanal ({ctx.nivel}):**\n\n"
            "Seg: Recuperação · Ter: Qualidade · Qua: Rodagem · "
            "Qui: Qualidade · Sex: Leve · Sáb: Longão · Dom: Mobilidade"
            + pace_ref +
            (f"\n\n{'ACWR alto — reduza 1 sessão de qualidade.' if ctx.acwr > 1.3 else 'ACWR ok — plano completo.'}")
        )

    def _resp_iniciante(self, ctx: CoachContexto, _: str) -> str:
        return (
            "**Para começar do zero:**\n\n"
            "Sem. 1–4: run/walk — 1 min correndo + 2 min caminhando, 20–30 min, 3×/semana\n\n"
            "Sem. 5–8: 5 min correndo + 1 min caminhando\n\n"
            "**Meta:** correr 30 min contínuos\n\n"
            "Sinal de ritmo certo: consegue falar frases completas enquanto corre. "
            "Se não consegue, está rápido demais."
        )

    def _resp_motivacao(self, ctx: CoachContexto, _: str) -> str:
        return (
            "Dias assim fazem parte do processo. A **disciplina** leva mais longe que a motivação.\n\n"
            "**Que funciona:** comprometa-se com 10 min. Se quiser parar depois, pare. "
            "(Raramente vai querer.)\n\n"
            f"Você já tem {ctx.total_km:.0f} km registrados — "
            "cada um deles foi uma decisão de treinar quando o ânimo estava baixo."
        )

    def _resp_zona_hr(self, ctx: CoachContexto, _: str) -> str:
        fc_info = ""
        if ctx.perfil and ctx.perfil.fc_max > 0:
            fc = ctx.perfil.fc_max
            fc_info = (
                f"\n\n**Suas faixas de FC** (FCmax {fc} bpm):\n"
                f"| Zona | bpm |\n|------|-----|\n"
                f"| Z1 | < {int(fc*0.60)} |\n"
                f"| Z2 | {int(fc*0.60)}–{int(fc*0.70)} |\n"
                f"| Z3 | {int(fc*0.70)}–{int(fc*0.80)} |\n"
                f"| Z4 | {int(fc*0.80)}–{int(fc*0.90)} |\n"
                f"| Z5 | > {int(fc*0.90)} |"
            )
        return (
            "**Zonas de intensidade:**\n\n"
            "| Zona | %FCmax | Sensação | Uso |\n"
            "|------|--------|----------|-----|\n"
            "| Z1 | <60% | Caminhada | Recuperação |\n"
            "| Z2 | 60–70% | Conversa fácil | Base (80% do volume) |\n"
            "| Z3 | 70–80% | Frases curtas | Transição |\n"
            "| Z4 | 80–90% | Difícil | Limiar |\n"
            "| Z5 | >90% | Máximo | Tiros curtos |\n\n"
            "**Regra 80/20:** 80% do volume em Z1/Z2."
            + fc_info
        )

    def _resp_volume(self, ctx: CoachContexto, _: str) -> str:
        sugestoes = {
            "Iniciante":     "20–30 km/semana",
            "Intermediário": "40–60 km/semana",
            "Avançado":      "70–100+ km/semana",
        }
        return (
            f"**Para {ctx.nivel}:** {sugestoes.get(ctx.nivel,'30–50 km/semana')}\n\n"
            "**Regra:** nunca aumente mais de **10% por semana**.\n\n"
            f"Sua base crônica atual: {ctx.carga_cronica:.0f} u.a./semana — "
            "isso representa sua capacidade real de absorver treino."
        )

    def _generica(self, ctx: CoachContexto, _: str = "") -> str:
        sugestoes = [
            "Como foi meu treino?",
            "Quais são meus paces de treino?",
            "O que fazer amanhã?",
            "Como melhorar meu VDOT?",
            "Como fazer um longão?",
        ]
        return (
            "Não entendi bem. Posso ajudar com:\n\n"
            + "\n".join(f"- {s}" for s in sugestoes)
            + f"\n\nStatus: ACWR {ctx.acwr:.2f} | {ctx.zona.value if ctx.zona else '—'}"
        )
