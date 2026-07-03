"""
Systeme AEB (Automatic Emergency Braking) - Approche Formelle
Reaction du systeme selon le type de detection YOLO :
  TP  (Succes Nominal)       -> Pipeline AEB nominal
  FP  (Faux Positif)         -> Freinage fantome -> danger arriere
  FN  (Faux Negatif)         -> Obstacle non detecte -> collision
  MC  (Mauvaise Classif.)    -> Mauvaise estimation du risque -> reponse inadaptee
"""

import sys
import os
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# ─── Classes KITTI et profils de risque ──────────────────────────────────────

CLASSES = {
    0: "car",
    1: "van",
    2: "truck",
    3: "pedestrian",
    4: "Person_sitting",
    5: "cyclist",
    6: "tram",
    7: "misc",
}

# Profil de risque par classe : (niveau 1-5, TTC_seuil_alerte[s], TTC_seuil_urgence[s])
RISK_PROFILE = {
    0: (3, 2.5, 1.2),   # car
    1: (3, 2.5, 1.2),   # van
    2: (4, 3.0, 1.5),   # truck  - masse elevee
    3: (5, 3.5, 1.8),   # pedestrian - vulnerable
    4: (5, 3.5, 1.8),   # Person_sitting - vulnerable
    5: (4, 3.0, 1.5),   # cyclist
    6: (2, 2.0, 1.0),   # tram - voie fixe
    7: (2, 2.0, 1.0),   # misc
}

# ─── Etats du systeme AEB ─────────────────────────────────────────────────────

class AEBState(Enum):
    MONITOR       = auto()   # Surveillance nominale, aucune menace
    ALERT         = auto()   # Avertissement conducteur (son + affichage)
    PARTIAL_BRAKE = auto()   # Freinage partiel 30-50 %
    FULL_BRAKE    = auto()   # Freinage d'urgence 100 %
    OVERRIDE      = auto()   # Conducteur a repris la main
    DEGRADED      = auto()   # Mode degrade (FP repetes ou FN detecte)

# ─── Types de detection ───────────────────────────────────────────────────────

class DetectionType(Enum):
    NOMINAL_SUCCESS = "TP"
    FALSE_POSITIVE  = "FP"
    FALSE_NEGATIVE  = "FN"
    MISCLASSIF      = "MISCLASSIF"

# ─── Structure d'une detection ────────────────────────────────────────────────

@dataclass
class Detection:
    det_type:     DetectionType
    cls_id:       Optional[int]  = None
    gt_cls_id:    Optional[int]  = None
    confidence:   float          = 0.0
    bbox_height:  float          = 0.0
    image_height: float          = 375.0
    timestamp:    float          = field(default_factory=time.time)

# ─── Estimateur TTC (Time To Collision) ──────────────────────────────────────

class TTCEstimator:
    """
    Estimation du TTC via la hauteur de la boite englobante.
    Calibration empirique KITTI : focale=721.5px.
    """
    FOCAL_LENGTH = 721.5
    OBJ_HEIGHT = {
        0: 1.5, 1: 2.0, 2: 3.5, 3: 1.7,
        4: 1.2, 5: 1.7, 6: 3.5, 7: 1.5,
    }

    def estimate(self, det: Detection, ego_speed_ms: float = 13.9) -> Optional[float]:
        if det.bbox_height <= 0 or det.cls_id is None:
            return None
        real_h   = self.OBJ_HEIGHT.get(det.cls_id, 1.5)
        distance = (self.FOCAL_LENGTH * real_h) / det.bbox_height
        if ego_speed_ms <= 0:
            return None
        return distance / ego_speed_ms


# ─── Machine d'etats AEB ─────────────────────────────────────────────────────

