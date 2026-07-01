# AUDIT DES CALCULS — Dashboard nacalculatie AWP Buro

> Document de référence : pour chaque chiffre, graphe et champ de la popup, quelle est la **donnée
> Teamleader**, la **méthode de calcul**, l'**objectif**, et les **axes d'amélioration**.
> Recoupé avec le code : `nacalc/sync.py` (`_compute`), `nacalc/calc.py`, `nacalc/views.py`,
> `nacalc/templates.py`. (Version : 2026-06-30.)

## 0. Principe général
**Flux :** Teamleader (`projects-v2`) → **sync** (calcul) → **cache SQLite** (1 snapshot/projet) →
**affichage**. La sync tourne 1×/heure + bouton « Sync nu ». Les pages lisent **uniquement le cache**
(aucun appel Teamleader au chargement d'une page).

**Règle clé sur les sources :**
- **Par fase** = montants **€** (`external_budget_spent / external_budget` du groupe Teamleader).
- **Niveau projet** (heures, coût, marge) = **timeTracking** (heures réelles) + l'**offerte**.
- ⚠️ Teamleader **ne fournit pas d'heures par fase**, seulement le **€ par fase**. C'est la limite centrale.
- Seuls les projets en statut **`open`** sont synchronisés.

## 1. Données récupérées de Teamleader
| Source (API projects-v2) | Champs utilisés | Sert à |
|---|---|---|
| `projects.list` + `projects.info` | `title`, `status`, `custom_fields`, `price`/`calculated_price`, `time_estimated`, `time_tracked`, `quotations[]` | identité, offerte, heures budget, custom fields |
| `projectGroups.list` (filter project_id) | par fase : `title`, `external_budget`, `external_budget_spent` | **% + couleur par fase** |
| `timeTracking.list` (`relates_to` nextgenProject) | `duration`, `user`, `work_type` | **heures réelles, coût, compteurs** |
| `quotations.info` | `grouped_lines` (sections + hoeveelheden) | heures budget par fase (peu/plus utilisé) |
| `customFieldDefinitions.list` | label → id | mapper les custom fields |
| `workTypes.list` | name → id | compteurs Werfbezoek / Bespreking klant |

**Custom fields projet utilisés :** `Budget BH` → budget klant · `Raming AWP` → raming voorontwerp ·
`2. Type` · `3. Categorie` · `Contracttype` · `4. Werfadres` → adres · `1. Verantw.` → verantwoordelijke ·
`Architectuur`.

## 2. Briques de calcul (réutilisées partout)
| # | Brique | Formule exacte | Données | ⚠️ Limite |
|---|---|---|---|---|
| **B1** | **% par fase** | `round(external_budget_spent / external_budget × 100, 1)` si budget>0, sinon `None` (= niet voorzien) | projectGroups | % du **budget devis €** consommé, pas des heures |
| **B2** | **Couleur fase** (statut budget) | `None`→geen ; `≥115`→donkerrood ; `>100`→rood ; `≥80`→oranje ; sinon groen | B1 + seuils | seuils configurables (Beheer ; défaut 80/100/115) |
| **B3** | **Glyphe fase** (avancement) | budget=0 → niet voorzien ; spent=0 → niet gestart ; gestart **et** une fase ultérieure démarrée → afgewerkt ; sinon in uitvoering | groups | « afgewerkt » est **déduit** du démarrage d'une fase suivante, pas d'une vraie clôture |
| **B4** | **Statut projet** | parmi les fases **« actives »** (gestart **et** budget>0) : la couleur la plus sévère → `over` (rood/donkerrood) / `warn` (oranje) / `ok` (groen) ; aucune active → `none` (« Nog niet gestart ») | B1-B2 | **ignore les heures loggées** (cf §5 #1) |
| **B5** | **Heures projet** | gepresteerd = `Σ duration(timeTracking) / 3600` ; begroot = `project.time_estimated` | timeTracking + project | begroot **souvent 0** (pas de tijdsbudget in TL) |
| **B6** | **Coût effectif** | `gepresteerde uren × €65` (tarif interne) | B5 + config | tarif **fixe pour tous** |
| **B7** | **Marge** | `offerte − kost` si offerte>0, sinon `None` (« — ») ; `marge_pct = marge / offerte` | offerte + B6 | offerte **souvent 0** → marge « — » |
| **B8** | **Compteurs werfbezoek / bespreking** | nb d'entrées timeTracking avec `work_type` = « Werfbezoek » / « Bespreking klant » | timeTracking | **non dédupliqué** (2 pers. = 2) ; pas comparé à l'offerte |
| **B9** | **Filtre architectuur** | inclus si `2. Type` ∉ {stedenbouw, epb, epc, epc/epb, wegenis} | custom field Type | inclut tout projet **sans type** explicitement non-arch |

---

## 3. ⭐ LA POPUP DE DÉTAIL (`/app/project/<id>`) — chaque champ + son calcul
*(C'est la fenêtre qui s'ouvre au clic sur un projet — le screenshot A082. Rendue par `templates.render_drawer`.)*

### En-tête
| Élément | Donnée / calcul | Objectif |
|---|---|---|
| **Titre** « A082 · Weststraat Waarschoot » | `project_key` (= `title` avant « - ») · `naam` (= `title` après « - », sinon Werfadres) | identifier le projet |
| **Sous-titre** « adres · verantw » | custom field `4. Werfadres` · `1. Verantw.` | localisation + responsable |
| **Tags** (Nieuwbouw · —) | `3. Categorie` · `Contracttype` | classification |
| **Pastille statut** (Not started / Op koers / Dreigt over / Over budget) | **B4** | état budgétaire global du projet |

### Grille des 6 cases
| Case | Donnée / calcul exact | Objectif |
|---|---|---|
| **Budget klant** | `parse_money(custom field « Budget BH »)` | budget annoncé par le client |
| **Raming voorontwerp** | `parse_money(custom field « Raming AWP »)` | estimation propre d'AWP (avant-projet) |
| **Offerte AWP** | `project.price` (sinon `calculated_price`) | montant offert / facturable |
| **Hours tracked / budgeted** | **B5** : `Σ timeTracking.duration / 3600` **/** `project.time_estimated` | heures réelles prestées vs budget heures |
| **Effective office cost** | **B6** : `uren gepresteerd × €65` | ce que le bureau a réellement dépensé (interne) |
| **Margin (quote − cost)** | **B7** : `offerte − kost` (ou « — » si pas d'offerte) `· marge_pct` | rentabilité du projet |

### Bloc « Progress per phase » (une ligne par groupe Teamleader)
| Élément de la ligne | Donnée / calcul | Objectif |
|---|---|---|
| **Nom de la fase** | `projectGroup.title` (ex. « 1. ADMINISTRATIE ») | la fase concernée |
| **Étiquette** (afgewerkt / lopend / dreigt over / over budget / fors over / niet gestart / niet voorzien) | dérivée de **B3** (avancement) + **B2** (couleur) | état de la fase |
| **Barre** | largeur = `min(B1, 100)` (pleine si ≥100%), couleur = **B2** | jauge de consommation du budget de la fase |
| **Texte** « € spent / € budget verbruikt · % » | `external_budget_spent` / `external_budget` du groupe `· B1` | **montant €** consommé du devis de la fase |
| **Note de bas de bloc** | texte fixe : « par fase = indicatif, basé sur le budget devis en € ; totaux & marge = heures réelles » | honnêteté sur la limite (pas d'heures par fase) |

### Bloc « Werfbezoeken & besprekingen »
| Élément | Calcul | Objectif |
|---|---|---|
| **Werfbezoeken** / **Klantbesprekingen** | **B8** (compte d'entrées timeTracking par work_type) | suivi des visites de chantier / réunions client |

---

## 4. Le reste du dashboard

### 4.1 Projectoverzicht (`/app`)
**KPI :** Lopende projecten = `len(snapshots)` · Over budget = nb `summary_status=="over"` (B4) ·
Dreigt over budget = nb `=="warn"` · Totale marge (lopend) = `Σ marge` (B7, **exclut** les projets sans offerte).
**Colonnes du tableau :** Status (**B4**) · Project (n° + naam + adres) · Verantwoordelijke · Categorie ·
Contract · Budget klant · Offerte AWP · **Uren** (B5, barre `min(gepr/begroot, 100)`) ·
**Fases** (stippen : couleur **B2** + forme **B3**) · **Marge** (B7, pastille verte/rouge ou « — »).

### 4.2 Meldingen (`/app/meldingen`)
Pour chaque projet, chaque fase **gestart** dont la couleur ∈ {oranje, rood, donkerrood} génère une
melding (sévérité = couleur, % = B1). **Objectif :** liste d'actions (fases ≥80% ou en dépassement).
⚠️ Le badge se base sur `seen`, remis à 0 à chaque sync (les alertes « réapparaissent » après une sync).

### 4.3 Analyse (`/app/analyse`) — 4 graphes
*(Tous calculés sur les snapshots architectuur. Chaque graphe a une infobulle ⓘ sur le titre + une infobulle par barre.)*

**① Gemiddeld budgetverbruik per fase** — fases regroupées par **nom de base** (sans « 1. / 2. … ») ;
par fase = **moyenne de B1** sur toutes les occurrences **gestart**. Barre = `min(%, 100)` (pleine ≥100%),
vert <80 / oranje 80-99 / **rood ≥100**. Trié du plus consommé au moins.
*Objectif :* quelles fases dérapent systématiquement. *Exclut :* fases non gestart, sans budget, projets non-arch.

**② Rendabiliteit per contracttype** — moyenne de `marge_pct` (B7) par contracttype, sur les projets
**avec offerte**. Barre = ampleur de la marge. *Objectif :* quels contrats sont rentables.
*Exclut :* sans contracttype, sans offerte.

**③ Overschrijding per categorie** — par categorie, `nb projets over budget / total × 100`.
*Objectif :* quels types dépassent le plus. *Exclut :* projets sans categorie.

**④ Projecten met klantbudget — status** — ≤12 projets avec `budget_klant`, drapeau over/op-koers.
*Objectif visé :* raming klant vs eigen raming. ⚠️ **Ne compare pas réellement** (`Raming AWP` quasi
vide) → montre juste le statut.

---

## 5. Axes d'amélioration (priorisés)
1. **🔴 Statut « Not started » alors qu'il y a des heures loggées (ex. A082).** B4 se base sur la
   consommation € par fase et **ignore les heures réelles** : un projet avec 32,8 h + €2.132 de coût mais
   0 € consommé par fase affiche « Nog niet gestart ». *À décider :* le statut doit-il suivre les
   **heures** ou la **consommation € du devis** ? (ex. « Bezig (uren geregistreerd) » si heures>0.)
2. **🟠 Offerte = 0** → marge « — » sur beaucoup de projets. Encoder les offertes dans Teamleader, ou
   fallback marge vs budget client.
3. **🟠 Heures budget = 0** (pas de tijdsbudget in TL) → « X / 0u ». Dériver de l'offerte (÷ €90) ou
   remplir le tijdsbudget dans TL.
4. **🟡 Pas d'heures par fase** (limite Teamleader) — la progression par fase est en €, pas en heures
   (déjà signalé par une note + infobulle).
5. **🟡 Noms de fases non standardisés** — fragmentation. Analyse : regroupé par nom ; overzicht/detail :
   tels quels. Piste : templates de fases standardisés dans TL.
6. **🟡 Graphe 4 (raming)** ne compare pas réellement — remplir `Raming AWP`, sinon retravailler/retirer.
7. **🟡 Coût interne fixe €65 pour tous** — la table `cost_rates` (par personne, avec historique) existe
   déjà mais n'est pas utilisée ; possibilité de revenir au coût par personne.
8. **⚪ Compteurs visites non dédupliqués** ; pas de comparaison au nombre prévu dans l'offerte.
9. **⚪ Calculs « morts »** : `tracked_hours` / `budget_hours` par fase et `calc.project_totals()` ne sont
   plus affichés (l'overzicht/detail utilisent les totaux projet) → à nettoyer.
10. **⚪ Seuls les projets `open`** sont synchronisés ; l'analyse « afgeronde projecten » (fase 2 de la
    spec) nécessitera aussi les projets clôturés.
