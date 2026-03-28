"""
CORRENDO PELA VIDA — Gerador de Relatório PDF
===============================================
Gera relatório mensal de performance usando ReportLab.
"""
from __future__ import annotations
import io
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Paleta escura adaptada para PDF (fundo branco)
COR_PRIMARIA  = colors.HexColor("#4f46e5")
COR_VERDE     = colors.HexColor("#059669")
COR_AMARELO   = colors.HexColor("#d97706")
COR_VERMELHO  = colors.HexColor("#dc2626")
COR_CINZA_BG  = colors.HexColor("#f8f7ff")
COR_CINZA_LN  = colors.HexColor("#e5e4ff")
COR_TEXTO     = colors.HexColor("#1f2937")
COR_MUTED     = colors.HexColor("#6b7280")
BRANCO        = colors.white


def _estilos():
    ss = getSampleStyleSheet()
    base = {"fontName": "Helvetica", "textColor": COR_TEXTO}
    estilos = {
        "titulo": ParagraphStyle("titulo", parent=ss["Normal"],
            fontSize=22, fontName="Helvetica-Bold",
            textColor=COR_PRIMARIA, spaceAfter=4, spaceBefore=0, alignment=TA_LEFT),
        "subtitulo": ParagraphStyle("subtitulo", parent=ss["Normal"],
            fontSize=11, fontName="Helvetica",
            textColor=COR_MUTED, spaceAfter=16, alignment=TA_LEFT),
        "secao": ParagraphStyle("secao", parent=ss["Normal"],
            fontSize=13, fontName="Helvetica-Bold",
            textColor=COR_PRIMARIA, spaceBefore=18, spaceAfter=6),
        "corpo": ParagraphStyle("corpo", parent=ss["Normal"],
            fontSize=9.5, fontName="Helvetica",
            textColor=COR_TEXTO, spaceAfter=4, leading=14),
        "label": ParagraphStyle("label", parent=ss["Normal"],
            fontSize=8, fontName="Helvetica-Bold",
            textColor=COR_MUTED, spaceAfter=2, alignment=TA_CENTER),
        "valor": ParagraphStyle("valor", parent=ss["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=COR_PRIMARIA, spaceAfter=0, alignment=TA_CENTER),
        "rodape": ParagraphStyle("rodape", parent=ss["Normal"],
            fontSize=7.5, fontName="Helvetica",
            textColor=COR_MUTED, alignment=TA_CENTER),
    }
    return estilos


def _tabela_metricas(dados: list[tuple[str, str, str]]) -> Table:
    """Cria tabela de métricas de destaque (label, valor, unidade)."""
    n = len(dados)
    larguras = [A4[0] / n - 1.4 * cm] * n

    cabecalhos = [[Paragraph(d[0], _estilos()["label"]) for d in dados]]
    valores    = [[Paragraph(d[1], _estilos()["valor"]) for d in dados]]
    unidades   = [[Paragraph(d[2], _estilos()["label"]) for d in dados]]

    t = Table(cabecalhos + valores + unidades, colWidths=larguras, rowHeights=[14, 26, 12])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_CINZA_BG),
        ("ROUNDEDCORNERS", [6]),
        ("BOX",      (0, 0), (-1, -1), 0.5, COR_CINZA_LN),
        ("INNERGRID",(0, 0), (-1, -1), 0,   colors.white),
        ("VALIGN",   (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    return t


def _tabela_historico(df: pd.DataFrame, es) -> Table:
    colunas = ["Data", "Distância", "Tempo", "Pace", "PSE", "Dor", "Carga"]
    header = [Paragraph(f"<b>{c}</b>", es["label"]) for c in colunas]
    linhas = [header]

    def pace_s(v):
        m = int(v); s = round((v - m) * 60)
        return f"{m}'{s:02d}\""

    for _, r in df.iterrows():
        linhas.append([
            Paragraph(str(r["data"]), es["corpo"]),
            Paragraph(f"{float(r['distancia_km']):.1f} km", es["corpo"]),
            Paragraph(f"{int(r['tempo_min'])} min", es["corpo"]),
            Paragraph(pace_s(float(r["pace_min_km"])), es["corpo"]),
            Paragraph(str(int(r["pse"])), es["corpo"]),
            Paragraph(str(int(r["dor"])), es["corpo"]),
            Paragraph(f"{float(r['carga']):.0f}", es["corpo"]),
        ])

    col_w = [2.6*cm, 2.2*cm, 2*cm, 2.2*cm, 1.2*cm, 1.1*cm, 1.5*cm]
    t = Table(linhas, colWidths=col_w, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR",  (0, 0), (-1, 0), BRANCO),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.3, COR_CINZA_LN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, COR_CINZA_BG]),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(estilo))
    return t


def _tabela_previsoes(previsoes, es) -> Table:
    header = [Paragraph(f"<b>{c}</b>", es["label"])
              for c in ["Prova", "Previsão de tempo", "Pace médio"]]
    linhas = [header]
    for p in previsoes:
        linhas.append([
            Paragraph(p.distancia_nome, es["corpo"]),
            Paragraph(f"<b>{p.tempo_str}</b>", es["corpo"]),
            Paragraph(f"{p.pace_str}/km", es["corpo"]),
        ])
    col_w = [5*cm, 5*cm, 5*cm]
    t = Table(linhas, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR",  (0, 0), (-1, 0), BRANCO),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.3, COR_CINZA_LN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, COR_CINZA_BG]),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return t


def gerar_pdf(
    df: pd.DataFrame,
    perfil,
    zonas,
    resultado,
    nivel_atleta,
    semanas_seguras: int,
    streak: int,
    pct_zona_otima: float,
    badges_desbloqueados: list,
    previsoes: list,
) -> bytes:
    """
    Gera o PDF completo e retorna bytes para download.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    es = _estilos()
    story = []

    # ── Cabeçalho ──────────────────────────────────────────────
    hoje = date.today()
    mes_ref = hoje.replace(day=1) - timedelta(days=1)
    mes_nome = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"][mes_ref.month - 1]

    story.append(Paragraph("🏃 Correndo pela Vida", es["titulo"]))
    story.append(Paragraph(
        f"Relatório de Performance — {mes_nome} {mes_ref.year} &nbsp;·&nbsp; "
        f"{perfil.nome} &nbsp;·&nbsp; {perfil.nivel}",
        es["subtitulo"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=COR_PRIMARIA, spaceAfter=16))

    # Filtra último mês
    df_mes = df.copy()
    if not df_mes.empty:
        df_mes["data"] = pd.to_datetime(df_mes["data"])
        ini_mes = pd.Timestamp(mes_ref.replace(day=1))
        fim_mes = pd.Timestamp(mes_ref)
        df_mes = df_mes[(df_mes["data"] >= ini_mes) & (df_mes["data"] <= fim_mes)]
        df_mes["data"] = df_mes["data"].dt.strftime("%d/%m")

    # ── Métricas de destaque ────────────────────────────────────
    story.append(Paragraph("Resumo do Mês", es["secao"]))
    total_km   = float(df_mes["distancia_km"].sum()) if not df_mes.empty else 0
    total_sess = len(df_mes)
    media_pse  = float(df_mes["pse"].mean()) if not df_mes.empty else 0
    acwr_val   = f"{resultado.acwr:.2f}" if resultado else "—"
    vdot_val   = f"{zonas.vdot:.1f}" if zonas else "—"

    story.append(_tabela_metricas([
        ("Total km", f"{total_km:.0f}", "km no mês"),
        ("Sessões",  str(total_sess),   "treinos"),
        ("PSE médio",f"{media_pse:.1f}","/ 10"),
        ("ACWR",     acwr_val,          "carga atual"),
        ("VDOT",     vdot_val,          "Daniels"),
    ]))
    story.append(Spacer(1, 16))

    # ── Gamificação ─────────────────────────────────────────────
    story.append(Paragraph("Perfil de Atleta", es["secao"]))
    gam_data = [
        [Paragraph("<b>Nível</b>", es["label"]),
         Paragraph("<b>Streak</b>", es["label"]),
         Paragraph("<b>Semanas seguras</b>", es["label"]),
         Paragraph("<b>% Zona ótima (28d)</b>", es["label"])],
        [Paragraph(f"{nivel_atleta.emoji} {nivel_atleta.nome}", es["valor"]),
         Paragraph(f"🔥 {streak}d", es["valor"]),
         Paragraph(f"🛡️ {semanas_seguras}sem", es["valor"]),
         Paragraph(f"✅ {pct_zona_otima:.0f}%", es["valor"])],
    ]
    gam_t = Table(gam_data, colWidths=[(A4[0]-4*cm)/4]*4, rowHeights=[14, 28])
    gam_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_CINZA_BG),
        ("BOX",        (0, 0), (-1, -1), 0.5, COR_CINZA_LN),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, COR_CINZA_LN),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(gam_t)

    if badges_desbloqueados:
        story.append(Spacer(1, 8))
        badges_str = "  ".join(f"{b.emoji} {b.nome}" for b in badges_desbloqueados[:8])
        story.append(Paragraph(f"Badges conquistados: {badges_str}", es["corpo"]))

    # ── Previsão de Provas ──────────────────────────────────────
    if previsoes and zonas:
        story.append(Paragraph("Previsão de Provas (VDOT atual)", es["secao"]))
        story.append(Paragraph(
            f"Com seu VDOT {zonas.vdot:.1f} (baseado em {zonas.fonte_rp}), "
            "estes são os tempos que você faria hoje em cada prova:",
            es["corpo"]
        ))
        story.append(Spacer(1, 6))
        story.append(_tabela_previsoes(previsoes, es))

    # ── Histórico de Sessões ────────────────────────────────────
    if not df_mes.empty:
        story.append(Paragraph("Sessões do Mês", es["secao"]))
        story.append(_tabela_historico(df_mes, es))

    # ── Análise do Coach ────────────────────────────────────────
    story.append(Paragraph("Análise do Coach IA", es["secao"]))
    if resultado:
        story.append(Paragraph(resultado.mensagem_coach.replace("\n", "<br/>"), es["corpo"]))
        if resultado.aviso_dor:
            story.append(Paragraph(
                f"⚠️ <b>Alerta de dor:</b> {resultado.aviso_dor}", es["corpo"]
            ))
    else:
        story.append(Paragraph("Dados insuficientes para análise.", es["corpo"]))

    # ── Rodapé ─────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COR_CINZA_LN))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Correndo pela Vida · Relatório gerado em {hoje.strftime('%d/%m/%Y')} · "
        "Motor ACWR + VDOT Daniels · Uso pessoal",
        es["rodape"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