class AEBStateMachine:
    """Machine d'etats formelle du systeme AEB."""

    def __init__(self, ego_speed_kmh: float = 50.0):
        self.state             = AEBState.MONITOR
        self.ego_speed_ms      = ego_speed_kmh / 3.6
        self.ttc_estimator     = TTCEstimator()
        self.fp_count          = 0
        self.fn_count          = 0
        self.history           = []

    def process(self, det: Detection) -> dict:
        if det.det_type == DetectionType.NOMINAL_SUCCESS:
            return self._handle_tp(det)
        elif det.det_type == DetectionType.FALSE_POSITIVE:
            return self._handle_fp(det)
        elif det.det_type == DetectionType.FALSE_NEGATIVE:
            return self._handle_fn(det)
        elif det.det_type == DetectionType.MISCLASSIF:
            return self._handle_misclassif(det)

    # ── TP : Succes Nominal ────────────────────────────────────────────────────

    def _handle_tp(self, det: Detection) -> dict:
        self.fp_count = 0
        self.fn_count = 0

        risk_lvl, ttc_alert, ttc_emerg = RISK_PROFILE.get(det.cls_id, (2, 2.0, 1.0))
        ttc = self.ttc_estimator.estimate(det, self.ego_speed_ms)

        if ttc is None:
            self._transition(AEBState.ALERT)
            return self._report("TP", AEBState.ALERT,
                                "TTC incalculable -> alerte preventive",
                                "AVERTISSEMENT SONORE", 0, det, ttc)

        if ttc <= ttc_emerg:
            self._transition(AEBState.FULL_BRAKE)
            return self._report("TP", AEBState.FULL_BRAKE,
                                f"TTC={ttc:.2f}s <= seuil urgence ({ttc_emerg}s)",
                                "FREINAGE D'URGENCE 100%", 100, det, ttc)

        elif ttc <= ttc_alert:
            self._transition(AEBState.PARTIAL_BRAKE)
            brake_pct = int(30 + 70 * (1 - (ttc - ttc_emerg) / (ttc_alert - ttc_emerg)))
            return self._report("TP", AEBState.PARTIAL_BRAKE,
                                f"TTC={ttc:.2f}s <= seuil alerte ({ttc_alert}s)",
                                f"FREINAGE PARTIEL {brake_pct}%", brake_pct, det, ttc)
        else:
            self._transition(AEBState.ALERT)
            return self._report("TP", AEBState.ALERT,
                                f"TTC={ttc:.2f}s > {ttc_alert}s, surveillance active",
                                "AVERTISSEMENT CONDUCTEUR", 0, det, ttc)

    # ── FP : Faux Positif ─────────────────────────────────────────────────────

    def _handle_fp(self, det: Detection) -> dict:
        """
        FP -> freinage fantome.
        Danger : collision arriere, perte de controle.
        Mitigation : compteur FP, mode degrade si repetes.
        """
        self.fp_count += 1
        self.fn_count  = 0

        if self.fp_count >= 3:
            self._transition(AEBState.DEGRADED)
            return self._report("FP", AEBState.DEGRADED,
                                f"FP repetes ({self.fp_count}) -> mode degrade active",
                                "MODE DEGRADE: AEB suspendu, alerte conducteur",
                                0, det, None,
                                safety_risk="CRITIQUE: risque collision arriere repete")
        else:
            self._transition(AEBState.MONITOR)
            return self._report("FP", AEBState.MONITOR,
                                f"FP #{self.fp_count}: freinage fantome inhibe",
                                "SUPPRESSION FREINAGE, log enregistre",
                                0, det, None,
                                safety_risk="MODERE: freinage non justifie")

    # ── FN : Faux Negatif ─────────────────────────────────────────────────────

    def _handle_fn(self, det: Detection) -> dict:
        """
        FN -> obstacle non detecte -> AEB non declenche.
        Cas le plus dangereux : la voiture ne freine pas.
        Strategie : escalade vers capteurs redondants (radar/lidar).
        """
        self.fn_count += 1
        self.fp_count  = 0
        cls_name = CLASSES.get(det.gt_cls_id, "inconnu") if det.gt_cls_id is not None else "inconnu"

        self._transition(AEBState.DEGRADED)
        return self._report("FN", AEBState.DEGRADED,
                            f"Objet reel '{cls_name}' non detecte -> collision imminente",
                            "ESCALADE VERS CAPTEURS REDONDANTS (RADAR/LIDAR)\n"
                            "     -> Si radar confirme : FREINAGE D'URGENCE 100%\n"
                            "     -> Si radar absent   : ALERTE CRITIQUE CONDUCTEUR",
                            0, det, None,
                            safety_risk="CRITIQUE: AEB aveugle, sans freinage d'urgence")

    # ── Misclassification ─────────────────────────────────────────────────────

    def _handle_misclassif(self, det: Detection) -> dict:
        """
        Mauvaise classification -> mauvais profil de risque applique.
        Strategie : appliquer le profil le plus conservateur entre predit et GT.
        """
        pred_profile = RISK_PROFILE.get(det.cls_id,     (2, 2.0, 1.0))
        gt_profile   = RISK_PROFILE.get(det.gt_cls_id,  (2, 2.0, 1.0)) \
                       if det.gt_cls_id is not None else pred_profile

        safe_risk   = max(pred_profile[0], gt_profile[0])
        safe_ttc_al = max(pred_profile[1], gt_profile[1])
        safe_ttc_em = max(pred_profile[2], gt_profile[2])

        ttc      = self.ttc_estimator.estimate(det, self.ego_speed_ms)
        pred_cls = CLASSES.get(det.cls_id,    "?")
        gt_cls   = CLASSES.get(det.gt_cls_id, "?") if det.gt_cls_id is not None else "inconnu"

        note = (f"Predit: {pred_cls} (risque={pred_profile[0]}) | "
                f"Reel: {gt_cls} (risque={gt_profile[0]}) -> "
                f"Profil conservateur applique (risque={safe_risk})")

        if ttc is not None and ttc <= safe_ttc_em:
            self._transition(AEBState.FULL_BRAKE)
            action    = "FREINAGE D'URGENCE 100% (profil conservateur)"
            brake_pct = 100
        elif ttc is not None and ttc <= safe_ttc_al:
            self._transition(AEBState.PARTIAL_BRAKE)
            brake_pct = 60
            action    = f"FREINAGE PARTIEL {brake_pct}% (profil conservateur)"
        else:
            self._transition(AEBState.ALERT)
            brake_pct = 0
            action    = "ALERTE + surveillance renforcee"

        return self._report("MISCLASSIF", self.state, note, action, brake_pct, det, ttc,
                            safety_risk="MODERE-ELEVE: risque sous-estimation classe vulnerable")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _transition(self, new_state: AEBState):
        self.history.append((self.state, new_state))
        self.state = new_state

    def _report(self, det_label, state, reason, action, brake_pct,
                det: Detection, ttc, safety_risk=""):
        cls_pred = CLASSES.get(det.cls_id,    "N/A") if det.cls_id    is not None else "N/A"
        cls_gt   = CLASSES.get(det.gt_cls_id, "N/A") if det.gt_cls_id is not None else "N/A"
        return {
            "detection_type":  det_label,
            "aeb_state":       state.name,
            "class_predicted": cls_pred,
            "class_gt":        cls_gt,
            "confidence":      round(det.confidence, 3),
            "ttc_seconds":     round(ttc, 3) if ttc else None,
            "brake_percent":   brake_pct,
            "reason":          reason,
            "action":          action,
            "safety_risk":     safety_risk,
        }


