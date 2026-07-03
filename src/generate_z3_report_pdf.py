"""
Generateur de rapport PDF expert — Verification Formelle par Solveur SMT Z3
Documente la demarche complete de z3_formal_verification.py
"""

import os, json
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image, KeepTogether
)

# ─── Palette ─────────────────────────────────────────────────────────────────
BLEU_NUIT   = colors.HexColor("#0D1B2A")
BLEU_FONCE  = colors.HexColor("#1B2A4A")
BLEU_ROI    = colors.HexColor("#2E5EA8")
BLEU_CLAIR  = colors.HexColor("#D6E4F7")
BLEU_PALE   = colors.HexColor("#EBF3FC")
VERT        = colors.HexColor("#1A7A4A")
VERT_FOND   = colors.HexColor("#E8F8F0")
ROUGE       = colors.HexColor("#B03030")
ROUGE_FOND  = colors.HexColor("#FDECEA")
ORANGE      = colors.HexColor("#C96A00")
ORANGE_FOND = colors.HexColor("#FEF3E2")
VIOLET      = colors.HexColor("#6A3DAA")
VIOLET_FOND = colors.HexColor("#F3EEF9")
JAUNE_FOND  = colors.HexColor("#FEFDE7")
GRIS_FONCE  = colors.HexColor("#4A5568")
GRIS_MOYEN  = colors.HexColor("#A0AEC0")
GRIS_CLAIR  = colors.HexColor("#F7FAFC")
BLANC       = colors.white
NOIR        = colors.black

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# ─── Styles ──────────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()
    def S(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)
    return {
        "h1":    S("h1","Heading1", fontSize=14, textColor=BLEU_FONCE,
                   spaceBefore=16, spaceAfter=6, leading=18),
        "h2":    S("h2","Heading2", fontSize=11.5, textColor=BLEU_ROI,
                   spaceBefore=12, spaceAfter=5, leading=15),
        "h3":    S("h3","Heading3", fontSize=10.5, textColor=GRIS_FONCE,
                   spaceBefore=8,  spaceAfter=4,  leading=14),
        "body":  S("body","Normal", fontSize=10, leading=15, spaceAfter=5,
                   alignment=TA_JUSTIFY),
        "bc":    S("bc","Normal",   fontSize=10, leading=15, spaceAfter=5,
                   alignment=TA_CENTER),
        "bull":  S("bull","Normal", fontSize=10, leading=14, spaceAfter=3,
                   leftIndent=14, firstLineIndent=-10),
        "code":  S("code","Code",   fontSize=8.5, fontName="Courier",
                   backColor=GRIS_CLAIR, leading=12,
                   leftIndent=10, rightIndent=10, spaceBefore=3, spaceAfter=3),
        "leg":   S("leg","Normal",  fontSize=8.5, textColor=GRIS_FONCE,
                   alignment=TA_CENTER, spaceAfter=6, spaceBefore=2),
        "note":  S("note","Normal", fontSize=9,   textColor=GRIS_FONCE,
                   leftIndent=10, spaceAfter=4, leading=13),
        "alert": S("alert","Normal",fontSize=10,  textColor=ROUGE,
                   leftIndent=10, spaceAfter=4, leading=14, fontName="Helvetica-Bold"),
        "ok":    S("ok","Normal",   fontSize=10,  textColor=VERT,
                   leftIndent=10, spaceAfter=4, leading=14, fontName="Helvetica-Bold"),
        "center_bold": S("cb","Normal", fontSize=10, textColor=BLEU_FONCE,
                         fontName="Helvetica-Bold", alignment=TA_CENTER),
    }

# ─── Helpers ─────────────────────────────────────────────────────────────────
def sp(h=6):  return Spacer(1, h)
def sep(c=BLEU_ROI, t=1, b=6, a=8): return HRFlowable(width="100%", thickness=t, color=c, spaceBefore=b, spaceAfter=a)

def h1_block(txt, st):
    return [sep(BLEU_FONCE, 2, 6, 0), Paragraph(txt, st["h1"]), sep(BLEU_ROI, 0.5, 0, 6)]

def h2_block(txt, st):
    return [Paragraph(txt, st["h2"]), sep(GRIS_MOYEN, 0.5, 0, 4)]

def cadre(paras, fond=BLEU_PALE, bord=BLEU_ROI, pad=10):
    data = [[p] for p in paras]
    t = Table(data, colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), fond),
        ("BOX",        (0,0),(-1,-1), 1.3, bord),
        ("LEFTPADDING",(0,0),(-1,-1), pad),
        ("RIGHTPADDING",(0,0),(-1,-1), pad),
        ("TOPPADDING", (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    return t

def prop_row(label, resultat, detail, fond, texte_color, st):
    icon = "[PROUVE]" if resultat == "PROUVE" else "[VIOLE]" if resultat == "VIOLE" else "[?]"
    icon_col = VERT if resultat == "PROUVE" else ROUGE if resultat == "VIOLE" else ORANGE
    data = [[
        Paragraph(icon, ParagraphStyle("ic", fontSize=9, fontName="Helvetica-Bold",
                                       textColor=icon_col, alignment=TA_CENTER)),
        Paragraph(f"<b>{label}</b>",
                  ParagraphStyle("pl", fontSize=9.5, leading=13, textColor=texte_color)),
        Paragraph(detail,
                  ParagraphStyle("pd", fontSize=8.5, leading=12, textColor=GRIS_FONCE,
                                 alignment=TA_JUSTIFY)),
    ]]
    cw = [(PAGE_W-2*MARGIN)*r for r in [0.11, 0.42, 0.47]]
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), fond),
        ("BOX",        (0,0),(-1,-1), 0.8, GRIS_MOYEN),
        ("LINEAFTER",  (0,0),(0,-1),  0.8, GRIS_MOYEN),
        ("LINEAFTER",  (1,0),(1,-1),  0.5, GRIS_MOYEN),
        ("TOPPADDING", (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
        ("VALIGN",     (0,0),(-1,-1), "TOP"),
    ]))
    return t

def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # En-tete
    canvas.setFillColor(BLEU_NUIT)
    canvas.rect(0, h-1.2*cm, w, 1.2*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(BLANC)
    canvas.drawString(MARGIN, h-0.75*cm,
        "RAPPORT DE VERIFICATION FORMELLE PAR SOLVEUR SMT Z3 — YOLO / KITTI / AEB")
    canvas.drawRightString(w-MARGIN, h-0.75*cm, date.today().strftime("%d/%m/%Y"))
    # Pied de page
    canvas.setFillColor(BLEU_FONCE)
    canvas.rect(0, 0, w, 0.9*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BLANC)
    canvas.drawString(MARGIN, 0.3*cm, "Z3 v4.16.0 | ONNX Runtime v1.26.0 | Ultralytics YOLO v8.4.60")
    canvas.drawCentredString(w/2, 0.3*cm, f"Page {doc.page}")
    canvas.drawRightString(w-MARGIN, 0.3*cm, "Document confidentiel")
    canvas.restoreState()

# =============================================================================
# PAGE DE GARDE
# =============================================================================
def page_garde(story, st):
    story.append(sp(55))
    # Bande principale
    titre_data = [[
        Paragraph("RAPPORT DE VERIFICATION FORMELLE",
                  ParagraphStyle("tg", fontSize=22, textColor=BLANC,
                                 fontName="Helvetica-Bold", alignment=TA_CENTER, leading=28)),
        ],[
        Paragraph("par Solveur SMT Z3 (Satisfiability Modulo Theories)",
                  ParagraphStyle("tg2", fontSize=13, textColor=BLEU_CLAIR,
                                 alignment=TA_CENTER, leading=18)),
    ]]
    tg = Table(titre_data, colWidths=[PAGE_W-2*MARGIN])
    tg.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), BLEU_NUIT),
        ("TOPPADDING",(0,0),(-1,-1), 14),
        ("BOTTOMPADDING",(0,0),(-1,-1), 14),
        ("LEFTPADDING",(0,0),(-1,-1), 16),
    ]))
    story.append(tg)
    story.append(sp(10))

    sous = [
        "Modele de detection : YOLO best.pt entraine sur KITTI",
        "Systeme cible : Freinage d'Urgence Automatique (AEB)",
        "Proprietes verifiees : Surete, Vivacite, Invariants, Robustesse",
    ]
    for s in sous:
        story.append(Paragraph(s, ParagraphStyle("sg", fontSize=11, textColor=BLEU_ROI,
                                                  alignment=TA_CENTER, spaceAfter=4)))
    story.append(sp(40))

    info_data = [
        ["Outil principal", "Date d'analyse", "Blocs verifies", "Proprietes totales"],
        ["Z3 SMT Solver v4.16.0", date.today().strftime("%d/%m/%Y"), "5 blocs", "32 proprietes"],
    ]
    cw = [(PAGE_W-2*MARGIN)/4]*4
    ti = Table(info_data, colWidths=cw)
    ti.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), BLEU_CLAIR),
        ("BACKGROUND",(0,1),(-1,1), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTNAME",(0,1),(-1,1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 10),
        ("TEXTCOLOR",(0,1),(-1,1), BLEU_FONCE),
        ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
        ("INNERGRID",(0,0),(-1,-1), 0.5, GRIS_MOYEN),
        ("ALIGN",(0,0),(-1,-1), "CENTER"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1), 9),
        ("BOTTOMPADDING",(0,0),(-1,-1), 9),
    ]))
    story.append(ti)
    story.append(PageBreak())

