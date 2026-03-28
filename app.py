"""
CORRENDO PELA VIDA — MVP Final v4 (Streamlit)
==============================================
Execute: streamlit run app.py
Deps:    pip install streamlit pandas matplotlib reportlab
"""

import io
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from acwr_motor import (
    HistoricoSemanas, MotorACWR, ResultadoACWR,
    SessaoTreino, ZonaRisco, AcaoTreino,
)
from treino_gerador import (
    GeradorTreino, NivelCorredor,
    TipoTreino, NOMES_DIA, TEMPLATE_SEMANAL, CATALOGO,
)
from dados_bootstrap import popular_dados_iniciais, calcular_serie_acwr
from coach_ia import CoachIA, CoachContexto
from perfil_service import (
    PerfilCorredor, ZonasRitmo, PaceZona,
    calcular_zonas, salvar_perfil, carregar_perfil,
    _fmt_pace, prever_tempos, ajustar_vdot,
)
from strava_service import StravaService
from gamificacao import (
    nivel_atual, avaliar_badges, NivelAtleta,
    calcular_semanas_seguras, calcular_pct_zona_otima,
)
from relatorio_pdf import gerar_pdf

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Correndo pela Vida",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Syne',sans-serif!important}
.block-container{padding-top:1.2rem;padding-bottom:3rem}

