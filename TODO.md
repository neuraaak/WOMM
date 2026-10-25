# Backlog consolidé — WOMM

> Rapport rafraîchi le **2026-10-25**, branche `optimisations-and-refactoring`,
> commit `0798a6b` (la branche la plus avancée — `main` n'a que les bumps
> Dependabot et la dépréciation du nom PyPI). Repère mesuré sur `f4c3789` :
> **982 tests passés + 1 skip**.
> **Source de vérité :** `~/.agents/memory/projects/e-dev-python-works-on-my-machine/current-backlog.md`.
> La numérotation est figée — elle est référencée ailleurs, notamment le
> « lot 4.4 ».

---

## ⚠️ Priorité 0a — porte `ty` rouge : bloque tout commit Python

`ty check` sort en échec sur **10 diagnostics pré-existants**, dans 3 fichiers
sans rapport avec les chantiers en cours. Le hook pre-commit `ty` est en
`pass_filenames: false` : il analyse **tout le projet** dès qu'un `.py` est
staged. Conséquence : aucun commit touchant du Python ne passe.

C'est resté invisible parce que les derniers commits de la branche ne
touchaient que des `.md`, du YAML et du TOML — le hook affichait
`Skipped (no files to check)`. Même schéma que le bug `import-linter` corrigé
dans `1ea9757`.

**5 `error[invalid-context-manager]`** dans `ui/common/ezpl_bridge.py`
(l.651, 674, 746, 770, 794) : `with self.wizard.<méthode>(...)` sur des
méthodes de la dépendance `ezplog`. Elles **sont** décorées `@contextmanager`,
mais ty résout leur type annoncé (`Generator[...]`) sans voir le décorateur.
Faux positifs de typage d'une lib externe, pas des bugs runtime.

**5 `warning[redundant-condition]`** : `services/context/parameters.py`
(l.115, 222, 302 — `context_type` toujours vrai, typé `ContextType`) et
`ui/context/wizard.py` (l.105, 391 — `None` toujours faux). Code défensif
mort, réels mais inoffensifs.

**À faire :** un commit `fix(typing)` préliminaire. Décision non prise sur la
méthode (suppressions ciblées vs retrait du code mort vs assouplissement de la
config `ty`) — à trancher avec le user. **Ne pas contourner avec
`--no-verify`.**

---

## ⚠️ Priorité 0b — finir le rapatriement du worktree détaché

> **Rectification du 2026-10-25.** Une version antérieure de cette section
> déclarait ce travail « perdu, repartir de la Task 1 ». C'était faux.

Les **tâches 1 à 8 sur 11** du chantier `generic-project-setup` sont livrées et
revues. Elles n'étaient pas dans la branche : elles vivaient dans le worktree
`.claude/worktrees/generic-project-setup/`, dont le `gitdir` pointe sur
`G:/.root/dev/.python/works_on_my_machine/.git` — **volume démonté**. Toute
commande git y répond `fatal: not a git repository`, d'où l'illusion de perte.

### État au 2026-10-25 : rapatrié, testé, **mis au stash**

```
stash@{0}  rapatriement generic-project-setup tasks 1-8
```

16 fichiers : 13 modifiés + 3 nouveaux. Les 3 nouveaux
(`setup_profile_resolver.py` 128 l., `test_setup_profile_resolver.py` 81 l.,
`test_project_validation_utils.py` 24 l.) sont dans le commit `stash@{0}^3`,
que `git stash show` **n'affiche pas**. Dépiler avec `git stash pop`, jamais
un `pop` partiel : sans le resolver, rien n'importe.