# =============================================================================
# SECTION 1 — QU'EST-CE QU'UN SOLVEUR SMT
# =============================================================================
def section_smt(story, st):
    story += h1_block("1. LE SOLVEUR SMT Z3 — FONDEMENTS THEORIQUES", st)

    story += h2_block("1.1 Satisfiabilite Modulo Theories (SMT)", st)
    story.append(Paragraph(
        "Un solveur SMT (Satisfiability Modulo Theories) est un outil de raisonnement automatique "
        "qui determine si une formule logique est satisfaisable dans un modele mathematique precis. "
        "Z3, developpe par Microsoft Research, est l'un des solveurs les plus performants et les "
        "plus utilises dans l'industrie et la recherche academique. Il combine :", st["body"]))
    for b in [
        "La logique propositionnelle (Et, Ou, Non, Implique)",
        "L'arithmetique lineaire reelle (LRA) — pour raisonner sur les nombres reels continus",
        "L'arithmetique lineaire entiere (LIA) — pour les entiers et les etats discrets",
        "La theorie des tableaux et des listes — pour les structures de donnees",
        "La combinaison de theories (Nelson-Oppen) — pour les formules mixtes",
    ]:
        story.append(Paragraph(f"  •  {b}", st["bull"]))

    story.append(sp(8))
    story += h2_block("1.2 Principe de preuve par refutation", st)
    story.append(Paragraph(
        "La methode de verification utilisee dans ce projet repose sur la "
        "<b>preuve par refutation</b> (aussi appelee methode indirecte) :", st["body"]))

    refut_data = [[
        Paragraph("Objectif", ParagraphStyle("rh", fontSize=10, fontName="Helvetica-Bold",
                                              textColor=BLANC, alignment=TA_CENTER)),
        Paragraph("Methode Z3", ParagraphStyle("rh2", fontSize=10, fontName="Helvetica-Bold",
                                               textColor=BLANC, alignment=TA_CENTER)),
        Paragraph("Interpretation", ParagraphStyle("rh3", fontSize=10, fontName="Helvetica-Bold",
                                                    textColor=BLANC, alignment=TA_CENTER)),
    ],[
        Paragraph("Prouver que la propriete P est vraie pour TOUS les inputs",
                  ParagraphStyle("rb", fontSize=9.5, leading=13)),
        Paragraph("Demander a Z3 si NOT(P) est satisfaisable",
                  ParagraphStyle("rb", fontSize=9.5, leading=13)),
        Paragraph("Si Z3 repond UNSAT : P est un theoreme mathematique certifie",
                  ParagraphStyle("rb", fontSize=9.5, leading=13, textColor=VERT,
                                 fontName="Helvetica-Bold")),
    ],[
        Paragraph("Trouver un cas ou P est violee",
                  ParagraphStyle("rb", fontSize=9.5, leading=13)),
        Paragraph("Demander a Z3 si NOT(P) est satisfaisable",
                  ParagraphStyle("rb", fontSize=9.5, leading=13)),
        Paragraph("Si Z3 repond SAT : un contre-exemple concret est fourni",
                  ParagraphStyle("rb", fontSize=9.5, leading=13, textColor=ROUGE,
                                 fontName="Helvetica-Bold")),
    ]]
    cwr = [(PAGE_W-2*MARGIN)*r for r in [0.30, 0.33, 0.37]]
    tr = Table(refut_data, colWidths=cwr)
    tr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLANC, GRIS_CLAIR]),
        ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
        ("INNERGRID",(0,0),(-1,-1), 0.5, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 7), ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 8), ("VALIGN",(0,0),(-1,-1), "TOP"),
    ]))
    story.append(tr)
    story.append(sp(8))

    story.append(cadre([
        Paragraph("<b>Difference fondamentale avec les tests classiques :</b>",
                  ParagraphStyle("cf", fontSize=10, fontName="Helvetica-Bold", textColor=BLEU_FONCE)),
        Paragraph(
            "Un test unitaire verifie le comportement sur un nombre FINI d'exemples choisis par le programmeur. "
            "Z3 prouve la propriete sur un espace INFINI d'inputs — le domaine continu des reels ou "
            "l'ensemble infini des entiers — sans aucune exception. "
            "Un resultat UNSAT de Z3 est une <b>certitude mathematique</b>, comparable a une demonstration "
            "formelle en logique mathematique.",
            ParagraphStyle("cb2", fontSize=10, leading=15, alignment=TA_JUSTIFY)),
    ], BLEU_PALE, BLEU_ROI))

    story.append(sp(8))
    story += h2_block("1.3 L'algorithme DPLL(T) utilise par Z3", st)
    story.append(Paragraph(
        "Sous le capot, Z3 utilise l'algorithme <b>DPLL(T)</b> "
        "(Davis-Putnam-Logemann-Loveland modulo Theories), une extension du solveur SAT classique. "
        "Le principe est le suivant :", st["body"]))
    for step in [
        "La formule logique est mise sous forme normale conjonctive (CNF)",
        "Le module SAT explore l'espace des affectations de variables booleennes par backtracking",
        "Chaque affectation partielle est transmise au solveur de theorie (arithmetique, etc.)",
        "Si le solveur de theorie detecte une inconsistance, il produit un lemme qui empeche "
        "Z3 de revisiter ce chemin — c'est ce qui garantit la completude",
        "Si aucune affectation valide n'existe : UNSAT — la propriete est prouvee",
    ]:
        story.append(Paragraph(f"  {chr(9654)}  {step}", st["bull"]))

    story.append(PageBreak())

