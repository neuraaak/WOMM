# Backlog consolidé — WOMM

> Rapport rafraîchi le **2026-10-25**, branche `optimisations-and-refactoring`,
> commit `f4c3789` (la branche la plus avancée — `main` n'a que les bumps
> Dependabot). Repère vérifié par mesure : **982 tests passés + 1 skip**.
> **Source de vérité :** `~/.agents/memory/projects/e-dev-python-works-on-my-machine/current-backlog.md`.
> La numérotation est figée — elle est référencée ailleurs, notamment le
> « lot 4.4 ».

---

## ⚠️ Priorité 0 — travail perdu à reprendre

Une session antérieure a noté les **Tasks 5 à 8 du chantier
`generic-project-setup`** comme livrées et approuvées (commits `45e14ba`,
`2d51de7`, « 995 tests »). Vérifié le 2026-10-25 : ces commits n'existent dans
**aucune branche** de ce dépôt, `resolve_setup_profile` / `SetupProfileResolver`
sont absents de `src/` et de `tests/`, et toutes les cases de
`.superpowers/plans/2026-08-07-generic-project-setup.md` sont décochées.

Ce travail a été fait sur une copie du dépôt sur un volume `G:` aujourd'hui
démonté. **Le considérer comme perdu et repartir de la Task 1.** Si le volume
ressort un jour, arbitrer les deux versions — ne pas supposer laquelle gagne.

**Housekeeping immédiat :** `uv.lock` est modifié et non commité (relock par un
`uv` plus récent, `revision = 3 → 5`, plus des bumps `backrefs 8.0→8.1`,
`pastel` → `inversion`/`tzdata`). Aucune dépendance déclarée n'a changé.
Committer en `chore(deps)` ou jeter, mais ne pas le laisser polluer le prochain
diff.

---

## Priorité 2 — rework `create` / `template`

**Décision du 2026-08-02.** Le scaffolding est un sujet à part : un projet
généré peut légitimement proposer un outillage que WOMM n'utilise pas pour
lui-même. Ne rien corriger au coup par coup d'ici là.

### 2.1 Setup générique — décision **prise**, implémentation à refaire

L'arbitrage qui bloquait la tâche 6 est **tranché en faveur de l'option 1** :
`setup_project` devient générique, piloté par des métadonnées `_womm.setup`
déclarées dans les `copier.yml`, au lieu d'un enum fixe. Spec et plan existent
(dans `.superpowers/`, **gitignoré** — non récupérables par git) :

- `.superpowers/specs/2026-08-07-generic-project-setup-design.md`
- `.superpowers/plans/2026-08-07-generic-project-setup.md`

État du blocage dans le code au 2026-10-25, **inchangé** :

- `SUPPORTED_PROJECT_TYPES = ["python", "javascript", "react", "vue"]` dans
  `shared/configs/project/project_config.py:104`, répliqué dans
  `services/project/validation_service.py:272`. *(La duplication autrefois
  signalée dans `utils/project/validation_utils.py` n'existe plus — ce fichier
  ne référence plus la liste.)*
- Conséquence : `womm create django … --setup` rendrait le projet puis
  échouerait au setup en « Unsupported project type ». Masqué aujourd'hui
  parce que les tests mockent entièrement `setup_project`, donc
  l'incompatibilité n'est jamais exercée en intégration.
- `ProjectManagerInterface.get_available_project_types()`
  (`interfaces/project/manager_interface.py:84`) s'appuie encore sur
  `ProjectConfig.get_project_types_for_ui()` plutôt que sur le catalogue de
  templates — même seam, à unifier dans le même geste.

**Débloque, une fois fait :** la suppression de `src/womm/assets/languages/`
(seul appelant : `utils/project/asset_utils.py` → `setup_interface.py:472`,
flux `--setup`), et avec elle les derniers fichiers encore câblés sur
black / isort / flake8 / mypy :

- `assets/languages/python/{py,django}/scripts/lint.py` et l'arborescence
  `assets/languages/` en général ;
- `ui/project/create/create_completion_summaries.py` et
  `ui/project/setup/setup_completion_summaries.py` (commandes suggérées par le
  chemin `setup_project` legacy).

### 2.2 Catalogue — volontairement à 2 entrées

2 templates officiels (`python`, `javascript`), et **c'est la cible** :
`django` est un champ `framework` du template python, `react`/`vue` et
`typescript` sont des champs du template javascript. Les 8 entrées de catalogue
du plan initial ont été abandonnées (décision D3/D5 de la migration Copier).
Ne pas rouvrir sans demande explicite.

### 2.3 Dette annexe, candidate au nettoyage du même lot

- `ConflictResolutionService`
  (`services/project/conflict_resolution_service.py`) n'a plus aucun appelant
  en production depuis le 2026-08-02 ; il n'est plus référencé que par les
  `__init__.py` de `services/` et son propre test.
  `destination_guard.py` porte seul le contrat `--force`.
- Code mort résiduel dans `shared/configs/project/` (`JavaScriptProjectConfig`,
  `VariantUIConfig`, `variant_detection_utils`) — reliquat de la table de
  mapping que D5 visait à éliminer. Encore consommé uniquement par les listes
  `SUPPORTED_VARIANTS` / `VARIANT_TO_ASSETS` / `DEFAULT_VARIANTS` du flux
  `--setup`, donc à supprimer **après** 2.1, en cascade.

---

## Priorité 3 — reliquats non-bloquants des chantiers templates

Identifiés lors des revues finales, hors périmètre de leur chantier d'origine.
Aucun n'a d'effet observé aujourd'hui.

- **`--setup` perd l'info de variante** (framework / typescript) choisie via
  les réponses Copier de `create` : il applique toujours la config VS Code JS
  plate. À traiter avec 2.1, qui touche le même chemin.