**Validation mesurée après rapatriement :** `pytest` **995 passés + 1 skip**
(+13 sur les 982 de la branche — exactement le chiffre annoncé par la session
d'origine), `ruff format --check`, `ruff check` et `import-linter` verts. Seule
`ty` échoue, sur les 10 diagnostics de la **Priorité 0a**, tous hors des
16 fichiers rapatriés.

### Ce qu'il faut rapatrier, et ce qu'il ne faut surtout pas

Mesure décisive : `git diff f43c24f HEAD -- src tests` est **vide**. La branche
n'a pas touché `src/` ni `tests/` depuis la base du worktree, donc le worktree
y est **strictement en avance** : 3 fichiers en plus, zéro en moins, aucun
conflit possible.

**Hors de `src/` et `tests/`, le worktree est en retard, pas en avance.** Son
`pyproject.toml` ne contient aucun `[tool.poe.tasks]` : il précède la migration
Poe (`ffccb2b`). Diffé contre la branche, il apparaît comme supprimant Poe, le
`Makefile` et `.scripts/dev/*` — ce n'est pas du travail, c'est l'absence de ce
commit. Idem `.pre-commit-config.yaml`, `requirements*.in`,
`.hooks/hooks-usage.md` et `uv.lock`.

→ **Ne reprendre que `src/` et `tests/`.** Prendre le reste annulerait la
migration Poe, la correction du hook `import-linter` et le reset de la doc.

### Reste à faire

1. Régler la Priorité 0a pour que la porte `ty` laisse passer un commit Python.
2. `git stash pop`, puis commit de récupération (un seul commit ; la
   granularité des 8 tâches reste tracée dans
   `.superpowers/sdd/2026-08-07-generic-project-setup/`, qui contient aussi les
   9 diffs `review-<base>..<tip>.diff` de la chaîne `b1eb7bb` → `b751b68` →
   `a377d7f` → `6fc0206` → `3bb64b2` → `62046b5` → `45e14ba` → `2d51de7`).
3. Enchaîner les **tâches 9 à 11**, non commencées.

⚠️ **Ne pas nettoyer `.claude/worktrees/`** avant que le commit de récupération
soit en place : c'est le seul filet si le stash est perdu.

---

## Priorité 2 — rework `create` / `template`

**Décision du 2026-08-02.** Le scaffolding est un sujet à part : un projet
généré peut légitimement proposer un outillage que WOMM n'utilise pas pour
lui-même. Ne rien corriger au coup par coup d'ici là.

### 2.1 Setup générique — décision prise, implémentation **au stash**

L'arbitrage qui bloquait la tâche 6 est **tranché en faveur de l'option 1** :
`setup_project` devient générique, piloté par des métadonnées `_womm.setup`
déclarées dans les `copier.yml`, au lieu d'un enum fixe. Spec et plan existent
(dans `.superpowers/`, **gitignoré** — non récupérables par git) :

- `.superpowers/specs/2026-08-07-generic-project-setup-design.md`
- `.superpowers/plans/2026-08-07-generic-project-setup.md`

L'implémentation existe déjà à 8 tâches sur 11, rapatriée et mise au
`stash@{0}` — voir la **Priorité 0b**. Ce qui suit décrit l'état de la *branche
de dev*, que le commit de récupération doit corriger :

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

> **Modèle retenu le 2026-10-25 : `flash-excel`.** Il répond à la question
> « inventorier ce qu'ezcompiler couvre déjà » : compilation par
> **`ezcompiler`**, pilotée par un `build.py` à la racine, avec des wrappers
> `.cmd` dans `.scripts/build/` (`publish-release.cmd`, `publish-update.cmd`)
> qui chargent le `.env` et forcent le backend de publication. C'est
> **délibérément hors CI** chez lui — son `poe build` est commenté « needs
> signing keys and credentials that are not in the repository », d'où
> l'absence de workflows `03`/`04` dans ce dépôt de référence.
> L'adaptation à WOMM est reportée à ce lot ; `.scripts/build/build_exe.py`
> reste en l'état jusque-là.

- compiler depuis `womm.cli:main`, vérifier la présence des assets ;
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

> **Réglé le 2026-10-25 par le reset de la doc (`0798a6b`)** : la nav morte
> (`lint`, `spell`, `install`, `git-hooks` et leurs diagrammes), les pages
> `womm new`, la doc `lint`, la doc `deps` à 3 strates et le
> `docs/api/index.md` périmé ont tous disparu avec les 31 pages supprimées.
> Il ne reste de ce lot que ce qui est **hors** de `docs/` ou **à écrire**.

- **`README.md` cite encore `womm new`** et conserve les badges
  « Python 3.10+ » et « Tests TODO » — le reset n'a touché que `docs/` ;
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

1. **Débloquer la porte `ty`** (Priorité 0a) : rien de Python ne peut être
   commité tant qu'elle est rouge.
2. **Commiter le rapatriement** (Priorité 0b), aujourd'hui au stash — du
   travail fait, revu et mesuré à 995 tests, que rien ne protège tant qu'il
   n'est pas dans la branche.
3. Finir `generic-project-setup` (tâches 9 à 11) — c'est le goulot : il
   débloque `--setup`, `assets/languages/`, le code mort de
   `shared/configs/project/` et la perte de variante de la priorité 3.
4. Reconstruire la documentation sur le profil Product (`docs/` est vide
   depuis `0798a6b`).
5. Terminer en un lot release : CI (4.2) d'abord — elle est indépendante du
   reste et protège tout ce qui suit —, puis le renommage PyPI en `womm-cli`,
   `install.ps1` et standalone/Inno.