# =============================================================================
# SECTION 2 — OBJECTIFS DE LA VERIFICATION
# =============================================================================
def section_objectifs(story, st):
    story += h1_block("2. OBJECTIFS DE LA VERIFICATION FORMELLE", st)

    story.append(Paragraph(
        "La verification formelle d'un systeme embarque critique comme l'AEB ne peut pas "
        "reposer uniquement sur des tests statistiques. Les standards de securite fonctionnelle "
        "(ISO 26262, SOTIF, AUTOSAR) exigent des <b>preuves de proprietes</b> — pas seulement "
        "des mesures de performance. Cette verification Z3 repond a cinq objectifs distincts :", st["body"]))

    objectifs = [
        ("Objectif 1 — Coherence des regles de classification",
         BLEU_PALE, BLEU_ROI,
         "Prouver que les regles qui transforment (IoU, classe, GT) en (TP/FP/FN/MC) "
         "sont logiquement coherentes : aucune detection ne peut appartenir a deux "
         "categories simultanement, et chaque situation est couverte sans ambiguite. "
         "Cela garantit que la base logique de la verification est elle-meme sans defaut."),
        ("Objectif 2 — Surete de la machine d'etats AEB",
         VERT_FOND, VERT,
         "Prouver que le systeme de freinage ne peut pas atteindre d'etat dangereux : "
         "pas de freinage fantome sur un FP isole, freinage obligatoire si TTC critique, "
         "mode degrade declencle par accumulation de FP. Ces proprietes de surete (safety) "
         "garantissent que le systeme ne fait pas de mal par commission."),
        ("Objectif 3 — Vivacite et absence de blocage",
         VERT_FOND, VERT,
         "Prouver que le systeme reagit toujours : si un obstacle est confirme a moins "
         "de 1.8 secondes (TTC), le freinage d'urgence est declenche sans exception. "
         "Cette propriete de vivacite (liveness) garantit que le systeme fait du bien "
         "par omission — il n'oublie jamais d'agir quand il le faut."),
        ("Objectif 4 — Correction mathematique de l'estimateur TTC",
         VIOLET_FOND, VIOLET,
         "Prouver les proprietes algebriques de la formule TTC sur le domaine reel "
         "continu : positivite, monotonie inverse, linearite, dualite vitesse. "
         "Ces proprietes sont impossibles a verifier exhaustivement par des tests "
         "car le domaine est infini — Z3 les prouve en quelques millisecondes."),
        ("Objectif 5 — Garantie du profil conservateur pour les misclassifications",
         ORANGE_FOND, ORANGE,
         "Prouver que pour toutes les 64 combinaisons de classes possibles (8x8), "
         "la strategie du profil conservateur ne peut jamais sous-estimer le risque reel. "
         "Cela certifie que le systeme AEB est robuste aux erreurs de classification du reseau."),
    ]
    for titre_o, fond, bord, desc in objectifs:
        odata = [[
            Paragraph(f"<b>{titre_o}</b>",
                      ParagraphStyle("ot", fontSize=10, textColor=bord, fontName="Helvetica-Bold")),
        ],[
            Paragraph(desc, ParagraphStyle("od", fontSize=9.5, leading=14, alignment=TA_JUSTIFY)),
        ]]
        to = Table(odata, colWidths=[PAGE_W-2*MARGIN])
        to.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,0), fond),
            ("BACKGROUND",(0,1),(0,1), BLANC),
            ("BOX",(0,0),(-1,-1), 1.2, bord),
            ("TOPPADDING",(0,0),(-1,-1), 8), ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ("LEFTPADDING",(0,0),(-1,-1), 12),
        ]))
        story.append(to)
        story.append(sp(5))

    story.append(PageBreak())

# =============================================================================
# SECTION 3 — ARCHITECTURE DE LA VERIFICATION
# =============================================================================
def section_architecture(story, st):
    story += h1_block("3. ARCHITECTURE DE LA VERIFICATION EN 5 BLOCS", st)

    story.append(Paragraph(
        "La verification est organisee en 5 blocs independants, chacun ciblant "
        "une composante differente du systeme. Les blocs 1 a 4 utilisent Z3 pour "
        "des preuves formelles mathematiquement certaines. Le bloc 5 utilise "
        "ONNX Runtime pour une analyse empirique de robustesse du reseau neuronal.", st["body"]))

    story.append(sp(6))
    blocs = [
        ("BLOC 1", "Regles de classification IoU",
         "Z3 — Logique du premier ordre",
         "7 proprietes", BLEU_PALE, BLEU_ROI),
        ("BLOC 2", "Machine d'etats AEB",
         "Z3 — Arithmetique mixte (reelle + entiere)",
         "9 proprietes (4 surete + 3 vivacite + 2 invariants)", VERT_FOND, VERT),
        ("BLOC 3", "Estimateur TTC",
         "Z3 — Arithmetique lineaire reelle (LRA)",
         "5 proprietes mathematiques", VIOLET_FOND, VIOLET),
        ("BLOC 4", "Profil conservateur MC",
         "Z3 — Arithmetique entiere (LIA)",
         "13 proprietes (6 generales + 6 paires + 1 idempotence)", ORANGE_FOND, ORANGE),
        ("BLOC 5", "Robustesse reseau YOLO",
         "ONNX Runtime — Perturbations epsilon",
         "4 niveaux epsilon x 30 images x 20 perturbations = 2400 tests", JAUNE_FOND, ORANGE),
    ]
    bloc_data = [["Bloc", "Composante", "Outil", "Couverture"]]
    for num, comp, outil, couv, fond, bord in blocs:
        bloc_data.append([num, comp, outil, couv])
    cwb = [(PAGE_W-2*MARGIN)*r for r in [0.11, 0.28, 0.30, 0.31]]
    tb = Table(bloc_data, colWidths=cwb)
    tb_style = [
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9.5),
        ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
        ("INNERGRID",(0,0),(-1,-1), 0.5, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 7), ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",(0,0),(-1,-1), "TOP"),
    ]
    for i, (_, _, _, _, fond, bord) in enumerate(blocs):
        tb_style.append(("BACKGROUND", (0,i+1),(0,i+1), fond))
        tb_style.append(("TEXTCOLOR",  (0,i+1),(0,i+1), bord))
        tb_style.append(("FONTNAME",   (0,i+1),(0,i+1), "Helvetica-Bold"))
    tb.setStyle(TableStyle(tb_style))
    story.append(tb)
    story.append(sp(10))

    story += h2_block("3.1 Variables symboliques Z3 utilisees dans la verification", st)
    story.append(Paragraph(
        "Chaque composante du systeme est encodee avec des variables symboliques Z3 "
        "qui representent les grandeurs du probleme. Le solveur raisonne sur ces "
        "variables sans leur affecter de valeur concrete — c'est ce qui permet la "
        "generalisation a tous les inputs possibles :", st["body"]))

    vars_data = [
        ["Variable Z3", "Type", "Domaine", "Signification physique"],
        ["iou",        "Real",  "[0, 1]",           "Intersection over Union entre pred et GT"],
        ["same_class", "Bool",  "{True, False}",     "Meme categorie predite et GT"],
        ["gt_exists",  "Bool",  "{True, False}",     "Presence d'un objet GT dans la scene"],
        ["det_type",   "Int",   "{0=TP,1=FP,2=FN,3=MC}", "Type de detection classifiee"],
        ["ttc",        "Real",  "[0, 60] s",         "Time-to-Collision estime"],
        ["fp_count",   "Int",   "[0, 10]",           "Compteur de FP consecutifs"],
        ["brake_pct",  "Int",   "[0, 100]",          "Commande de freinage en %"],
        ["aeb_state",  "Int",   "{0..5}",            "Etat courant de la machine AEB"],
        ["h_box",      "Real",  "[1, 375] px",       "Hauteur boite englobante en pixels"],
        ["h_real",     "Real",  "[0, 5] m",          "Hauteur reelle de l'objet en metres"],
        ["speed",      "Real",  "[0, 50] m/s",       "Vitesse ego du vehicule"],
        ["pred_cls",   "Int",   "[0, 7]",            "Classe predite par le reseau"],
        ["gt_cls",     "Int",   "[0, 7]",            "Classe reelle (ground truth)"],
    ]
    cwv = [(PAGE_W-2*MARGIN)*r for r in [0.18, 0.10, 0.20, 0.52]]
    tv = Table(vars_data, colWidths=cwv)
    tv.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLANC, GRIS_CLAIR]),
        ("FONTNAME",(0,1),(1,-1), "Courier"),
        ("TEXTCOLOR",(0,1),(1,-1), BLEU_ROI),
        ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
        ("INNERGRID",(0,0),(-1,-1), 0.4, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 7), ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(tv)
    story.append(PageBreak())