/* Métricas */
.metric-card{background:#16161f;border:1px solid #2a2a3e;border-radius:14px;padding:.9rem 1rem;text-align:center}
.metric-label{color:#6b7280;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.3rem}
.metric-value{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;line-height:1;margin-bottom:.15rem}
.metric-sub{color:#6b7280;font-size:.72rem}

/* Cores zona */
.zona-otima{color:#34d399}.zona-atencao{color:#fbbf24}.zona-perigo{color:#f87171}
.zona-bloqueado{color:#ef4444}.zona-subtreino{color:#60a5fa}

/* HERO: Treino de amanhã */
.hero-card{background:linear-gradient(135deg,#0d0d1f 0%,#1a1040 100%);
  border:1px solid #4f46e5;border-radius:20px;padding:1.6rem 1.8rem}
.hero-label{color:#818cf8;font-size:.75rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.1em;margin-bottom:.4rem}
.hero-title{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;
  color:#fff;line-height:1.2;margin-bottom:.3rem}
.hero-meta{color:#a5b4fc;font-size:.85rem;margin-bottom:1rem}
.hero-estrutura{background:rgba(79,70,229,.12);border-left:3px solid #6366f1;
  border-radius:0 10px 10px 0;padding:.8rem 1rem;font-size:.85rem;
  color:#c7d2fe;line-height:1.6;margin:.8rem 0}
.hero-dica{background:rgba(5,150,105,.1);border-left:3px solid #059669;
  border-radius:0 10px 10px 0;padding:.65rem 1rem;font-size:.8rem;
  color:#6ee7b7;line-height:1.5}
.hero-justif{background:rgba(234,179,8,.07);border:1px solid rgba(234,179,8,.2);
  border-radius:8px;padding:.6rem .9rem;font-size:.78rem;color:#fde68a;margin-top:.7rem}

/* Risco card */
.risco-card{border-radius:16px;padding:1.2rem 1.4rem;margin-bottom:.4rem}
.risco-otima{background:#001f0f;border:1px solid #065f46}
.risco-atencao{background:#1f1500;border:1px solid #b45309}
.risco-perigo{background:#1f0000;border:1px solid #991b1b}
.risco-titulo{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700}
.risco-corpo{font-size:.83rem;margin-top:.4rem;line-height:1.55;opacity:.9}

/* Badges */
.badge-grid{display:flex;flex-wrap:wrap;gap:.4rem;margin:.5rem 0}
.badge-item{background:#16161f;border:1px solid #2a2a3e;border-radius:8px;
  padding:.3rem .7rem;font-size:.78rem;color:#d1d5db}
.badge-item.on{background:#0f2238;border-color:#1d4ed8;color:#93c5fd}
.nivel-card{background:linear-gradient(135deg,#0d0d1a,#1a1030);
  border-radius:14px;padding:1rem 1.2rem;text-align:center;
  border:1px solid #312e81;margin-bottom:.8rem}

/* Treino card (secundário) */
.treino-badge{display:inline-block;padding:.18rem .6rem;border-radius:16px;
  font-size:.7rem;font-weight:600;margin-right:.3rem;margin-bottom:.3rem}
.badge-zona{background:#1e293b;color:#93c5fd}
.badge-dist{background:#14291f;color:#6ee7b7}
.badge-tempo{background:#1f1b0e;color:#fde68a}
.badge-pse{background:#1f1215;color:#fca5a5}
.badge-pace{background:#1b1029;color:#c084fc}

/* Pace box */
.pace-box{background:#0f0f18;border:1px solid #312e6a;border-radius:10px;
  padding:.65rem .9rem;margin:.4rem 0}
.pace-zona-nome{font-size:.7rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.06em;margin-bottom:.15rem}
.pace-faixa{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700}
.pace-desc{font-size:.68rem;color:#6b7280;margin-top:.1rem}

/* Strava */
.strava-box{background:#0a160e;border:1px solid #1a3a20;border-radius:12px;
  padding:.9rem 1.1rem;margin-bottom:.6rem}

/* Calendário */
.cal-wrap{display:grid;grid-template-columns:repeat(7,1fr);gap:.3rem;margin:.4rem 0}
.cal-cell{border-radius:9px;padding:.5rem .2rem;text-align:center;
  font-size:.68rem;border:1px solid transparent}
.cal-descanso{background:#0d0d12;border-color:#1e1e2e;opacity:.55}
.cal-leve{background:#071a10;border-color:#065f46}
.cal-moderado{background:#1a150a;border-color:#78350f}
.cal-forte{background:#1a0a0a;border-color:#7f1d1d}
.cal-hoje{outline:2px solid #4f46e5;outline-offset:1px}
.cal-label{color:#6b7280;font-weight:600;text-transform:uppercase;font-size:.58rem;margin-bottom:.15rem}
.cal-emoji{font-size:1.15rem;line-height:1;margin:.1rem 0}
.cal-nome{color:#9ca3af;font-size:.62rem;line-height:1.2}
.cal-dist{font-size:.6rem;margin-top:.1rem;font-weight:600}
.cal-pace{font-size:.56rem;color:#7c3aed;margin-top:.05rem}

/* Prova predict */
.prova-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;margin:.5rem 0}
.prova-card{background:#0a0f1a;border:1px solid #1e2d4a;border-radius:10px;
  padding:.8rem .6rem;text-align:center}
.prova-nome{color:#6b7280;font-size:.68rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:.3rem}
.prova-tempo{font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:800;color:#60a5fa}
.prova-pace{color:#6b7280;font-size:.65rem;margin-top:.2rem}

/* Alertas inline */
.alerta-atencao{background:#1f1500;border:1px solid #b45309;border-radius:10px;padding:.7rem 1rem;color:#fbbf24;font-size:.82rem;margin:.4rem 0}
.alerta-perigo{background:#1f0000;border:1px solid #991b1b;border-radius:10px;padding:.7rem 1rem;color:#f87171;font-size:.82rem;margin:.4rem 0}
.alerta-ok{background:#001f0f;border:1px solid #065f46;border-radius:10px;padding:.7rem 1rem;color:#34d399;font-size:.82rem;margin:.4rem 0}

section[data-testid="stSidebar"]{background:#0d0d16;border-right:1px solid #1e1e2e}
.stButton>button{background:linear-gradient(135deg,#4f46e5,#7c3aed)!important;
  color:white!important;border:none!important;border-radius:10px!important;
  font-weight:600!important;padding:.55rem 1.3rem!important}
.stButton>button:hover{opacity:.88!important}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────
CSV_PATH = Path("data/treinos.csv")
CSV_COLUNAS = ["data","distancia_km","tempo_min","pse","dor","local_dor",
               "nivel","pace_min_km","carga","notas"]
ZONA_CORES = {
    ZonaRisco.OTIMA:     ("zona-otima",     "🟢", "Ótima"),
    ZonaRisco.ATENCAO:   ("zona-atencao",   "🟡", "Atenção"),
    ZonaRisco.PERIGO:    ("zona-perigo",    "🔴", "Perigo"),
    ZonaRisco.BLOQUEADO: ("zona-bloqueado", "⛔", "Bloqueado"),
    ZonaRisco.SUBTREINO: ("zona-subtreino", "🔵", "Subtreino"),
}
INT_CLASSE = {
    TipoTreino.RECUPERACAO:("cal-leve","#34d399"),
    TipoTreino.RODAGEM_LEVE:("cal-leve","#34d399"),
    TipoTreino.RODAGEM_MODERADA:("cal-moderado","#fbbf24"),
    TipoTreino.RODAGEM_PESADA:("cal-forte","#f87171"),
    TipoTreino.PROGRESSIVO_CURTO:("cal-moderado","#fbbf24"),
    TipoTreino.PROGRESSIVO_LONGO:("cal-forte","#f87171"),
    TipoTreino.TEMPO_RUN:("cal-forte","#f87171"),
    TipoTreino.FARTLEK_LIVRE:("cal-moderado","#fbbf24"),
    TipoTreino.FARTLEK_ESTRUTURADO:("cal-forte","#f87171"),
    TipoTreino.INTERVALADO_CURTO:("cal-forte","#f87171"),
    TipoTreino.INTERVALADO_LONGO:("cal-forte","#f87171"),
    TipoTreino.HILL_REPEATS:("cal-forte","#f87171"),
    TipoTreino.STRIDES:("cal-moderado","#fbbf24"),
    TipoTreino.LONGAO_LEVE:("cal-moderado","#fbbf24"),
    TipoTreino.LONGAO_PROGRESSIVO:("cal-forte","#f87171"),
    TipoTreino.LONGAO_ESPECIAL:("cal-forte","#f87171"),
    TipoTreino.DESCANSO_ATIVO:("cal-descanso","#6b7280"),
    TipoTreino.MOBILIDADE:("cal-descanso","#6b7280"),
}

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def garantir_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        pd.DataFrame(columns=CSV_COLUNAS).to_csv(CSV_PATH, index=False)

def carregar_df() -> pd.DataFrame:
    garantir_csv()
    df = pd.read_csv(CSV_PATH)
    if df.empty:
        return df
    df["data"] = pd.to_datetime(df["data"]).dt.date
    if "notas" not in df.columns:
        df["notas"] = ""
    return df.sort_values("data", ascending=False).reset_index(drop=True)

def salvar_sessao(dist, tempo, pse, dor, local_dor, nivel, notas=""):
    pace  = round(tempo / dist, 2) if dist > 0 else 0.0
    carga = round(dist * pse, 2)
    nova  = pd.DataFrame([{
        "data": date.today().isoformat(), "distancia_km": dist,
        "tempo_min": tempo, "pse": pse, "dor": dor, "local_dor": local_dor,
        "nivel": nivel.value, "pace_min_km": pace, "carga": carga, "notas": notas,
    }])
    garantir_csv()
    # Garante coluna notas no CSV existente
    if CSV_PATH.exists():
        df_ex = pd.read_csv(CSV_PATH)
        if "notas" not in df_ex.columns:
            df_ex["notas"] = ""
            df_ex.to_csv(CSV_PATH, index=False)
    nova.to_csv(CSV_PATH, mode="a", header=False, index=False)

def df_para_historico(df: pd.DataFrame) -> HistoricoSemanas:
    if df.empty: return HistoricoSemanas()
    hoje = date.today()
    def ss(ini, fim):
        mask = (df["data"] >= ini) & (df["data"] <= fim)
        out = []
        for _, r in df[mask].iterrows():
            d, p = float(r["distancia_km"]), int(r["pse"])
            if d > 0 and p > 0:
                try: out.append(SessaoTreino(distancia_km=d, pse=p))
                except: pass
        return out
    sw = ss(hoje - timedelta(days=6), hoje)
    prev = []
    for i in range(1, 4):
        s = ss(hoje - timedelta(days=6+i*7), hoje - timedelta(days=i*7))
        if s: prev.append(s)
    return HistoricoSemanas(semana_atual=sw, semanas_prev=prev)

def calcular_streak(df: pd.DataFrame) -> int:
    if df.empty: return 0
    datas = sorted(df["data"].unique(), reverse=True)
    streak, dia = 0, date.today()
    for d in datas:
        if d == dia or d == dia - timedelta(days=1):
            streak += 1; dia = d - timedelta(days=1)
        else: break
    return streak

def calcular_tendencia(serie: pd.DataFrame) -> tuple[str, float]:
    if len(serie) < 8: return "estável", 0.0
    a_cur = serie["acwr"].dropna().iloc[-1]
    a_ant = serie["acwr"].dropna().iloc[-8]
    d = a_cur - a_ant
    if d > 0.05: return "subindo", round(a_ant, 3)
    if d < -0.05: return "caindo", round(a_ant, 3)
    return "estável", round(a_ant, 3)

def pace_str(v: float) -> str:
    if v <= 0: return "—"
    m = int(v); s = round((v - m) * 60)
    return f"{m}'{s:02d}\"/km"

# ─────────────────────────────────────────────
# Gráfico ACWR
# ─────────────────────────────────────────────

def render_grafico_acwr(serie: pd.DataFrame):
    if serie.empty or len(serie) < 3:
        st.info("Registre pelo menos 3 sessões para ver o gráfico de tendência.")
        return
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5.5),
                                    gridspec_kw={"height_ratios": [2, 1]}, sharex=True)
    fig.patch.set_facecolor("#0f0f13")
    for ax in (ax1, ax2):
        ax.set_facecolor("#16161f")
        ax.tick_params(colors="#6b7280", labelsize=8.5)
        ax.spines[:].set_color("#2a2a3e")

    datas = pd.to_datetime(serie["data"])
    ax1.fill_between(datas, serie["aguda"],   alpha=0.18, color="#818cf8")
    ax1.fill_between(datas, serie["cronica"], alpha=0.18, color="#34d399")
    ax1.plot(datas, serie["aguda"],   color="#818cf8", lw=2,   label="Aguda (7d)")
    ax1.plot(datas, serie["cronica"], color="#34d399", lw=2,   label="Crônica (28d)", linestyle="--")
    ax1.set_ylabel("Carga (u.a.)", color="#9ca3af", fontsize=8.5)
    ax1.legend(loc="upper left", facecolor="#16161f", edgecolor="#2a2a3e",
               labelcolor="#d1d5db", fontsize=8)
    ax1.grid(axis="y", color="#2a2a3e", linestyle="--", alpha=0.4)

    acwr_vals = serie["acwr"].fillna(method="ffill")
    ax2.axhspan(0.0, 0.8, alpha=0.15, color="#60a5fa", zorder=0)
    ax2.axhspan(0.8, 1.3, alpha=0.20, color="#34d399", zorder=0)
    ax2.axhspan(1.3, 1.5, alpha=0.20, color="#fbbf24", zorder=0)
    ax2.axhspan(1.5, 3.0, alpha=0.18, color="#f87171", zorder=0)
    for y, c in [(0.8,"#34d399"),(1.3,"#fbbf24"),(1.5,"#f87171")]:
        ax2.axhline(y, color=c, lw=0.6, linestyle=":")
    ax2.plot(datas, acwr_vals, color="#e879f9", lw=2.2, zorder=5, label="ACWR")
    if len(datas) > 0 and not acwr_vals.empty:
        ax2.scatter([datas.iloc[-1]], [acwr_vals.iloc[-1]], color="#e879f9", s=55, zorder=6)
    ax2.set_ylim(0, max(3.0, float(acwr_vals.max()) + 0.3))
    ax2.set_ylabel("ACWR", color="#9ca3af", fontsize=8.5)
    ax2.legend(loc="upper left", facecolor="#16161f", edgecolor="#2a2a3e",
               labelcolor="#d1d5db", fontsize=8)
    ax2.grid(axis="y", color="#2a2a3e", linestyle="--", alpha=0.35)
    ax2r = ax2.twinx()
    ax2r.set_facecolor("#16161f"); ax2r.set_ylim(ax2.get_ylim())
    ax2r.tick_params(left=False, right=False, labelleft=False, labelright=False)
    for y, lbl, cor in [(0.4,"Subtreino","#60a5fa"),(1.05,"Ótima","#34d399"),
                         (1.4,"Atenção","#fbbf24"),(1.65,"Perigo","#f87171")]:
        if y < ax2.get_ylim()[1]:
            ax2r.text(0.98, y, lbl, transform=ax2r.get_yaxis_transform(),
                      ha="right", va="center", fontsize=7.5, color=cor, alpha=0.85)
    ax2.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m"))
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), dpi=130, bbox_inches="tight")
    buf.seek(0); plt.close(fig)
    st.image(buf, use_container_width=True)

# ─────────────────────────────────────────────
# Componentes UI
# ─────────────────────────────────────────────

def render_metric_card(label, value, sub, css_class=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {css_class}">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


def render_hero_treino(treino, justificativa, volume_reduzido, zonas, dia_str):
    """Card HERO — destaque máximo para o treino de amanhã."""
    dist    = treino.distancia_reduzida if volume_reduzido else treino.distancia_ref_km
    dist_s  = f"{dist:.1f} km" if dist > 0 else "—"
    vol_tag = " (−25%)" if volume_reduzido else ""

    badges_html = (
        f'<span class="treino-badge badge-zona">Zona {treino.zona_principal}</span>'
        f'<span class="treino-badge badge-dist">📍 {dist_s}{vol_tag}</span>'
        f'<span class="treino-badge badge-tempo">⏱ ~{treino.duracao_ref_min} min</span>'
        f'<span class="treino-badge badge-pse">PSE est. {treino.pse_estimado}/10</span>'
    )
    pace_html = ""
    if zonas:
        zona_p = zonas.zona_por_tipo(treino.tipo.value)
        if zona_p:
            badges_html += f'<span class="treino-badge badge-pace">🎯 {zona_p.alvo_str}</span>'
            pace_html = (
                f'<div class="pace-box" style="margin-top:.6rem">'
                f'<div class="pace-zona-nome" style="color:{zona_p.cor}">{zona_p.zona_hr} · {zona_p.nome}</div>'
                f'<div class="pace-faixa" style="color:{zona_p.cor}">{zona_p.faixa_str}</div>'
                f'<div class="pace-desc">{zona_p.descricao} · PSE {zona_p.pse_ref}</div>'
                f'</div>'
            )

    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-label">Treino de amanhã · {dia_str}</div>
        <div class="hero-title">{treino.emoji} {treino.nome}</div>
        <div class="hero-meta">{treino.nivel.value} · {treino.intensidade.value}</div>
        <div>{badges_html}</div>
        <div class="hero-estrutura">{treino.estrutura}</div>
        <div class="hero-dica">💡 <strong>Coach:</strong> {treino.dica_coach}</div>
        <div class="hero-justif">⚙️ {justificativa}</div>
        {pace_html}
    </div>""", unsafe_allow_html=True)


def render_risco_card(resultado):
    """Card de risco compacto e visual."""
    if resultado is None:
        st.markdown('<div class="alerta-ok">📊 Registre treinos para ativar o motor ACWR.</div>',
                    unsafe_allow_html=True)
        return
    z = resultado.zona
    if z in (ZonaRisco.OTIMA, ZonaRisco.SUBTREINO):
        css = "risco-otima"
        ic  = "✅" if z == ZonaRisco.OTIMA else "🔵"
        cor = "#34d399" if z == ZonaRisco.OTIMA else "#60a5fa"
        titulo = f"ACWR {resultado.acwr:.2f} — {ic} {z.value.capitalize()}"
        corpo  = resultado.mensagem_coach.split("\n")[0]
    elif z == ZonaRisco.ATENCAO:
        css = "risco-atencao"; ic = "⚠️"; cor = "#fbbf24"
        titulo = f"ACWR {resultado.acwr:.2f} — ⚠️ Zona de Atenção"
        corpo  = resultado.mensagem_coach.split("\n")[0]
    else:
        css = "risco-perigo"; ic = "🚨"; cor = "#f87171"
        titulo = f"ACWR {resultado.acwr:.2f} — 🚨 {resultado.zona.value.capitalize()}"
        corpo  = resultado.titulo
    st.markdown(f"""
    <div class="risco-card {css}">
        <div class="risco-titulo" style="color:{cor}">{titulo}</div>
        <div class="risco-corpo">{corpo}</div>
    </div>""", unsafe_allow_html=True)


def render_calendario(nivel: NivelCorredor, zonas):
    hoje = date.today()
    seg  = hoje - timedelta(days=hoje.weekday())
    dias_html = ""
    for i in range(7):
        d = seg + timedelta(days=i)
        tipo = TEMPLATE_SEMANAL[nivel][i]
        treino = CATALOGO.get((nivel, tipo))
        emoji  = treino.emoji if treino else "❓"
        nome   = " ".join(tipo.value.split("_")[:2]).capitalize()
        dist_s = f"{treino.distancia_ref_km:.0f}km" if treino and treino.distancia_ref_km > 0 else "—"
        css_cl, cor_d = INT_CLASSE.get(tipo, ("cal-descanso","#6b7280"))
        hoje_extra = "cal-hoje" if d == hoje else ""
        amanha_tag = " ◀" if d == hoje + timedelta(days=1) else ""
        pace_cal = ""
        if zonas and treino:
            zona_p = zonas.zona_por_tipo(tipo.value)
            if zona_p:
                pace_cal = f'<div class="cal-pace">{zona_p.pace_max_str}–{zona_p.pace_min_str}</div>'
        dias_html += f"""
        <div class="cal-cell {css_cl} {hoje_extra}">
            <div class="cal-label">{NOMES_DIA[i]}{amanha_tag}</div>
            <div class="cal-emoji">{emoji}</div>
            <div class="cal-nome">{nome}</div>
            <div class="cal-dist" style="color:{cor_d}">{dist_s}</div>
            {pace_cal}
        </div>"""
    legenda = """<div style="display:flex;gap:.8rem;flex-wrap:wrap;margin-top:.4rem;font-size:.68rem;color:#6b7280">
        <span style="color:#34d399">■ Leve</span>
        <span style="color:#fbbf24">■ Moderado/Longão</span>
        <span style="color:#f87171">■ Forte/Intervalado</span>
        <span style="color:#6b7280">■ Descanso</span>
        <span style="color:#7c3aed">■ Pace (perfil)</span></div>"""
    st.markdown(f'<div class="cal-wrap">{dias_html}</div>{legenda}', unsafe_allow_html=True)


def render_previsoes(previsoes):
    if not previsoes: return
    cards = ""
    for p in previsoes:
        cards += f"""
        <div class="prova-card">
            <div class="prova-nome">{p.distancia_nome}</div>
            <div class="prova-tempo">{p.tempo_str}</div>
            <div class="prova-pace">{p.pace_str}/km</div>
        </div>"""
    st.markdown(f'<div class="prova-grid">{cards}</div>', unsafe_allow_html=True)


def render_nivel_atleta(nivel_at: NivelAtleta, semanas_seguras: int, pct_zona: float):
    st.markdown(f"""
    <div class="nivel-card">
        <div style="font-size:2rem;line-height:1">{nivel_at.emoji}</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800;
          color:{nivel_at.cor};margin:.3rem 0">{nivel_at.nome}</div>
        <div style="color:#6b7280;font-size:.78rem">{nivel_at.descricao}</div>
        <div style="color:#9ca3af;font-size:.72rem;margin-top:.5rem">
          🛡️ {semanas_seguras} sem. seguras · ✅ {pct_zona:.0f}% na zona ótima (28d)</div>
        <div style="color:#4f46e5;font-size:.68rem;margin-top:.3rem">{nivel_at.proxima_meta}</div>
    </div>""", unsafe_allow_html=True)


def render_badges(badges):
    html = '<div class="badge-grid">'
    for b in badges:
        css = "badge-item on" if b.desbloqueado else "badge-item"
        op  = "" if b.desbloqueado else " style='opacity:.35'"
        html += f'<div class="{css}"{op} title="{b.descricao}">{b.emoji} {b.nome}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏃 Correndo pela Vida")
    st.markdown("---")
    nivel_sel = st.selectbox("Nível", [n.value for n in NivelCorredor], index=1)
    nivel = NivelCorredor(nivel_sel)
    st.markdown("---")
    if st.button("🗃️ Popular dados de teste"):
        r = popular_dados_iniciais(nivel=nivel_sel, forcar=True)
        st.success(r["mensagem"]); st.rerun()
    if st.button("🗑️ Resetar tudo", type="secondary"):
        for p in [Path("data/treinos.csv"), Path("data/perfil.json")]:
            if p.exists(): p.unlink()
        if "chat_historico" in st.session_state:
            del st.session_state["chat_historico"]
        st.warning("Dados apagados."); st.rerun()
    st.markdown("---")
    st.markdown("**ACWR** · 🔵<0.8 · 🟢0.8–1.3 · 🟡1.3–1.5 · 🔴>1.5")
    st.caption("v0.4.0 · Final MVP")

# ─────────────────────────────────────────────
# Carrega dados
# ─────────────────────────────────────────────
df        = carregar_df()
perfil    = carregar_perfil()
zonas     = calcular_zonas(perfil)
historico = df_para_historico(df)
motor     = MotorACWR()
gerador   = GeradorTreino()

dor_atual       = int(df.iloc[0]["dor"])              if not df.empty else 0
local_dor_atual = str(df.iloc[0]["local_dor"])        if not df.empty and pd.notna(df.iloc[0]["local_dor"]) else ""
ultimo_pace     = float(df.iloc[0]["pace_min_km"])    if not df.empty else 0.0
ultimo_dist     = float(df.iloc[0]["distancia_km"])   if not df.empty else 0.0
ultimo_pse      = int(df.iloc[0]["pse"])              if not df.empty else 0
ultima_nota     = str(df.iloc[0]["notas"])            if not df.empty and "notas" in df.columns and pd.notna(df.iloc[0]["notas"]) else ""

resultado: ResultadoACWR | None = None
if historico.semana_atual or historico.semanas_prev:
    resultado = motor.calcular(historico, dor_hoje=dor_atual, localizacao_dor=local_dor_atual)

treino_amanha, justificativa, volume_reduzido = gerador.sugerir_amanha(
    nivel=nivel, resultado_acwr=resultado,
    data_amanha=date.today() + timedelta(days=1),
)

df_csv     = pd.read_csv(CSV_PATH) if CSV_PATH.exists() else pd.DataFrame(columns=CSV_COLUNAS)
serie_acwr = calcular_serie_acwr(df_csv)
tendencia, acwr_ant = calcular_tendencia(serie_acwr)
streak     = calcular_streak(df)

# Gamificação
sem_seg    = calcular_semanas_seguras(df_csv, serie_acwr)
pct_zona   = calcular_pct_zona_otima(serie_acwr)
nivel_at   = nivel_atual(sem_seg)
badges     = avaliar_badges(df_csv, streak, sem_seg,
                            float(df_csv["distancia_km"].sum()) if not df_csv.empty else 0.0,
                            resultado.acwr if resultado else 1.0)

# Previsões de prova
previsoes = prever_tempos(zonas.vdot) if zonas else []

# Análise de nota para ajuste VDOT
sugestao_vdot = ""
if ultima_nota and zonas:
    novo_vdot, sugestao_vdot = ajustar_vdot(zonas.vdot, ultima_nota)

# ─────────────────────────────────────────────
# Título + Métricas
# ─────────────────────────────────────────────
col_tit, col_rel = st.columns([4, 1])
with col_tit:
    st.markdown("## 🏃 Correndo pela Vida")
    st.caption("Treinador adaptativo · VDOT Daniels · Gamificação · Coach IA")
with col_rel:
    # Botão PDF
    if not df.empty:
        pdf_bytes = gerar_pdf(
            df=df_csv, perfil=perfil, zonas=zonas, resultado=resultado,
            nivel_atleta=nivel_at, semanas_seguras=sem_seg, streak=streak,
            pct_zona_otima=pct_zona,
            badges_desbloqueados=[b for b in badges if b.desbloqueado],
            previsoes=previsoes,
        )
        st.download_button(
            "📄 Relatório PDF",
            data=pdf_bytes,
            file_name=f"correndo_pela_vida_{date.today().isoformat()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# ── Métricas topo ────────────────────────────
m1, m2, m3, m4, m5, m6 = st.columns(6)
acwr_val    = f"{resultado.acwr:.2f}"          if resultado else "—"
aguda_val   = f"{resultado.carga_aguda:.0f}"   if resultado else "—"
cronica_val = f"{resultado.carga_cronica:.0f}" if resultado else "—"
css_z, ic_z, nm_z = ZONA_CORES.get(resultado.zona, ("","","—")) if resultado else ("","","—")
tend_icon   = {"subindo":"↑","caindo":"↓","estável":"→"}.get(tendencia,"→")
vdot_val    = f"{zonas.vdot:.1f}" if zonas else "—"

with m1: render_metric_card("ACWR",      acwr_val,              f"{ic_z} {nm_z}", css_z)
with m2: render_metric_card("Carga 7d",  aguda_val+" u.a.",     f"Tend. {tend_icon}", "zona-atencao" if resultado and resultado.acwr>1.3 else "")
with m3: render_metric_card("Base 28d",  cronica_val+" u.a.",   "Crônica média", "")
with m4: render_metric_card("VDOT",      vdot_val,              f"RP: {perfil.rp_str}", "zona-otima" if zonas else "")
with m5: render_metric_card("Streak",    f"🔥 {streak}d",       "Consecutivos", "zona-otima" if streak>=3 else "")
with m6: render_metric_card(f"{nivel_at.emoji} Nível", nivel_at.nome,
                             f"🛡️ {sem_seg} sem. seguras",
                             "zona-otima" if sem_seg >= 4 else "")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HERO: Treino de Amanhã + Risco (destaque máximo)
# ─────────────────────────────────────────────
col_hero, col_risco = st.columns([3, 2], gap="large")

with col_hero:
    d_am  = date.today() + timedelta(days=1)
    dn    = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"][d_am.weekday()]
    render_hero_treino(treino_amanha, justificativa, volume_reduzido, zonas,
                       f"{dn} {d_am.strftime('%d/%m')}")

with col_risco:
    st.markdown("#### Risco de Lesão")
    render_risco_card(resultado)

    if resultado and resultado.modo_calibracao:
        st.caption(f"📡 Calibração {resultado.semanas_disponiveis}/4 semanas")

    # Alerta VDOT baseado em nota
    if sugestao_vdot:
        st.markdown(f'<div class="alerta-atencao">🧠 <strong>Ajuste de VDOT sugerido pela nota do último treino:</strong><br>{sugestao_vdot}</div>',
                    unsafe_allow_html=True)

    # Badges desbloqueados (compacto)
    st.markdown("**Conquistas recentes**")
    badges_on = [b for b in badges if b.desbloqueado]
    if badges_on:
        st.markdown("  ".join(f"{b.emoji} {b.nome}" for b in badges_on[:5]))
    else:
        st.caption("Registre treinos para desbloquear conquistas.")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Gráfico de Tendência
# ─────────────────────────────────────────────
st.markdown("#### 📈 Tendência de Carga (ACWR)")
render_grafico_acwr(serie_acwr)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Strava + Formulário + Calendário
# ─────────────────────────────────────────────
col_form, col_cal = st.columns([1, 1], gap="large")

with col_form:
    # Strava
    st.markdown('<div class="strava-box"><b style="color:#fc4c02">⚡ Strava Sync</b></div>',
                unsafe_allow_html=True)
    if st.button("🔄 Sincronizar última atividade", use_container_width=True):
        svc = StravaService()
        ativ, msg = svc.sincronizar_ultima_atividade(nivel_sel, zonas)
        salvo = svc.salvar_no_csv(ativ, nivel_sel)
        if salvo:
            st.success(msg)
            st.info(f"**{ativ.distancia_km} km · {ativ.pace_str} · FC {ativ.fc_media} bpm · PSE {ativ.pse_estimado}/10**")
            st.rerun()
        else:
            st.warning("Já existe registro similar de hoje — sem duplicata.")

    st.markdown("---")

    # Formulário manual
    st.markdown("#### Registrar treino manualmente")
    with st.form("form_treino", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            distancia = st.number_input("Distância (km)", 0.5, 100.0, 8.0, 0.5)
        with c2:
            tempo = st.number_input("Tempo (min)", 5, 600, 50, 1)

        pace_c = tempo / distancia if distancia > 0 else 0
        st.caption(f"Pace: **{int(pace_c)}'{round((pace_c-int(pace_c))*60):02d}\"/km**")

        if zonas:
            z2 = zonas.rodagem_leve
            if z2.pace_max <= pace_c <= z2.pace_min:
                st.caption(f"✅ Pace na zona Z2 ({z2.faixa_str})")
            elif pace_c <= zonas.limiar.pace_min:
                st.caption("🔥 Pace de limiar ou acima")

        pse = st.slider("PSE (1–10)", 1, 10, 6)
        dor = st.slider("Dor (0–10)", 0, 10, 0)
        local_dor = ""
        if dor > 0:
            local_dor = st.text_input("Local da dor", placeholder="ex: joelho direito")
            if dor >= 4: st.warning(f"⚠️ Dor {dor}/10 — protocolo de proteção amanhã.")

        # NOVIDADE: Diário de Sensações
        notas = st.text_area(
            "📓 Diário de Sensações",
            placeholder="Como foi o treino? (ex: 'senti cansaço excessivo', 'fácil demais', 'ótimo ritmo')",
            height=80, max_chars=500,
        )
        if notas:
            _, sugest_preview = ajustar_vdot(zonas.vdot if zonas else 40.0, notas)
            if sugest_preview:
                st.info(f"🧠 **Coach IA detectou:** {sugest_preview[:120]}...")

        st.info(f"📊 Carga: **{round(distancia*pse,1)} u.a.**")
        if st.form_submit_button("💾 Registrar treino", use_container_width=True):
            salvar_sessao(distancia, tempo, pse, dor, local_dor, nivel, notas)
            st.success("✅ Registrado!")
            st.rerun()

with col_cal:
    st.markdown("#### Plano da semana")
    render_calendario(nivel, zonas)

    if previsoes:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🏁 Previsão de Provas (VDOT atual)")
        if zonas:
            st.caption(f"VDOT {zonas.vdot:.1f} · Base: {zonas.fonte_rp}")
        render_previsoes(previsoes)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
tab_hist, tab_coach, tab_perfil, tab_gam, tab_debug = st.tabs([
    "📋 Histórico", "🤖 Coach IA", "👤 Perfil & Zonas",
    "🏆 Gamificação", "🔧 Debug",
])

# ── Histórico ────────────────────────────────
with tab_hist:
    if df.empty:
        st.info("Nenhum treino ainda.")
    else:
        df_d = df.copy()
        df_d["data"]  = pd.to_datetime(df_d["data"]).dt.strftime("%d/%m")
        df_d["pace"]  = df_d["pace_min_km"].apply(pace_str)
        df_d["carga"] = df_d["carga"].apply(lambda x: f"{x:.0f}")
        df_d = df_d.rename(columns={
            "data":"Data","distancia_km":"Km","tempo_min":"Min",
            "pse":"PSE","dor":"Dor","local_dor":"Local dor",
            "nivel":"Nível","pace":"Pace","carga":"Carga u.a.","notas":"Notas",
        })
        cols = ["Data","Km","Min","Pace","PSE","Dor","Carga u.a.","Nível"]
        if "Notas" in df_d.columns:
            cols.append("Notas")
        st.dataframe(df_d[cols], use_container_width=True, hide_index=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total km",  f"{df['distancia_km'].sum():.1f}")
        c2.metric("Sessões",   len(df))
        c3.metric("PSE médio", f"{df['pse'].mean():.1f}")
        c4.metric("Dor máx",   f"{df['dor'].max():.0f}/10" if not df.empty else "—")

# ── Coach IA ─────────────────────────────────
with tab_coach:
    ctx = CoachContexto(
        resultado=resultado, nivel=nivel_sel,
        total_sessoes=len(df),
        total_km=float(df["distancia_km"].sum()) if not df.empty else 0.0,
        media_pse=float(df["pse"].mean()) if not df.empty else 0.0,
        streak_dias=streak, dor_local=local_dor_atual,
        tendencia_acwr=tendencia, acwr_semana_ant=acwr_ant,
        semanas_disponiveis=historico.semanas_disponiveis,
        zonas=zonas, perfil=perfil,
        ultimo_pace=ultimo_pace, ultimo_distancia=ultimo_dist, ultimo_pse=ultimo_pse,
    )
    coach = CoachIA()

    if "chat_historico" not in st.session_state:
        st.session_state.chat_historico = []
        st.session_state.chat_historico.append({
            "role": "coach",
            "content": coach.analise_proativa(ctx),
        })

    # Nota detectada → mensagem proativa do coach
    if sugestao_vdot and "vdot_sugest_shown" not in st.session_state:
        st.session_state.vdot_sugest_shown = True
        st.session_state.chat_historico.append({
            "role": "coach",
            "content": f"📓 **Nota detectada no último treino:**\n\n{sugestao_vdot}",
        })

    for msg in st.session_state.chat_historico:
        role = "assistant" if msg["role"] == "coach" else "user"
        av   = "🏃" if role == "assistant" else None
        with st.chat_message(role, avatar=av):
            st.markdown(msg["content"])

    if pergunta := st.chat_input("Pergunte ao Coach IA..."):
        st.session_state.chat_historico.append({"role": "user", "content": pergunta})
        with st.chat_message("user"): st.markdown(pergunta)
        resposta = coach.responder(pergunta, ctx)
        st.session_state.chat_historico.append({"role": "coach", "content": resposta})
        with st.chat_message("assistant", avatar="🏃"): st.markdown(resposta)

    if st.session_state.get("chat_historico"):
        if st.button("🗑️ Limpar conversa", key="limpar_chat"):
            del st.session_state["chat_historico"]
            if "vdot_sugest_shown" in st.session_state:
                del st.session_state["vdot_sugest_shown"]
            st.rerun()

# ── Perfil & Zonas ────────────────────────────
with tab_perfil:
    col_p1, col_p2 = st.columns([1, 1], gap="large")

    with col_p1:
        st.markdown("### 👤 Perfil do Corredor")
        with st.form("form_perfil"):
            nome_p   = st.text_input("Nome", value=perfil.nome)
            nivel_p  = st.selectbox("Nível", [n.value for n in NivelCorredor],
                                    index=[n.value for n in NivelCorredor].index(perfil.nivel)
                                    if perfil.nivel in [n.value for n in NivelCorredor] else 1)
            c1, c2   = st.columns(2)
            with c1:
                peso_p = st.number_input("Peso (kg)", 40.0, 150.0, perfil.peso_kg, 0.5)
                fc_p   = st.number_input("FCmax (bpm)", 140, 220, perfil.fc_max, 1)
            with c2:
                nasc_p = st.text_input("Nascimento", value=perfil.data_nascimento, placeholder="dd/mm/aaaa")

            st.markdown("#### Recorde Pessoal")
            rp_dist  = st.selectbox("Distância", ["5km","10km"],
                                    index=0 if perfil.rp_distancia=="5km" else 1)
            c3, c4   = st.columns(2)
            with c3: rp_min = st.number_input("Minutos", 0, 120, perfil.rp_tempo_min, 1)
            with c4: rp_seg = st.number_input("Segundos", 0, 59, perfil.rp_tempo_seg, 1)

            st.markdown("#### Objetivo")
            obj_prova = st.text_input("Prova alvo", value=perfil.objetivo_prova,
                                      placeholder="ex: São Silvestre 2026")
            obj_tempo = st.text_input("Tempo alvo", value=perfil.objetivo_tempo,
                                      placeholder="ex: Sub-50 nos 10km")

            if st.form_submit_button("💾 Salvar perfil", use_container_width=True):
                novo = PerfilCorredor(nome=nome_p, nivel=nivel_p, rp_distancia=rp_dist,
                                      rp_tempo_min=rp_min, rp_tempo_seg=rp_seg,
                                      peso_kg=peso_p, fc_max=fc_p,
                                      data_nascimento=nasc_p,
                                      objetivo_prova=obj_prova, objetivo_tempo=obj_tempo)
                salvar_perfil(novo)
                st.success("✅ Perfil salvo! Zonas atualizadas.")
                st.rerun()

    with col_p2:
        st.markdown("### 📊 Zonas de Ritmo (VDOT Daniels)")
        if zonas:
            st.markdown(f"**RP:** {zonas.fonte_rp} · **VDOT:** {zonas.vdot:.1f}")
            st.caption("Fórmula de Jack Daniels (Running Formula, 2ª ed.)")
            for zona_p in [zonas.recuperacao, zonas.rodagem_leve, zonas.longao,
                           zonas.limiar, zonas.intervalado, zonas.repeticao]:
                st.markdown(f"""
                <div class="pace-box">
                    <div class="pace-zona-nome" style="color:{zona_p.cor}">{zona_p.zona_hr} · {zona_p.nome}</div>
                    <div class="pace-faixa" style="color:{zona_p.cor}">{zona_p.faixa_str}</div>
                    <div class="pace-desc">{zona_p.descricao} · PSE {zona_p.pse_ref}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("#### 🏁 Previsão de Provas")
            st.caption(f"Com VDOT {zonas.vdot:.1f}, estes são seus tempos hoje:")
            render_previsoes(previsoes)
        else:
            st.info("Cadastre seu RP para ver zonas de pace e previsão de provas.")

# ── Gamificação ───────────────────────────────
with tab_gam:
    col_g1, col_g2 = st.columns([1, 1], gap="large")

    with col_g1:
        st.markdown("### 🏆 Seu Nível de Atleta")
        render_nivel_atleta(nivel_at, sem_seg, pct_zona)

        # Progressão para o próximo nível
        from gamificacao import NIVEIS
        prox = next((n for n in NIVEIS if n.min_semanas > sem_seg), None)
        if prox:
            faltam = prox.min_semanas - sem_seg
            prog   = sem_seg / prox.min_semanas if prox.min_semanas > 0 else 1.0
            st.progress(min(prog, 1.0), text=f"Faltam {faltam} sem. seguras para {prox.emoji} {prox.nome}")

        st.markdown("---")
        st.markdown("### 📊 Métricas de Consistência")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Semanas seguras", f"🛡️ {sem_seg}")
        mc2.metric("% Zona ótima (28d)", f"✅ {pct_zona:.0f}%")
        mc3.metric("Streak atual", f"🔥 {streak}d")

        # Histórico de semanas seguras (visual simples)
        if not serie_acwr.empty:
            st.markdown("**Histórico ACWR por semana (últimas 8)**")
            semanas_info = []
            hoje = date.today()
            for i in range(7, -1, -1):
                ini = hoje - timedelta(days=(i+1)*7)
                fim = hoje - timedelta(days=i*7)
                mask = (pd.to_datetime(serie_acwr["data"]).dt.date >= ini) & \
                       (pd.to_datetime(serie_acwr["data"]).dt.date < fim)
                s = serie_acwr[mask]
                if not s.empty:
                    max_a = s["acwr"].dropna().max()
                    semanas_info.append((ini, float(max_a) if not pd.isna(max_a) else 0))

            for ini, max_a in semanas_info:
                ic = "🟢" if max_a <= 1.3 else "🟡" if max_a <= 1.5 else "🔴"
                st.markdown(
                    f'<div style="font-size:.78rem;padding:.2rem 0">'
                    f'{ic} Semana de {ini.strftime("%d/%m")}: ACWR máx {max_a:.2f}</div>',
                    unsafe_allow_html=True
                )

    with col_g2:
        st.markdown("### 🎖️ Badges")
        render_badges(badges)

        st.markdown("---")
        st.markdown("### 🏅 Sistema de Níveis")
        for n in NIVEIS:
            ativo = n.min_semanas <= sem_seg
            op = "1.0" if ativo else "0.35"
            st.markdown(
                f'<div style="opacity:{op};padding:.4rem 0;display:flex;align-items:center;gap:.6rem">'
                f'<span style="font-size:1.4rem">{n.emoji}</span>'
                f'<div>'
                f'<div style="font-weight:600;color:{n.cor};font-size:.85rem">{n.nome}</div>'
                f'<div style="color:#6b7280;font-size:.72rem">{n.min_semanas} semanas seguras · {n.descricao}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

# ── Debug ──────────────────────────────────────
with tab_debug:
    st.caption("Dados brutos para desenvolvimento")
    if resultado:
        st.json({
            "acwr": resultado.acwr, "zona": resultado.zona.value,
            "acao": resultado.acao.value, "tendencia": tendencia,
            "semanas_seguras": sem_seg, "pct_zona_otima": pct_zona,
            "nivel_atleta": nivel_at.nome,
            "vdot": zonas.vdot if zonas else None,
            "ultima_nota": ultima_nota[:100] if ultima_nota else "",
        })
    if treino_amanha:
        st.json({"treino": treino_amanha.nome, "volume_reduzido": volume_reduzido})
    st.code(f"CSV: {CSV_PATH.resolve()}\nRegistros: {len(df)}")