# ─── Affichage ────────────────────────────────────────────────────────────────

SEP  = "=" * 65
SEP2 = "-" * 65

def print_report(r: dict):
    tag = {"TP": "[TP]", "FP": "[FP]", "FN": "[FN]", "MISCLASSIF": "[MC]"}
    dt  = r["detection_type"]
    print(f"\n{SEP}")
    print(f"  {tag.get(dt,'[?]')} DETECTION : {dt}   -->   Etat AEB : {r['aeb_state']}")
    print(SEP)
    print(f"  Classe predite    : {r['class_predicted']}")
    print(f"  Classe reelle     : {r['class_gt']}")
    print(f"  Confiance modele  : {r['confidence']:.1%}")
    if r["ttc_seconds"] is not None:
        print(f"  TTC estime        : {r['ttc_seconds']:.2f} s")
    print(f"  Freinage applique : {r['brake_percent']} %")
    print(f"  Raison            : {r['reason']}")
    print(f"  Action AEB        : {r['action']}")
    if r["safety_risk"]:
        print(f"  Risque securite   : *** {r['safety_risk']} ***")


# ─── Scenario de demonstration ────────────────────────────────────────────────

def run_aeb_demo():
    print("\n" + "#"*65)
    print("   SYSTEME AEB - DEMONSTRATION DES 4 TYPES DE DETECTION")
    print("   Vitesse ego : 50 km/h  |  Camera KITTI calibree")
    print("#"*65)

    aeb = AEBStateMachine(ego_speed_kmh=50)

    scenarios = [
        # TP - pieton proche (boite haute = proche ~5m)
        Detection(det_type=DetectionType.NOMINAL_SUCCESS,
                  cls_id=3, gt_cls_id=3, confidence=0.88, bbox_height=220),
        # TP - voiture distante (petite boite)
        Detection(det_type=DetectionType.NOMINAL_SUCCESS,
                  cls_id=0, gt_cls_id=0, confidence=0.75, bbox_height=30),
        # FP #1 - detection fantome
        Detection(det_type=DetectionType.FALSE_POSITIVE,
                  cls_id=0, gt_cls_id=None, confidence=0.31, bbox_height=45),
        # FP #2
        Detection(det_type=DetectionType.FALSE_POSITIVE,
                  cls_id=1, gt_cls_id=None, confidence=0.28, bbox_height=40),
        # FN - pieton traversant non detecte
        Detection(det_type=DetectionType.FALSE_NEGATIVE,
                  cls_id=None, gt_cls_id=3, confidence=0.0, bbox_height=180),
        # MC - cycliste confondu avec voiture
        Detection(det_type=DetectionType.MISCLASSIF,
                  cls_id=0, gt_cls_id=5, confidence=0.52, bbox_height=95),
    ]

    labels = [
        "Scenario 1 - TP : Pieton proche (urgence)",
        "Scenario 2 - TP : Voiture distante (alerte)",
        "Scenario 3 - FP : Detection fantome #1",
        "Scenario 4 - FP : Detection fantome #2",
        "Scenario 5 - FN : Pieton invisible (non detecte)",
        "Scenario 6 - MC : Cycliste confondu avec voiture",
    ]

    for label, det in zip(labels, scenarios):
        print(f"\n  >> {label}")
        report = aeb.process(det)
        print_report(report)

    print(f"\n\n{SEP}")
    print("  RESUME DES TRANSITIONS D'ETAT AEB")
    print(SEP)
    for i, (s1, s2) in enumerate(aeb.history):
        print(f"  [{i+1}] {s1.name:<18} -> {s2.name}")

    print(f"\n{SEP}")
    print("  MATRICE DE RISQUE SECURITAIRE")
    print(SEP)
    rows = [
        ("TP  (Succes Nominal)", "AEB active correctement",             "FAIBLE",   "Pipeline normal"),
        ("FP  (Faux Positif)  ", "Freinage non justifie",               "MODERE",   "Desactivation si repete, log"),
        ("FN  (Faux Negatif)  ", "Obstacle non detecte -> collision",   "CRITIQUE", "Escalade radar/lidar obligatoire"),
        ("MC  (Mauvaise Class)", "Profil risque errone",                 "ELEVE",    "Profil conservateur par defaut"),
    ]
    for t, effet, risque, mitigation in rows:
        print(f"\n  {t}")
        print(f"    Effet      : {effet}")
        print(f"    Risque     : {risque}")
        print(f"    Mitigation : {mitigation}")
    print(f"\n{SEP}\n")


if __name__ == "__main__":
    run_aeb_demo()