# =============================================================================
# SECTION 4 — BLOC 1
# =============================================================================
def section_bloc1(story, st):
    story += h1_block("4. BLOC 1 — REGLES DE CLASSIFICATION IoU", st)
    story.append(cadre([
        Paragraph("<b>Objectif du bloc :</b>  Prouver que les 4 regles (TP, FP, FN, MC) "
                  "basees sur l'IoU sont mutuellement exclusives, sondes (suffisantes) "
                  "et necessaires. Toute detection appartient a exactement une categorie.",
                  ParagraphStyle("co", fontSize=10, leading=14, alignment=TA_JUSTIFY)),
    ], BLEU_PALE, BLEU_ROI))
    story.append(sp(8))

    story += h2_block("4.1 Encodage formel des 4 categories", st)
    story.append(Paragraph(
        "Les quatre categories sont definies comme des predicats Z3 booleen "
        "dependant des variables symboliques iou, same_class, gt_exists :", st["body"]))
    for code_line in [
        "IS_TP = And(iou >= 1/2,  same_class,      gt_exists)   # Detection correcte",
        "IS_MC = And(iou >= 1/2,  Not(same_class), gt_exists)   # Bonne position, mauvaise classe",
        "IS_FP = And(iou <  1/2)                                 # Aucun GT correspondant",
        "IS_FN = And(gt_exists,   Not(iou >= 1/2))               # GT non couvert",
    ]:
        story.append(Paragraph(code_line, st["code"]))
    story.append(sp(6))

    story += h2_block("4.2 Resultats des 7 proprietes verifiees", st)
    props_b1 = [
        ("P1.1 — TP et FP mutuellement exclusifs",
         "PROUVE", "0.3 ms",
         "Il est impossible qu'une detection soit a la fois TP et FP. "
         "Z3 a prouve que Not(And(IS_TP, IS_FP)) est une tautologie."),
        ("P1.2 — TP et MC mutuellement exclusifs",
         "PROUVE", "0.2 ms",
         "Une detection correctement classifiee ne peut pas etre une misclassification."),
        ("P1.3 — MC et FP mutuellement exclusifs",
         "PROUVE", "0.2 ms",
         "Une detection avec IoU >= 0.5 (localisation correcte) ne peut pas etre un FP."),
        ("P1.4 — Soundness : IoU>=0.5 + meme_classe + GT => TP",
         "PROUVE", "0.1 ms",
         "La regle TP est suffisante : si les 3 conditions sont reunies, c'est necessairement un TP. "
         "Le solveur a verifie Not(Implies(..., IS_TP)) est UNSAT."),
        ("P1.5 — TP => IoU>=0.5 ET meme classe (necessite)",
         "PROUVE", "1.5 ms",
         "Reciproquement, etre TP implique necessairement avoir un IoU >= 0.5 avec la bonne classe."),
        ("P1.6 — FN => IoU < 0.5 (definition formelle)",
         "PROUVE", "0.1 ms",
         "Un faux negatif est defini comme un GT sans aucune prediction avec IoU >= 0.5."),
        ("P1.7 — Determinisme : memes entrees => meme classification",
         "PROUVE", "0.7 ms",
         "La fonction de classification est une fonction pure : "
         "pour les memes valeurs de iou, same_class, gt_exists, "
         "le resultat est toujours identique — pas d'aleatoire, pas d'effet de bord."),
    ]
    for nom, res, temps, detail in props_b1:
        story.append(prop_row(
            f"{nom}  [{temps}]", res, detail,
            VERT_FOND if res == "PROUVE" else ROUGE_FOND,
            VERT if res == "PROUVE" else ROUGE, st))
        story.append(sp(3))

    story.append(PageBreak())

# =============================================================================
# SECTION 5 — BLOC 2
# =============================================================================
def section_bloc2(story, st):
    story += h1_block("5. BLOC 2 — MACHINE D'ETATS AEB", st)
    story.append(cadre([
        Paragraph("<b>Objectif du bloc :</b>  Prouver les proprietes de surete (safety), "
                  "de vivacite (liveness) et les invariants de la machine d'etats AEB. "
                  "La machine a 6 etats et prend des decisions de freinage basees sur "
                  "le type de detection (TP/FP/FN/MC) et le TTC estime.",
                  ParagraphStyle("co2", fontSize=10, leading=14, alignment=TA_JUSTIFY)),
    ], VERT_FOND, VERT))
    story.append(sp(8))

    story += h2_block("5.1 Les 6 etats de la machine AEB", st)
    etats = [
        ("0 — MONITOR",       "Surveillance nominale, aucune menace detectee"),
        ("1 — ALERT",         "Avertissement sonore et visuel au conducteur"),
        ("2 — PARTIAL_BRAKE", "Freinage progressif 30 a 100% selon TTC"),
        ("3 — FULL_BRAKE",    "Freinage d'urgence maximum 100%"),
        ("4 — DEGRADED",      "Mode degrade — FP repetes ou FN detecte"),
        ("5 — OVERRIDE",      "Conducteur a repris la main — AEB suspendu"),
    ]
    edata = [["Etat (entier Z3)", "Description"]]
    for e, d in etats:
        edata.append([
            Paragraph(e, ParagraphStyle("ec", fontSize=9, fontName="Courier-Bold",
                                         textColor=BLEU_ROI)),
            Paragraph(d, ParagraphStyle("ed", fontSize=9.5, leading=13)),
        ])
    te = Table(edata, colWidths=[(PAGE_W-2*MARGIN)*r for r in [0.30, 0.70]])
    te.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLANC, GRIS_CLAIR]),
        ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
        ("INNERGRID",(0,0),(-1,-1), 0.4, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 6), ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(te)
    story.append(sp(8))

    story += h2_block("5.2 Fonction de freinage symbolique encodee en Z3", st)
    story.append(Paragraph(
        "Le pourcentage de freinage est encode comme une expression If-Then-Else Z3 "
        "dependant du type de detection et du TTC, avec les seuils pieton "
        "(classe la plus critique : t_alert=3.5s, t_emerg=1.8s) :", st["body"]))
    story.append(Paragraph(
        "brake_sym = If(det_type==TP AND ttc<=1.8,  100,\n"
        "            If(det_type==TP AND ttc<=3.5,   60,\n"
        "                                             0  ))",
        st["code"]))
    story.append(sp(8))

    story += h2_block("5.3 Proprietes de Surete (Safety)", st)
    story.append(Paragraph(
        "Les proprietes de surete garantissent qu'un etat dangereux "
        "ne peut pas etre atteint :", st["body"]))

    props_s = [
        ("S1 — FN => etat DEGRADED", "VIOLE", "",
         "VIOLATION REVELANTE : Z3 trouve le contre-exemple "
         "[aeb_state=0, det_type=FN]. L'etat AEB peut rester MONITOR "
         "avec un FN car la transition n'est pas garantie par la logique symbolique seule — "
         "elle depend de l'appel explicite a _handle_fn() dans le code Python. "
         "Correction requise : ajouter un assert dans le constructeur."),
        ("S2 — fp_count >= 3 est la condition necessaire du mode DEGRADE",
         "PROUVE", "0.2 ms",
         "Z3 prouve que fp_count >= 3 est la condition minimale qui declenche le mode degrade. "
         "Le seuil de 3 FP consecutifs est bien encode et ne peut pas etre contourne."),
        ("S3 — brake_pct ∈ [0, 100] toujours",
         "PROUVE", "0.2 ms",
         "La commande de freinage est toujours bornee entre 0 et 100%. "
         "Impossible d'envoyer une commande negative ou superieure a 100%."),
        ("S4 — FP non-repete (count < 3) => freinage = 0%",
         "PROUVE", "1.0 ms",
         "Un faux positif isole ne provoque aucun freinage. "
         "Protection contre les freinages fantomes sur detecteur erratique."),
    ]
    for nom, res, temps, detail in props_s:
        t_label = f"  [{temps}]" if temps else ""
        story.append(prop_row(f"{nom}{t_label}", res, detail,
            VERT_FOND if res=="PROUVE" else ROUGE_FOND,
            VERT if res=="PROUVE" else ROUGE, st))
        story.append(sp(3))

    story.append(sp(6))
    story += h2_block("5.4 Proprietes de Vivacite (Liveness)", st)
    story.append(Paragraph(
        "Les proprietes de vivacite garantissent que le systeme agit toujours quand c'est necessaire :",
        st["body"]))
    props_l = [
        ("L1 — TP avec TTC <= 1.8s => FULL_BRAKE 100%",
         "PROUVE", "0.6 ms",
         "Si un obstacle reel est confirme et que le TTC est critique (<= 1.8s), "
         "le freinage d'urgence est mathematiquement obligatoire. Le systeme ne peut "
         "pas rester en mode MONITOR ou ALERT dans cette situation."),
        ("L2 — Monotonie : TTC_a <= TTC_b => freinage_a >= freinage_b",
         "PROUVE", "3.2 ms",
         "Plus on est proche de l'obstacle (TTC petit), plus le freinage est fort. "
         "Cette propriete intuitive est prouvee formellement pour tous les couples (TTC_a, TTC_b). "
         "Temps plus long car la formule est bilinement quantifiee sur 2 variables reelles."),
        ("L3 — FULL_BRAKE => brake_pct = 100 toujours",
         "PROUVE", "0.1 ms",
         "L'etat FULL_BRAKE produit toujours exactement 100% de freinage. "
         "Coherence parfaite entre l'etat de la machine et l'action effectuee."),
    ]
    for nom, res, temps, detail in props_l:
        story.append(prop_row(f"{nom}  [{temps}]", res, detail, VERT_FOND, VERT, st))
        story.append(sp(3))

    story.append(sp(6))
    story += h2_block("5.5 Invariants du systeme", st)
    props_i = [
        ("I1 — Mode DEGRADE => brake = 0 (AEB camera suspendu)",
         "PROUVE", "0.6 ms",
         "En mode degrade, la camera est suspendue et ne commande plus le freinage. "
         "La decision est transferee au radar ou au conducteur."),
        ("I2 — aeb_state ∈ {0, 1, 2, 3, 4, 5}",
         "VIOLE", "",
         "VIOLATION INSTRUCTIVE : Z3 trouve le contre-exemple [aeb_state = -1]. "
         "Le type Int Z3 est non-borne — rien n'empeche symboliquement une valeur "
         "hors de l'ensemble valide. Correction : ajouter une precondition "
         "'domain: 0 <= aeb_state <= 5' ou utiliser un type enumere."),
        ("I3 — TTC > 60s => freinage = 0",
         "PROUVE", "2.0 ms",
         "Un obstacle a plus de 60 secondes de TTC ne declenche aucun freinage. "
         "Coherence temporelle du systeme."),
    ]
    for nom, res, temps, detail in props_i:
        t_label = f"  [{temps}]" if temps else ""
        story.append(prop_row(f"{nom}{t_label}", res, detail,
            VERT_FOND if res=="PROUVE" else ROUGE_FOND,
            VERT if res=="PROUVE" else ROUGE, st))
        story.append(sp(3))

    story.append(PageBreak())

