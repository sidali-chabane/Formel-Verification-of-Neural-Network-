"""
Vérification Formelle du réseau YOLO - Dataset KITTI
Catégories: Faux Négatif (FN), Faux Positif (FP), Mauvaise Classification, Succès Nominal (TP)
"""

import os
import cv2
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ─── Configuration ────────────────────────────────────────────────────────────
MODEL_PATH   = "best.pt"
IMAGES_DIR   = "kitti/images/val"
LABELS_DIR   = "kitti/labels/val"   # labels YOLO format (optionnel)
OUTPUT_DIR   = "verification_results"
IOU_THRESHOLD   = 0.5    # seuil IoU pour matcher une détection à un GT
CONF_THRESHOLD  = 0.25   # seuil de confiance modèle

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

# Couleurs par type de résultat (BGR pour OpenCV)
COLORS = {
    "TP":              (0, 255, 0),    # Vert   - Succès nominal
    "FP":              (0, 0, 255),    # Rouge  - Faux positif
    "FN":              (0, 165, 255),  # Orange - Faux négatif
    "MISCLASSIF":      (255, 0, 255),  # Magenta - Mauvaise classification
    "GT":              (255, 255, 0),  # Cyan   - Ground truth
}

# ─── Utilitaires IoU ─────────────────────────────────────────────────────────

