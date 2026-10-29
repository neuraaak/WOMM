# Backlog consolidé — WOMM

> État vérifié le **2026-10-29** sur `optimisations-and-refactoring`.
> Vue actionnable de la mémoire du projet :
> `~/.agents/memory/projects/e-dev-python-womm/current-backlog.md`.
> La numérotation des lots est conservée pour les références existantes ;
> les sections terminées ont été retirées.

---

## Priorité 3 — finaliser la migration ezplog 2.x

La première passe a supprimé `EzplBridge`, adopté les API publiques
d'ezplog 2.x et isolé l'accès temporaire à la console Rich dans
`WommPrinter.console`. Le sous-lot 3.1 est clos le 2026-10-29
(−1117 lignes) ; il ne reste que l'attente amont et les deux décisions
de compatibilité ci-dessous.

- [ ] Supprimer `WommPrinter.console` lorsque ezplog exposera un accesseur
  public équivalent. **Bloqué en amont** : vérifié sur ezplog 2.3.3, aucun
  accesseur public de console n'existe encore, et l'adaptateur a 18
  appelants de production.

**Critère de sortie du lot :** l'intégration ne duplique aucune capacité
publique d'ezplog 2.x et n'accède à ses attributs privés qu'au travers du
seul adaptateur temporaire documenté.

### 3.1 Nettoyages confirmés par l'audit

Les sept nettoyages sont clos le 2026-10-29 (détail dans la mémoire du
projet), ainsi que leur seul effet de bord : `setup_development_environment`
a été supprimée des deux interfaces, le flux de la commande `setup` passant
par `setup_project`. Vérification : 914 tests + 1 skip, couverture 70,97 %
(seuil `test-ci` à 60 %), Ruff, Ruff format, Ty, import-linter et
`mkdocs build --strict` verts.

### 3.2 Décisions de compatibilité et exclusions

- [x] Supprimer `--log-level`, `--log-file` et `--log-json` comme rupture CLI
  explicite : ces options étaient acceptées sans appliquer le réglage demandé.
  Elles sont désormais rejetées par Click ; annoncer leur retrait dans les
  notes de la prochaine version.
- [x] Conserver `ContextConfig` : la façade est utilisée par quatre modules de
  production (`services/context/parameters.py`, `registry_service.py`,
  `validation_service.py` et `utils/context/core_utils.py`) et réduit leur
  couplage aux configurations spécialisées. Ses exports publics et les valeurs
  partagées avec ces configurations sont couverts par un test. Toute suppression
  future exige une migration des consommateurs et une décision sur la
  compatibilité de l'export public.

**Critère de sortie du sous-lot :** chaque suppression est justifiée par un
inventaire des appelants, les contrats publics conservés disposent d'un test,
`uv.lock` est synchronisé et les portes Ruff, Ty, import-linter, pytest et
MkDocs sont vertes.

---

## Priorité 4 — distribution, release et documentation

> Lot différé jusqu'à stabilisation du comportement métier. Les workflows
> `00` à `04` et la matrice de tests Ubuntu/Windows existent déjà ; valider
> leur état sur le commit destiné à la release avant toute publication.

### 4.1 Dispatcher `install.ps1`

- [ ] Publier un script PowerShell épinglé à un tag, jamais à `main`.
- [ ] Déléguer à `uv tool` lorsqu'il est présent ; avec Python 3.13+,
  installer `uv` puis déléguer.
- [ ] Ne pas écrire directement dans le PATH ni dans `~/.womm` ;
  documenter le hash du script et garder `uv tool install` comme voie
  principale.

### 4.3 Canal standalone et Inno Setup

Le modèle de référence retenu est `flash-excel` : compilation avec
`ezcompiler`, wrappers de publication et signature hors CI. L'adaptation à
WOMM reste à concevoir ; aucun script de build standalone n'est présent
actuellement dans `.scripts/build/`.

- [ ] Compiler l'entrée commune de WOMM et vérifier que les assets sont
  inclus dans l'exécutable.
- [ ] Installer sous `%LocalAppData%\Programs\WOMM`, avec PATH utilisateur
  et désinstallation propre, sans toucher aux données `~/.womm`.
- [ ] Ajouter un contrôle de mise à jour et vérifier cryptographiquement
  tout artefact téléchargé avant son exécution.

### 4.4 Documentation produit finale

Le reset documentaire a supprimé les anciennes pages obsolètes. Les pages
produit restent à reconstruire après stabilisation des commandes et des
canaux d'installation.

- [ ] Refaire le README : remplacer `womm new` et `womm lint`, corriger
  le badge Python 3.10+ et les exemples d'outillage généré.
- [ ] Documenter `womm doctor`, `path add/remove`,
  `path backup restore [name]` et `context backup`.
- [ ] Présenter les canaux d'installation réellement retenus, avec
  `uv tool` comme voie principale.
- [ ] Décrire `--force` comme une fusion explicite, sans promettre
  d'écrasement global.
- [ ] Vérifier qu'aucune documentation utilisateur ne suggère une commande
  inexistante ou une sémantique incorrecte.

**Critère de sortie du lot :** les canaux développement, `uv tool` et
standalone appellent la même entrée, préservent les données utilisateur et
sont vérifiés avant publication.

---

## Ordre de reprise recommandé

1. Reconstruire la documentation produit — la migration ezplog 2.x est
   bloquée en amont et ne tient plus la file.
2. Finaliser le renommage PyPI en `womm-cli`, `install.ps1` et le canal
   standalone, puis valider la chaîne CI/release complète.
3. Reprendre la suppression de `WommPrinter.console` dès qu'ezplog expose un
   accesseur public.