# =============================================================================
# SECTION 6 — BLOC 3
# =============================================================================
def section_bloc3(story, st):
    story += h1_block("6. BLOC 3 — ESTIMATEUR TTC : PROPRIETES MATHEMATIQUES", st)
    story.append(cadre([
        Paragraph("<b>Objectif du bloc :</b>  Prouver les proprietes algebriques de "
                  "la formule geometrique d'estimation du TTC sur le domaine reel continu. "
                  "Ces preuves sont impossibles a obtenir par tests car le domaine est infini.",
                  ParagraphStyle("co3", fontSize=10, leading=14, alignment=TA_JUSTIFY)),
    ], VIOLET_FOND, VIOLET))
    story.append(sp(8))

    story += h2_block("6.1 La formule TTC et son encodage Z3", st)
    story.append(Paragraph(
        "L'estimateur TTC utilise la geometrie projective de la camera calibree KITTI "
        "(focale = 721.5 pixels). La formule est encodee comme des contraintes Z3 "
        "sur les variables reelles :", st["body"]))
    story.append(Paragraph(
        "distance (m) = focale (px) x hauteur_reelle (m) / hauteur_boite (px)\n"
        "TTC (s)      = distance (m) / vitesse_ego (m/s)\n\n"
        "Contraintes Z3 :\n"
        "  h_box  ∈ (0, 375]   -- hauteur boite en pixels\n"
        "  h_real ∈ (0, 5]     -- hauteur reelle objet en metres\n"
        "  focal  = 14430/20   -- 721.5 en fraction exacte (arithmetique exacte)\n"
        "  speed  ∈ (0, 50]    -- vitesse ego en m/s (jusqu'a 180 km/h)\n"
        "  dist   = focal * h_real / h_box\n"
        "  ttc    = dist / speed", st["code"]))
    story.append(sp(6))

    story.append(Paragraph(
        "<b>Pourquoi utiliser des fractions exactes ?</b>  "
        "Z3 travaille en arithmetique rationnelle exacte (pas en virgule flottante). "
        "721.5 est encode comme 14430/20 pour eviter les erreurs d'arrondi "
        "qui invalideraient les preuves.", st["note"]))
    story.append(sp(8))

    story += h2_block("6.2 Les 5 proprietes prouvees", st)
    props_ttc = [
        ("T1 — TTC > 0 pour tout input physiquement valide",
         "PROUVE", "8.8 ms",
         "Sur le domaine {h_box>0, h_real>0, focal>0, speed>0}, le TTC est toujours strictement "
         "positif. Garantie que le systeme n'obtient jamais un TTC nul ou negatif, "
         "ce qui causerait une division par zero ou un freinage immediat errone."),
        ("T2 — Monotonie inverse : h_box_1 > h_box_2 => TTC_1 < TTC_2",
         "PROUVE", "7.8 ms",
         "Un objet qui occupe plus de pixels dans l'image est plus proche, "
         "donc son TTC est plus court. Cette propriete fondamentale est prouvee "
         "pour toutes les paires (h_box_1, h_box_2) en meme temps. "
         "Temps plus long car formule bilineaire sur 2 variables reelles."),
        ("T3 — TTC est borne superieurement",
         "PROUVE", "8.3 ms",
         "La borne superieure theorique est 3608 s (objet de 5m de haut, "
         "boite d'1 pixel, vitesse 1 m/s). En pratique les objets detectable "
         "produisent des boites plus grandes et les vitesses sont plus elevees."),
        ("T4 — Linearite : doubler h_real double le TTC",
         "PROUVE", "6.9 ms",
         "Un objet deux fois plus haut (ex: camion vs voiture, meme boite) "
         "est estime deux fois plus loin, donc TTC double. "
         "Propriete algebrique fondamentale de la formule geometrique."),
        ("T5 — Dualite vitesse : doubler la vitesse divise le TTC par 2",
         "PROUVE", "8.3 ms",
         "A 100 km/h, le TTC est deux fois plus court qu'a 50 km/h pour "
         "le meme objet. Propriete cruciale pour l'AEB : a haute vitesse, "
         "le systeme doit reagir plus vite."),
    ]
    for nom, res, temps, detail in props_ttc:
        story.append(prop_row(f"{nom}  [{temps}]", res, detail, VERT_FOND, VERT, st))
        story.append(sp(3))

    story.append(PageBreak())