- **`_exclude` du template JS écrase** silencieusement la liste d'exclusion par
  défaut de Copier (latent).
- **Pre-commit JS et CI JS** : `husky` / `lint-staged` absents, et `with_ci`
  n'existe pas côté javascript alors qu'il existe côté python. Reporté
  explicitement par l'utilisateur (« on verra plus tard »).

---

## Priorité 4 — lot final distribution et release

> Différé par décision : à traiter ensemble après le chantier précédent.
> Ce lot est bloquant avant la prochaine release publique.

### 4.1 Dispatcher `install.ps1`

- publier un script PowerShell pinné sur un tag, jamais sur `main` ;
- déléguer vers `uv tool` si disponible ;
- avec Python 3.13+, installer `uv` puis déléguer ;
- ne jamais écrire lui-même dans le PATH ni dans `~/.womm` ;
- documenter le hash du script et garder `uv tool install` comme voie
  principale.

### 4.2 CI de validation et packaging

`.github/workflows/` contient `auto-tag`, `docs`, `publish-pypi` et `release` —
**aucun workflow ne lance les tests ni les linters.** C'est le trou le plus
large du lot.

- ajouter un workflow PR/push qui appelle simplement **`uv run poe check`**
  (séquence déjà définie dans `[tool.poe.tasks]` depuis `ffccb2b` :
  format-check → lint → types → imports → test) — ne pas réécrire la liste
  d'outils dans le YAML, elle divergerait ;
- ajouter `poe security` (bandit) à la porte ou au workflow — c'est aujourd'hui
  le seul consommateur de la dépendance dev `bandit`, invisible au `grep` du
  code applicatif ;
- construire la wheel et faire une installation réelle `uv tool` sous Windows
  et Linux, suivie de `womm doctor` ;
- faire dépendre publication et release de cette porte de qualité.

### 4.3 Canal standalone et Inno Setup

- inventorier d'abord ce que `ezcompiler` couvre déjà ;
- compiler depuis `womm.cli:main`, vérifier la présence des assets ;
- installer sous `%LocalAppData%\Programs\WOMM` avec PATH utilisateur et
  désinstallation propre, sans toucher `~/.womm` ;
- démarrer la mise à jour par `womm update --check`, puis exiger une
  vérification cryptographique avant téléchargement ou exécution d'un
  installeur.

### 4.4 Documentation finale

**Constat, revérifié le 2026-10-25.** Le code ne propose plus `womm install`,
`womm uninstall`, `womm lint`, `womm spell`, `womm git-hooks` ni `womm new`,
mais la doc les documente encore. Le README conserve aussi les badges
« Python 3.10+ » et « Tests TODO » alors que le projet demande Python 3.13+ et
a une suite réelle de 982 tests.

**À faire**, une fois les canaux d'installation stabilisés :

- **`womm new <language>` (commande inexistante)** encore référencée dans
  6 fichiers : `docs/index.md`, `docs/getting-started.md`,
  `docs/examples/index.md`, `docs/guides/environment.md`,
  `docs/diagrams/new.md` et `README.md` ;
- **nav morte dans `mkdocs.yml`** pour des verticales supprimées :
  `Install: cli/install.md` (l.77), `Lint: cli/lint.md` (l.80),
  `Spell: cli/spell.md` (l.81), `Git Hooks: cli/git-hooks.md` (l.84),
  `Install Flow: diagrams/install.md` (l.91), `Lint Flow: diagrams/lint.md`
  (l.93) — supprimer les entrées **et** les pages ;
- **retirer toute la documentation `lint`** (décision du 2026-08-02 : ce
  nettoyage rentre ici, pas dans un chantier autonome) — supprimer
  `docs/cli/lint.md` et `docs/diagrams/lint.md`, puis les mentions dans
  `docs/cli/commands.md`, `docs/index.md`, `docs/getting-started.md`,
  `docs/guides/configuration.md`, `docs/guides/index.md`,
  `docs/examples/index.md` et `README.md` ;
- **mettre à jour la doc `deps`** : le modèle est passé de 3 à 2 strates
  (`5f0492e`), toute la doc décrit encore les 3 ;
- **`docs/api/index.md` décrit une architecture périmée** : il pointe encore
  `womm/core/managers/…`, `womm/core/utils/…` (l.65, l.102, l.196), chemins
  disparus depuis le passage au src-layout `commands`/`interfaces`/`services` ;
- documenter `womm doctor` et les sous-groupes `path` / `context backup`, dont
  `path add <dir>` / `path remove <dir>` et `path backup restore [name]` ;
- présenter le canal réellement retenu et `uv tool` comme voie principale ;
- aligner la documentation de `--force` sur une fusion explicite, sans promesse
  d'écrasement global ;
- corriger les badges et la version Python minimale.

**Critère de sortie.** Aucune documentation utilisateur ne suggère une commande
inexistante ou une sémantique d'écrasement incorrecte.

**Critère de sortie du lot.** Les trois canaux (développement, `uv tool`,
standalone Windows) appellent le même point d'entrée, préservent les données
utilisateur et sont vérifiés par la CI avant publication.

---

## Ordre de reprise recommandé

1. Committer ou jeter `uv.lock` (5 min, débloque la lisibilité des diffs).
2. Reprendre `generic-project-setup` depuis la Task 1 — c'est le goulot : il
   débloque `--setup`, `assets/languages/`, le code mort de
   `shared/configs/project/` et la perte de variante de la priorité 3.
3. Terminer en un lot release : CI (4.2) d'abord — elle est indépendante du
   reste et protège tout ce qui suit —, puis `install.ps1`, standalone/Inno et
   la documentation.