def compute_iou(box_a, box_b):
    """Calcule IoU entre deux boîtes [x1, y1, x2, y2]."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def yolo_to_xyxy(cx, cy, w, h, img_w, img_h):
    """Convertit format YOLO normalisé → [x1, y1, x2, y2] pixels."""
    x1 = (cx - w / 2) * img_w
    y1 = (cy - h / 2) * img_h
    x2 = (cx + w / 2) * img_w
    y2 = (cy + h / 2) * img_h
    return [x1, y1, x2, y2]


# ─── Chargement des labels Ground Truth ──────────────────────────────────────

def load_gt_labels(label_path, img_w, img_h):
    """Charge les annotations YOLO depuis un fichier .txt → liste de dicts."""
    gts = []
    if not os.path.exists(label_path):
        return gts
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls_id = int(parts[0])
            cx, cy, w, h = map(float, parts[1:5])
            box = yolo_to_xyxy(cx, cy, w, h, img_w, img_h)
            gts.append({"class": cls_id, "box": box, "matched": False})
    return gts


# ─── Classification d'une image ──────────────────────────────────────────────

def classify_detections(preds, gts):
    """
    Compare prédictions vs ground truth et retourne:
    - pour chaque prédiction: "TP", "FP", ou "MISCLASSIF"
    - pour chaque GT non matché: "FN"
    """
    results = []
    gt_matched = [False] * len(gts)

    for pred in preds:
        pred_box   = pred["box"]
        pred_class = pred["class"]
        best_iou   = 0.0
        best_idx   = -1

        for i, gt in enumerate(gts):
            iou = compute_iou(pred_box, gt["box"])
            if iou > best_iou:
                best_iou = iou
                best_idx = i

        if best_iou >= IOU_THRESHOLD and best_idx >= 0:
            if not gt_matched[best_idx]:
                gt_matched[best_idx] = True
                if pred_class == gts[best_idx]["class"]:
                    results.append({**pred, "type": "TP", "gt_class": gts[best_idx]["class"]})
                else:
                    results.append({**pred, "type": "MISCLASSIF", "gt_class": gts[best_idx]["class"]})
            else:
                # GT déjà assigné → doublon = FP
                results.append({**pred, "type": "FP", "gt_class": None})
        else:
            results.append({**pred, "type": "FP", "gt_class": None})

    # GTs non matchés → FN
    fn_list = []
    for i, gt in enumerate(gts):
        if not gt_matched[i]:
            fn_list.append({"class": gt["class"], "box": gt["box"], "type": "FN"})

    return results, fn_list


# ─── Visualisation ───────────────────────────────────────────────────────────

def draw_results(img, detections, fn_list, has_gt):
    """Dessine les boîtes annotées sur l'image."""
    vis = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX

    for det in detections:
        x1, y1, x2, y2 = map(int, det["box"])
        color = COLORS[det["type"]]
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

        label = f"{det['type']}: {CLASSES.get(det['class'], det['class'])}"
        if "conf" in det:
            label += f" ({det['conf']:.2f})"
        if det["type"] == "MISCLASSIF" and det.get("gt_class") is not None:
            label += f" → GT:{CLASSES.get(det['gt_class'])}"

        cv2.putText(vis, label, (x1, max(y1 - 5, 15)), font, 0.45, color, 1, cv2.LINE_AA)

    for fn in fn_list:
        x1, y1, x2, y2 = map(int, fn["box"])
        color = COLORS["FN"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        label = f"FN: {CLASSES.get(fn['class'], fn['class'])}"
        cv2.putText(vis, label, (x1, max(y1 - 5, 15)), font, 0.45, color, 1, cv2.LINE_AA)

    return vis


# ─── Rapport global ──────────────────────────────────────────────────────────

def compute_metrics(counters):
    """Calcule précision, rappel, F1 par classe."""
    metrics = {}
    for cls_id in range(len(CLASSES)):
        tp = counters["TP"][cls_id]
        fp = counters["FP"][cls_id]
        fn = counters["FN"][cls_id]
        mc = counters["MISCLASSIF"][cls_id]
        prec = tp / (tp + fp + mc) if (tp + fp + mc) > 0 else 0.0
        rec  = tp / (tp + fn + mc) if (tp + fn + mc) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        metrics[cls_id] = {"precision": prec, "recall": rec, "f1": f1,
                           "TP": tp, "FP": fp, "FN": fn, "MISCLASSIF": mc}
    return metrics


def save_bar_chart(metrics, output_path):
    cls_names = [CLASSES[i] for i in range(len(CLASSES))]
    tp  = [metrics[i]["TP"]         for i in range(len(CLASSES))]
    fp  = [metrics[i]["FP"]         for i in range(len(CLASSES))]
    fn  = [metrics[i]["FN"]         for i in range(len(CLASSES))]
    mc  = [metrics[i]["MISCLASSIF"] for i in range(len(CLASSES))]

    x = np.arange(len(cls_names))
    w = 0.2
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - 1.5*w, tp, w, label="TP (Succès Nominal)", color="#2ecc71")
    ax.bar(x - 0.5*w, fp, w, label="FP (Faux Positif)",  color="#e74c3c")
    ax.bar(x + 0.5*w, fn, w, label="FN (Faux Négatif)",  color="#e67e22")
    ax.bar(x + 1.5*w, mc, w, label="Mauvaise Classif.",  color="#9b59b6")
    ax.set_xticks(x)
    ax.set_xticklabels(cls_names, rotation=25)
    ax.set_title("Vérification Formelle - Distribution TP/FP/FN/Misclassification par classe")
    ax.set_ylabel("Nombre de détections")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_metrics_chart(metrics, output_path):
    cls_names = [CLASSES[i] for i in range(len(CLASSES))]
    prec = [metrics[i]["precision"] for i in range(len(CLASSES))]
    rec  = [metrics[i]["recall"]    for i in range(len(CLASSES))]
    f1   = [metrics[i]["f1"]        for i in range(len(CLASSES))]

    x = np.arange(len(cls_names))
    w = 0.25
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - w,  prec, w, label="Précision", color="#3498db")
    ax.bar(x,      rec,  w, label="Rappel",    color="#1abc9c")
    ax.bar(x + w,  f1,   w, label="F1-Score",  color="#f39c12")
    ax.set_xticks(x)
    ax.set_xticklabels(cls_names, rotation=25)
    ax.set_ylim(0, 1.1)
    ax.set_title("Métriques par classe - Précision / Rappel / F1")
    ax.set_ylabel("Score (0-1)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


# ─── Pipeline principal ───────────────────────────────────────────────────────

def run_verification(max_images=200):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vis_dir = os.path.join(OUTPUT_DIR, "visualizations")
    os.makedirs(vis_dir, exist_ok=True)

    model = YOLO(MODEL_PATH)
    image_paths = sorted(Path(IMAGES_DIR).glob("*.png"))[:max_images]

    has_gt = os.path.isdir(LABELS_DIR) and any(Path(LABELS_DIR).glob("*.txt"))
    print(f"{'[MODE GT]' if has_gt else '[MODE SANS GT - analyse confiance]'}")
    print(f"Images à traiter : {len(image_paths)}")

    counters = {
        "TP":        defaultdict(int),
        "FP":        defaultdict(int),
        "FN":        defaultdict(int),
        "MISCLASSIF":defaultdict(int),
    }
    global_counts = {"TP": 0, "FP": 0, "FN": 0, "MISCLASSIF": 0}
    image_results = []

    for idx, img_path in enumerate(image_paths):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        # Inférence YOLO
        results = model.predict(str(img_path), conf=CONF_THRESHOLD, verbose=False)[0]
        preds = []
        for box in results.boxes:
            xyxy   = box.xyxy[0].tolist()
            cls_id = int(box.cls[0].item())
            conf   = float(box.conf[0].item())
            preds.append({"box": xyxy, "class": cls_id, "conf": conf})

        if has_gt:
            label_file = os.path.join(LABELS_DIR, img_path.stem + ".txt")
            gts = load_gt_labels(label_file, w, h)
            detections, fn_list = classify_detections(preds, gts)
        else:
            # Sans GT : confiance ≥ 0.5 → pseudo-TP, sinon FP
            detections = []
            for p in preds:
                t = "TP" if p["conf"] >= 0.5 else "FP"
                detections.append({**p, "type": t, "gt_class": None})
            fn_list = []

        # Comptage
        img_count = {"TP": 0, "FP": 0, "FN": 0, "MISCLASSIF": 0}
        for d in detections:
            counters[d["type"]][d["class"]] += 1
            global_counts[d["type"]] += 1
            img_count[d["type"]] += 1
        for fn in fn_list:
            counters["FN"][fn["class"]] += 1
            global_counts["FN"] += 1
            img_count["FN"] += 1

        image_results.append({
            "image": img_path.name,
            **img_count
        })

        # Sauvegarde image annotée (toutes les 20 images ou si anomalie)
        if idx % 20 == 0 or img_count["FP"] > 0 or img_count["FN"] > 0 or img_count["MISCLASSIF"] > 0:
            vis = draw_results(img, detections, fn_list, has_gt)
            cv2.imwrite(os.path.join(vis_dir, f"annot_{img_path.name}"), vis)

        if (idx + 1) % 50 == 0:
            print(f"  Traité {idx+1}/{len(image_paths)} images...")

    # ── Métriques finales ──────────────────────────────────────────────────
    metrics = compute_metrics(counters)

    total = sum(global_counts.values()) or 1
    print("\n" + "="*65)
    print("  RAPPORT DE VÉRIFICATION FORMELLE - YOLO / KITTI")
    print("="*65)
    print(f"  Images analysées : {len(image_paths)}")
    print(f"  Seuil IoU        : {IOU_THRESHOLD}")
    print(f"  Seuil confiance  : {CONF_THRESHOLD}")
    print(f"  Mode             : {'Avec Ground Truth' if has_gt else 'Sans Ground Truth (confiance)'}")
    print("-"*65)
    print(f"  {'Type':<22} {'Nombre':>8}  {'%':>7}")
    print("-"*65)
    for t, emoji in [("TP","✓"), ("FP","✗"), ("FN","△"), ("MISCLASSIF","≠")]:
        n = global_counts[t]
        print(f"  {emoji} Succès Nominal (TP)" if t=="TP" else
              f"  {emoji} Faux Positif (FP)   " if t=="FP" else
              f"  {emoji} Faux Négatif (FN)   " if t=="FN" else
              f"  {emoji} Mauvaise Classif.   ", end="")
        print(f"{'':>2}{n:>8}  {100*n/total:>6.1f}%")
    print("-"*65)
    print(f"  {'TOTAL':<22} {total:>8}")
    print("="*65)
    print("\n  MÉTRIQUES PAR CLASSE:")
    print(f"  {'Classe':<18} {'Préc.':>7} {'Rappel':>7} {'F1':>7} | {'TP':>5} {'FP':>5} {'FN':>5} {'MC':>5}")
    print("  " + "-"*62)
    for cls_id, m in metrics.items():
        name = CLASSES[cls_id]
        if m["TP"] + m["FP"] + m["FN"] + m["MISCLASSIF"] == 0:
            continue
        print(f"  {name:<18} {m['precision']:>7.3f} {m['recall']:>7.3f} {m['f1']:>7.3f}"
              f" | {m['TP']:>5} {m['FP']:>5} {m['FN']:>5} {m['MISCLASSIF']:>5}")

    # Graphiques
    save_bar_chart(metrics, os.path.join(OUTPUT_DIR, "detection_counts.png"))
    save_metrics_chart(metrics, os.path.join(OUTPUT_DIR, "metrics_by_class.png"))

    # JSON
    report = {
        "config": {"iou_threshold": IOU_THRESHOLD, "conf_threshold": CONF_THRESHOLD,
                   "images_analyzed": len(image_paths), "has_gt": has_gt},
        "global": global_counts,
        "per_class": {CLASSES[i]: metrics[i] for i in range(len(CLASSES))},
        "per_image": image_results,
    }
    with open(os.path.join(OUTPUT_DIR, "verification_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Résultats sauvegardés dans : {OUTPUT_DIR}/")
    print(f"    • detection_counts.png")
    print(f"    • metrics_by_class.png")
    print(f"    • verification_report.json")
    print(f"    • visualizations/  ({len(os.listdir(vis_dir))} images annotées)")
    return report


if __name__ == "__main__":
    run_verification(max_images=9999)   # toutes les images val