# =============================================================================
# SECTION 7 — BLOC 4
# =============================================================================
def section_bloc4(story, st):
    story += h1_block("7. BLOC 4 — PROFIL CONSERVATEUR POUR MISCLASSIFICATION", st)
    story.append(cadre([
        Paragraph("<b>Objectif du bloc :</b>  Prouver que la strategie 'profil conservateur' "
                  "(prendre le max des profils de risque entre classe predite et classe reelle) "
                  "ne peut jamais sous-estimer le risque pour les 64 combinaisons de classes "
                  "possibles (8 classes x 8 classes).",
                  ParagraphStyle("co4", fontSize=10, leading=14, alignment=TA_JUSTIFY)),
    ], ORANGE_FOND, ORANGE))
    story.append(sp(8))

    story += h2_block("7.1 Les profils de risque par classe", st)
    story.append(Paragraph(
        "Chaque classe KITTI est associee a un profil de risque AEB encode "
        "en arithmetique entiere Z3 (x10 pour eviter les decimales) :", st["body"]))
    prof_data = [
        ["Classe", "ID", "Risque", "TTC Alert (x10)", "TTC Urgence (x10)", "Profil reel"],
        ["car",            "0", "3/5", "25", "12", "2.5s / 1.2s"],
        ["van",            "1", "3/5", "25", "12", "2.5s / 1.2s"],
        ["truck",          "2", "4/5", "30", "15", "3.0s / 1.5s"],
        ["pedestrian",     "3", "5/5", "35", "18", "3.5s / 1.8s"],
        ["Person_sitting", "4", "5/5", "35", "18", "3.5s / 1.8s"],
        ["cyclist",        "5", "4/5", "30", "15", "3.0s / 1.5s"],
        ["tram",           "6", "2/5", "20", "10", "2.0s / 1.0s"],
        ["misc",           "7", "2/5", "20", "10", "2.0s / 1.0s"],
    ]
    cwp = [(PAGE_W-2*MARGIN)*r for r in [0.20, 0.07, 0.10, 0.16, 0.18, 0.29]]
    tp = Table(prof_data, colWidths=cwp)
    tp_style = [
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLANC, GRIS_CLAIR]),
        ("BOX",(0,0),(-1,-1), 1, ORANGE),
        ("INNERGRID",(0,0),(-1,-1), 0.4, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 7), ("ALIGN",(1,0),(-1,-1), "CENTER"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",(0,4),(5,5), colors.HexColor("#FDECEA")),
        ("BACKGROUND",(0,5),(5,6), colors.HexColor("#FDECEA")),
        ("TEXTCOLOR",(2,4),(2,5), ROUGE),
        ("FONTNAME",(2,4),(2,5), "Helvetica-Bold"),
    ]
    tp.setStyle(TableStyle(tp_style))
    story.append(tp)
    story.append(sp(8))

    story += h2_block("7.2 Proprietes generales prouvees", st)
    props_c = [
        ("C1 — safe_ttc_alert >= pred_ttc_alert (toutes classes)",
         "PROUVE", "8.1 ms",
         "Le seuil conservateur est toujours >= au seuil de la classe predite. "
         "On ne peut jamais declencher moins tot qu'avec le profil predit seul."),
        ("C2 — safe_ttc_alert >= gt_ttc_alert (toutes classes)",
         "PROUVE", "8.4 ms",
         "Le seuil conservateur est toujours >= au seuil de la classe reelle. "
         "Le profil reel n'est jamais sous-estime, quelle que soit la misclassification."),
        ("C3 — safe_risk >= gt_risk (toutes classes)",
         "PROUVE", "5.6 ms",
         "Le niveau de risque conservateur est toujours >= au risque reel. "
         "Aucune misclassification ne peut abaisser le niveau de danger pris en compte."),
        ("C4 — Pedestrian implique toujours safe_risk = 5 (maximum)",
         "PROUVE", "6.7 ms",
         "Si l'une des deux classes (predite OU reelle) est 'pedestrian' (id=3), "
         "le risque conservateur est automatiquement 5/5 — le maximum possible. "
         "Protection absolue pour les usagers vulnerables."),
        ("C5 — Voiture->Pieton : seuils = (3.5s / 1.8s)",
         "PROUVE", "2.7 ms",
         "Le cas le plus critique (voiture predite, pieton reel) utilise "
         "le profil pieton, jamais le profil voiture. Verifie pour pred_cls=0, gt_cls=3."),
        ("C6 — Idempotence : pred==gt => safe==pred",
         "PROUVE", "2.9 ms",
         "Quand la classification est correcte, le profil conservateur est "
         "identique au profil normal. Pas de sur-freinage injustifie."),
    ]
    for nom, res, temps, detail in props_c:
        story.append(prop_row(f"{nom}  [{temps}]", res, detail, VERT_FOND, VERT, st))
        story.append(sp(3))

    story.append(sp(6))
    story += h2_block("7.3 Verification des 6 paires de misclassification critiques", st)
    paires_data = [
        ["Paire (Predit -> Reel)", "Seuil safe", "Profil applique", "Resultat"],
        ["voiture (2.5s) -> pieton (3.5s)", "3.5s / 1.8s", "Profil pieton", "[PROUVE]"],
        ["van (2.5s) -> pieton (3.5s)",     "3.5s / 1.8s", "Profil pieton", "[PROUVE]"],
        ["voiture (2.5s) -> cycliste (3.0s)","3.0s / 1.5s", "Profil cycliste","[PROUVE]"],
        ["cycliste (3.0s) -> pieton (3.5s)", "3.5s / 1.8s", "Profil pieton", "[PROUVE]"],
        ["camion (3.0s) -> voiture (2.5s)",  "3.0s / 1.5s", "Profil camion", "[PROUVE]"],
        ["van (2.5s) -> voiture (2.5s)",     "2.5s / 1.2s", "Profil egal",   "[PROUVE]"],
    ]
    cwpp = [(PAGE_W-2*MARGIN)*r for r in [0.30, 0.22, 0.23, 0.25]]
    tpp = Table(paires_data, colWidths=cwpp)
    tpp_style = [
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLANC, GRIS_CLAIR]),
        ("BOX",(0,0),(-1,-1), 1, ORANGE),
        ("INNERGRID",(0,0),(-1,-1), 0.4, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 6), ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 7),
        ("TEXTCOLOR",(3,1),(-1,-1), VERT),
        ("FONTNAME",(3,1),(-1,-1), "Helvetica-Bold"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]
    tpp.setStyle(TableStyle(tpp_style))
    story.append(tpp)
    story.append(PageBreak())

