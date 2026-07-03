# Vérification de la couche de détection neuronale d'un système AEB

Implémentation et vérification du **composant de détection par réseau de
neurones** d'un système de freinage d'urgence automatique (**AEB**, *Automatic
Emergency Braking*). Ce dépôt accompagne le mémoire *« Vérification formelle du
système AEB par automates ouverts et model checking »* (Chapitre 3, Section 1)
et regroupe le code Python et les résultats de référence.

> Le volet **model checking** du système complet (NuSMV / UPPAAL) fait l'objet
> d'un dépôt distinct.

---

## 1. Idée directrice

Dans le modèle formel du système, le réseau de détection n'est pas représenté
par ses poids, mais par l'**éventail de ses issues sémantiques**. Chaque sortie
du détecteur relève de l'un de quatre régimes :

| Régime | Signification | Domaine |
|--------|---------------|---------|
| **TP** | détection correcte (bonne boîte, bonne classe) | prédiction |
| **MC** | mauvaise classification (bonne boîte, mauvaise classe) | prédiction |
| **FP** | détection fantôme (aucun objet réel) | prédiction |
| **FN** | détection manquée (objet réel non détecté) | objet de référence |

Ce dépôt **justifie et sécurise cette abstraction** de deux manières :

1. une **caractérisation empirique** des quatre régimes sur données réelles, qui
   montre qu'ils existent tous et en quantifie la fréquence ;
2. une **vérification formelle** (solveur SMT **Z3**) de la logique de
   classification et du traitement de la mauvaise classification.

La démarche s'inscrit dans l'esprit de la **SOTIF (ISO 21448)**, qui cible les
défaillances fonctionnelles d'un composant correctement réalisé, et se veut
complémentaire des vérificateurs de réseaux isolés (Reluplex, Marabou).

---

## 2. Contenu du dépôt

```
aeb-neural-verification/
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── src/
│   ├── formal_verification.py     # caractérisation empirique TP/FP/FN/MC (KITTI)
│   ├── z3_formal_verification.py  # preuves SMT (Z3) + robustesse (ONNX)
│   ├── aeb_system.py              # prototype de réaction AEB aux 4 régimes
│   ├── generate_report_pdf.py     # (optionnel) rapport PDF de la caractérisation
│   └── generate_z3_report_pdf.py  # (optionnel) rapport PDF des preuves Z3
└── results/                       # résultats de référence (versionnés)
    ├── verification_report.json   # comptes TP/FP/FN/MC + métriques par classe
    ├── z3_robustness_results.json # robustesse par niveau de perturbation
    ├── detection_counts.png       # distribution des régimes par classe
    ├── metrics_by_class.png       # précision / rappel / F1 par classe
    └── samples/                   # exemples d'images annotées
```

> **Non versionnés** (voir `.gitignore`) : le modèle `best.pt` / `best.onnx`
> (volumineux) et le jeu de données `kitti/`. Voir la section *Données et
> modèle*.

---

## 3. Installation

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate   |   Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Utilisation

> Exécuter les scripts **depuis la racine du dépôt** : ils attendent le modèle
> `best.pt` et le dossier `kitti/` à la racine.

### 4.1 Caractérisation empirique des régimes

```bash
python src/formal_verification.py
```

Parcourt le jeu de validation KITTI, apparie chaque détection au *ground truth*
par IoU (seuil 0,5), classe le résultat en TP / FP / FN / MC, puis produit les
métriques par classe, les graphiques et les images annotées.

### 4.2 Vérification formelle par Z3

```bash
python src/z3_formal_verification.py
```

Prouve **par réfutation** (résultat `UNSAT` de la négation) : la cohérence de la
partition des issues de prédiction {TP, FP, MC}, et la sûreté du profil de
risque conservateur appliqué en cas de mauvaise classification. Le dernier bloc
mesure la robustesse locale du réseau exporté en ONNX.

### 4.3 Prototype de réaction AEB

```bash
python src/aeb_system.py
```

Illustre, pour chacun des quatre régimes, la réaction du système (freinage
nominal, freinage fantôme inhibé, escalade radar sur détection manquée, profil
conservateur sur mauvaise classification).

---

## 5. Résultats de référence

### Distribution des régimes (YOLOv8 / KITTI, 1 496 images de validation)

| Régime | Effectif | Proportion |
|--------|---------:|-----------:|
| TP — détection correcte | 7 582 | 83,8 % |
| FP — détection fantôme | 915 | 10,1 % |
| FN — détection manquée | 507 | 5,6 % |
| MC — mauvaise classification | 39 | 0,4 % |

Précision globale **88,8 %**, rappel **93,3 %**, score F1 **91,0 %**. Les trois
modes de défaillance sont tous présents, ce qui justifie la décomposition en
quatre régimes. Point sensible pour la sûreté : la classe **piéton** présente le
rappel le plus faible (0,805 → 174 piétons manqués).

### Vérification formelle (Z3)

- **Partition des prédictions {TP, FP, MC}** : exclusivité mutuelle, complétude
  et déterminisme — **prouvés** (`UNSAT`, < 10 ms chacun). FN est traité
  séparément, sur le domaine des objets de référence.
- **Profil conservateur** : le niveau de risque n'est **jamais** sous-estimé en
  cas de mauvaise classification (`r* ≥ r_réel`), et le piéton est toujours
  traité au risque maximal — **prouvé pour les 64 paires de classes**.

### Robustesse locale (perturbations bornées ℓ∞, ONNX — analyse exploratoire)

| ε (/255) | Stabilité top-1 |
|---------:|----------------:|
| 1  | 100,0 % |
| 5  | 80,0 %  |
| 10 | 57,8 %  |

---

## 6. Données et modèle

Non versionnés (taille) :

- **KITTI** (détection 2D) : à télécharger sur le
  [site KITTI](https://www.cvlib.net/datasets/kitti/), converti au format YOLO
  et rangé en `kitti/images/{train,val}` et `kitti/labels/{train,val}`.
- **Modèle `best.pt`** (YOLOv8n entraîné sur KITTI) : à publier via Git LFS ou en
  *release* GitHub. L'export ONNX est produit automatiquement au premier appel du
  bloc de robustesse.

---

## 7. Outils

`ultralytics 8.4.60` · `z3-solver 4.16.0` · `onnx 1.21.0` ·
`onnxruntime 1.26.0` · `opencv-python`.

## Licence

Distribué sous licence MIT — voir [`LICENSE`](LICENSE).