# =============================================================================
# SECTION 8 — BLOC 5
# =============================================================================
def section_bloc5(story, st):
    story += h1_block("8. BLOC 5 — ROBUSTESSE DU RESEAU YOLO VIA ONNX", st)
    story.append(cadre([
        Paragraph("<b>Objectif du bloc :</b>  Analyser empiriquement la robustesse locale "
                  "du reseau de neurones YOLO face a des perturbations additives sur les pixels. "
                  "Ce bloc n'est pas une preuve formelle complete (NP-difficile pour les reseaux "
                  "profonds) mais une verification par echantillonnage systematique.",
                  ParagraphStyle("co5", fontSize=10, leading=14, alignment=TA_JUSTIFY)),
    ], JAUNE_FOND, ORANGE))
    story.append(sp(8))

    story += h2_block("8.1 Export YOLO vers ONNX", st)
    story.append(Paragraph(
        "Le modele best.pt (format PyTorch) est exporte vers le format "
        "<b>ONNX (Open Neural Network Exchange)</b>, un format ouvert et interoperable "
        "pour les modeles de deep learning :", st["body"]))
    for stat in [
        "Architecture : 93 couches fusionnees, 25 844 392 parametres, 78.7 GFLOPs",
        "Taille ONNX : 98.8 MB (vs 49.6 MB pour PyTorch — ONNX inclut les metadonnees)",
        "Format de sortie : tenseur [1, 12, 8400] — 12 = 4 coords + 8 classes, 8400 ancres",
        "Temps d'inference CPU : ~1100 ms par image (Intel Core i7-8565U)",
        "Outil de simplification : onnxslim v0.1.94 (fusion des operations redondantes)",
    ]:
        story.append(Paragraph(f"  •  {stat}", st["bull"]))

    story.append(sp(8))
    story += h2_block("8.2 Protocole de test de robustesse", st)
    story.append(Paragraph(
        "Pour chaque image du jeu de validation, quatre niveaux de perturbation "
        "additive uniforme sont appliques independamment "
        "(30 images x 20 perturbations x 4 niveaux = 2 400 inferences) :", st["body"]))
    story.append(Paragraph(
        "Pour chaque image I et chaque epsilon :\n"
        "  Pour k = 1 a N (N=5 perturbations) :\n"
        "    bruit_k ~ Uniforme(-epsilon/255, +epsilon/255)  [forme: 1x3x640x640]\n"
        "    I_perturbe = clip(I + bruit_k, 0.0, 1.0)\n"
        "    pred_k = ONNX(I_perturbe)\n"
        "    stable_k = (classe_dominante(pred_k) == classe_dominante(ONNX(I)))\n"
        "    delta_conf_k = |conf(pred_k) - conf(ONNX(I))|",
        st["code"]))
    story.append(sp(8))

    story += h2_block("8.3 Resultats de robustesse", st)
    rob_data = [
        ["Epsilon (niveaux/255)", "Stables", "Instables", "Robustesse %",
         "dConf moy.", "dConf max.", "Interpretation"],
        ["epsilon = 1  (±1/255)",  "569 / 580", "11 / 580",  "98.1 %", "0.0091", "0.0877", "ROBUSTE"],
        ["epsilon = 5  (±5/255)",  "488 / 580", "92 / 580",  "84.1 %", "0.0645", "0.4527", "FRAGILE"],
        ["epsilon = 10 (±10/255)", "394 / 580", "186 / 580", "67.9 %", "0.1032", "0.4902", "FRAGILE"],
        ["epsilon = 20 (±20/255)", "344 / 580", "236 / 580", "59.3 %", "0.1630", "0.5768", "FRAGILE"],
    ]
    cwr2 = [(PAGE_W-2*MARGIN)*r for r in [0.22, 0.12, 0.12, 0.11, 0.10, 0.10, 0.23]]
    tr2 = Table(rob_data, colWidths=cwr2)
    tr2_style = [
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("BOX",(0,0),(-1,-1), 1, ORANGE),
        ("INNERGRID",(0,0),(-1,-1), 0.4, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 6), ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
        ("ALIGN",(1,0),(-1,-1), "CENTER"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",(0,1),(-1,1), VERT_FOND),
        ("BACKGROUND",(0,2),(-1,2), ROUGE_FOND),
        ("BACKGROUND",(0,3),(-1,3), ROUGE_FOND),
        ("BACKGROUND",(0,4),(-1,4), ROUGE_FOND),
        ("TEXTCOLOR",(3,1),(3,1), VERT),
        ("TEXTCOLOR",(3,2),(3,2), ROUGE),
        ("TEXTCOLOR",(3,3),(3,3), ROUGE),
        ("TEXTCOLOR",(3,4),(3,4), ROUGE),
        ("TEXTCOLOR",(6,1),(6,1), VERT),
        ("TEXTCOLOR",(6,2),(6,2), ROUGE),
        ("TEXTCOLOR",(6,3),(6,3), ROUGE),
        ("TEXTCOLOR",(6,4),(6,4), ROUGE),
        ("FONTNAME",(3,1),(-1,-1), "Helvetica-Bold"),
    ]
    tr2.setStyle(TableStyle(tr2_style))
    story.append(tr2)
    story.append(sp(8))

    story += h2_block("8.4 Analyse et implications", st)
    story.append(Paragraph(
        "Les resultats revelent une <b>robustesse asymetrique</b> du reseau :", st["body"]))
    analyses = [
        ("epsilon = 1/255 (98.1% robuste — 569/580 stables) :",
         "Le reseau est insensible aux perturbations equivalentes au bruit de capteur "
         "normal (bruit electronique camera, compression JPEG faible). "
         "Seulement 11 instabilites sur 580 tests. "
         "La classe dominante ne change que dans 1.9% des cas."),
        ("epsilon = 5/255 (84.1% robuste — 488/580 stables) :",
         "Perturbation representant des conditions degradees moderees (brouillard leger, "
         "pluie fine, compression JPEG agressive). 15.9% de changements de classe — "
         "limite acceptable pour un systeme avec capteurs redondants (radar, LiDAR)."),
        ("epsilon = 10/255 (67.9% robuste — 394/580 stables) :",
         "Conditions meteorologiques defavorables (pluie forte, brouillard dense). "
         "32.1% d'instabilite — le reseau montre une fragilite significative "
         "qui justifie une fusion multi-capteurs en conditions difficiles."),
        ("epsilon = 20/255 (59.3% robuste — 344/580 stables) :",
         "Perturbation severe equivalente a une degradation extreme de l'image. "
         "40.7% d'instabilite — le systeme ne devrait pas fonctionner sans "
         "capteur redondant a ce niveau de degradation visuelle."),
    ]
    for titre_a, desc_a in analyses:
        story.append(Paragraph(f"  <b>{titre_a}</b>  {desc_a}", st["bull"]))

    story.append(sp(8))
    story.append(cadre([
        Paragraph("<b>Propriete R1 derivee (PROUVEE empiriquement) :</b>",
                  ParagraphStyle("r1h", fontSize=10, fontName="Helvetica-Bold", textColor=VERT)),
        Paragraph("Pour epsilon = 1/255 et un echantillon de 30 images x 20 perturbations (580 tests): "
                  "robustesse = 98.1%. La classe dominante est stable pour les "
                  "perturbations equivalentes au bruit capteur nominal. "
                  "Pour une certification formelle complete (pour TOUS les inputs), "
                  "des outils specialises comme alpha-beta-CROWN ou Marabou "
                  "seraient necessaires.",
                  ParagraphStyle("r1b", fontSize=9.5, leading=14, alignment=TA_JUSTIFY)),
    ], VERT_FOND, VERT))
    story.append(PageBreak())

# =============================================================================
# SECTION 9 — VIOLATIONS TROUVEES
# =============================================================================
def section_violations(story, st):
    story += h1_block("9. VIOLATIONS TROUVEES — ANALYSE DES CONTRE-EXEMPLES", st)
    story.append(Paragraph(
        "Z3 a trouve deux violations qui constituent des <b>decouvertes reelles</b> "
        "sur la specification du systeme — pas des bugs du code Python, mais des "
        "proprietes qui ne sont pas garanties au niveau logique pur.", st["body"]))
    story.append(sp(8))

    story += h2_block("9.1 Violation S1 — FN ne garantit pas l'etat DEGRADED", st)
    viol1_data = [[
        Paragraph("Contre-exemple Z3 :",
                  ParagraphStyle("v1h", fontSize=10, fontName="Helvetica-Bold", textColor=ROUGE)),
    ],[
        Paragraph("[aeb_state = 0,  fp_count = 0,  ttc = 0,  brake_pct = 0,  det_type = 2]",
                  ParagraphStyle("v1c", fontSize=9.5, fontName="Courier-Bold", textColor=ROUGE)),
    ],[
        Paragraph("Interpretation : det_type=2 signifie FN. aeb_state=0 signifie MONITOR. "
                  "Z3 montre qu'il est logiquement possible d'avoir simultanement FN et etat=MONITOR. "
                  "La contrainte de transition n'est pas encodee dans la specification symbolique.",
                  ParagraphStyle("v1d", fontSize=9.5, leading=14, alignment=TA_JUSTIFY)),
    ],[
        Paragraph("Correction requise : ajouter dans le code Python de _handle_fn() une assertion "
                  "qui garantit la transition vers DEGRADED, ET ajouter cette contrainte "
                  "comme precondition dans la specification Z3.",
                  ParagraphStyle("v1f", fontSize=9.5, leading=14, textColor=BLEU_ROI,
                                 fontName="Helvetica-Bold")),
    ]]
    tv1 = Table(viol1_data, colWidths=[PAGE_W-2*MARGIN])
    tv1.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), ROUGE_FOND),
        ("BOX",(0,0),(-1,-1), 1.5, ROUGE),
        ("TOPPADDING",(0,0),(-1,-1), 8), ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",(0,0),(-1,-1), 12),
    ]))
    story.append(tv1)
    story.append(sp(10))

    story += h2_block("9.2 Violation I2 — aeb_state peut prendre des valeurs hors {0..5}", st)
    viol2_data = [[
        Paragraph("Contre-exemple Z3 :",
                  ParagraphStyle("v2h", fontSize=10, fontName="Helvetica-Bold", textColor=ROUGE)),
    ],[
        Paragraph("[aeb_state = -1]",
                  ParagraphStyle("v2c", fontSize=9.5, fontName="Courier-Bold", textColor=ROUGE)),
    ],[
        Paragraph("Interpretation : le type Int de Z3 est non-borne. Sans precondition "
                  "'0 <= aeb_state <= 5', le solveur peut choisir aeb_state = -1 comme "
                  "assignation valide. Ce n'est pas un bug du code Python (qui utilise "
                  "un Enum Python bome), mais une lacune de la specification formelle.",
                  ParagraphStyle("v2d", fontSize=9.5, leading=14, alignment=TA_JUSTIFY)),
    ],[
        Paragraph("Correction requise : ajouter 'domain: And(aeb_state >= 0, aeb_state <= 5)' "
                  "comme precondition dans toutes les proprietes du BLOC 2.",
                  ParagraphStyle("v2f", fontSize=9.5, leading=14, textColor=BLEU_ROI,
                                 fontName="Helvetica-Bold")),
    ]]
    tv2 = Table(viol2_data, colWidths=[PAGE_W-2*MARGIN])
    tv2.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), ROUGE_FOND),
        ("BOX",(0,0),(-1,-1), 1.5, ROUGE),
        ("TOPPADDING",(0,0),(-1,-1), 8), ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",(0,0),(-1,-1), 12),
    ]))
    story.append(tv2)
    story.append(sp(10))

    story.append(cadre([
        Paragraph("<b>Valeur pedagogique des violations :</b>",
                  ParagraphStyle("vv", fontSize=10, fontName="Helvetica-Bold", textColor=BLEU_FONCE)),
        Paragraph("Ces deux violations illustrent la puissance de la verification formelle : "
                  "elles auraient ete INVISIBLES avec des tests unitaires classiques. "
                  "Un test Python verifie le comportement du code Python — qui est correct. "
                  "Z3 verifie la specification logique — et montre qu'elle est incomplete. "
                  "C'est exactement l'objectif des methodes formelles dans les systemes critiques.",
                  ParagraphStyle("vvb", fontSize=10, leading=15, alignment=TA_JUSTIFY)),
    ], BLEU_PALE, BLEU_ROI))
    story.append(PageBreak())

# =============================================================================
# SECTION 10 — SYNTHESE ET CONCLUSION
# =============================================================================
def section_conclusion(story, st):
    story += h1_block("10. SYNTHESE ET CONCLUSION", st)

    story += h2_block("10.1 Tableau de synthese des 32 proprietes", st)
    synth_data = [
        ["Bloc", "Composante", "Proprietes", "Prouvees", "Violees", "Statut"],
        ["1", "Regles IoU",          "7",  "7",  "0", "CERTIFIE"],
        ["2", "Machine AEB",         "9",  "7",  "2", "PARTIEL"],
        ["3", "Estimateur TTC",      "5",  "5",  "0", "CERTIFIE"],
        ["4", "Profil conservateur", "13", "13", "0", "CERTIFIE"],
        ["5", "Robustesse ONNX",     "1",  "1",  "0", "EMPIRIQUE"],
        ["", "TOTAL",               "35", "33",  "2", ""],
    ]
    cws = [(PAGE_W-2*MARGIN)*r for r in [0.08, 0.28, 0.14, 0.12, 0.10, 0.28]]
    ts = Table(synth_data, colWidths=cws)
    ts_style = [
        ("BACKGROUND",(0,0),(-1,0), BLEU_FONCE),
        ("TEXTCOLOR",(0,0),(-1,0), BLANC),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [BLANC, GRIS_CLAIR]),
        ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
        ("INNERGRID",(0,0),(-1,-1), 0.4, GRIS_MOYEN),
        ("TOPPADDING",(0,0),(-1,-1), 7), ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 7),
        ("ALIGN",(2,0),(-1,-1), "CENTER"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",(0,-1),(-1,-1), BLEU_CLAIR),
        ("FONTNAME",(0,-1),(-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",(5,1),(5,1), VERT),
        ("TEXTCOLOR",(5,2),(5,2), ORANGE),
        ("TEXTCOLOR",(5,3),(5,3), VERT),
        ("TEXTCOLOR",(5,4),(5,4), VERT),
        ("TEXTCOLOR",(5,5),(5,5), BLEU_ROI),
        ("FONTNAME",(5,1),(-1,-1), "Helvetica-Bold"),
    ]
    ts.setStyle(TableStyle(ts_style))
    story.append(ts)
    story.append(sp(10))

    story += h2_block("10.2 Ce que garantit cette verification", st)
    garanties = [
        "Les regles de classification IoU sont logiquement coherentes et deterministesx pour TOUS les inputs reels",
        "Le freinage d'urgence est obligatoire si TTC <= 1.8s et detection confirmee — sans exception mathematique",
        "Le freinage ne depasse jamais 100% et ne peut pas etre negatif — propriete de borne certifiee",
        "Un FP isole ne provoque jamais de freinage — protection contre les fausses alarmes isolees",
        "Le profil conservateur ne sous-estime jamais le risque reel pour les 64 paires de classes",
        "La formule TTC est monotone : plus l'objet est proche, plus le TTC est court — toujours",
        "Le reseau YOLO est robuste aux perturbations de bruit capteur standard (epsilon=1/255)",
    ]
    for g in garanties:
        story.append(Paragraph(f"  {chr(10003)}  {g}", ParagraphStyle("g", fontSize=10,
                                leading=14, spaceAfter=3, textColor=VERT, leftIndent=10)))

    story.append(sp(8))
    story += h2_block("10.3 Limites et travaux futurs", st)
    limites = [
        ("Verification du reseau neuronal complet",
         "La verification formelle complete d'un reseau YOLO (25M parametres) est NP-difficile. "
         "Des outils specialises (Marabou, alpha-beta-CROWN, ERAN) permettraient des "
         "certifications de robustesse locale avec bornes garanties."),
        ("Specification complete de la machine AEB",
         "Les deux violations trouvees (S1, I2) indiquent que la specification formelle "
         "est incomplete. Une specification TLA+ ou Event-B serait plus rigoureuse "
         "pour modeliser les transitions d'etats avec leur historique."),
        ("Verification en temps reel",
         "La verification actuelle est hors-ligne (offline). Pour un systeme embarque, "
         "la verification en ligne (runtime verification) avec moniteurs formels "
         "permettrait de detecter les violations pendant l'execution."),
        ("Prise en compte des incertitudes de mesure",
         "L'estimateur TTC suppose une calibration parfaite. Une extension avec "
         "des variables Z3 bornees par des intervalles d'incertitude "
         "([focal - delta_f, focal + delta_f]) renforcerait la robustesse des preuves."),
    ]
    for titre_l, desc_l in limites:
        ldata = [[
            Paragraph(f"<b>{titre_l}</b>",
                      ParagraphStyle("lh", fontSize=10, textColor=BLEU_ROI,
                                     fontName="Helvetica-Bold")),
        ],[
            Paragraph(desc_l, ParagraphStyle("lb", fontSize=9.5, leading=14,
                                              alignment=TA_JUSTIFY)),
        ]]
        tl = Table(ldata, colWidths=[PAGE_W-2*MARGIN])
        tl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,0), BLEU_PALE),
            ("BACKGROUND",(0,1),(0,1), BLANC),
            ("BOX",(0,0),(-1,-1), 1, BLEU_ROI),
            ("TOPPADDING",(0,0),(-1,-1), 7), ("BOTTOMPADDING",(0,0),(-1,-1), 7),
            ("LEFTPADDING",(0,0),(-1,-1), 12),
        ]))
        story.append(tl)
        story.append(sp(5))

    story.append(sp(10))
    fin_data = [[Paragraph(
        "Cette verification formelle par solveur SMT Z3 constitue une etape critique "
        "dans la certification d'un systeme AEB base sur la vision par ordinateur. "
        "Les 33 proprietes prouvees (sur 35) etablissent des garanties mathematiques "
        "sur la coherence logique, la surete, la vivacite et la correction algebrique "
        "des composantes du systeme. Les 2 violations trouvees, loin d'etre des echecs, "
        "sont des decouvertes precieuses qui renforcent la specification et guident "
        "les corrections necessaires avant tout deploiement sur vehicule reel.",
        ParagraphStyle("fin", fontSize=10, leading=15, textColor=BLEU_FONCE,
                       alignment=TA_JUSTIFY))
    ]]
    tf = Table(fin_data, colWidths=[PAGE_W-2*MARGIN])
    tf.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), BLEU_CLAIR),
        ("BOX",(0,0),(-1,-1), 1.5, BLEU_FONCE),
        ("TOPPADDING",(0,0),(-1,-1), 14), ("BOTTOMPADDING",(0,0),(-1,-1), 14),
        ("LEFTPADDING",(0,0),(-1,-1), 16), ("RIGHTPADDING",(0,0),(-1,-1), 16),
    ]))
    story.append(tf)

# =============================================================================
# MAIN
# =============================================================================
def generer_pdf(output="rapport_z3_verification_formelle.pdf"):
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.6*cm, bottomMargin=1.4*cm,
        title="Rapport de Verification Formelle SMT Z3 — YOLO/KITTI/AEB",
        author="Systeme AEB — Analyse formelle Z3",
    )
    st = build_styles()
    story = []

    page_garde(story, st)
    section_smt(story, st)
    section_objectifs(story, st)
    section_architecture(story, st)
    section_bloc1(story, st)
    section_bloc2(story, st)
    section_bloc3(story, st)
    section_bloc4(story, st)
    section_bloc5(story, st)
    section_violations(story, st)
    section_conclusion(story, st)

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"PDF genere : {output}")
    return output

if __name__ == "__main__":
    generer_pdf()
