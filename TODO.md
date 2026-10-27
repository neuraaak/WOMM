# Backlog consolidé — WOMM

> État vérifié le **2026-10-27** sur `optimisations-and-refactoring`.
> Vue actionnable de la mémoire du projet :
> `~/.agents/memory/projects/e-dev-python-womm/current-backlog.md`.
> La numérotation des lots est conservée pour les références existantes ;
> les sections terminées ont été retirées.

---

## Priorité 3 — finaliser la migration ezplog 2.x

La première passe a supprimé `EzplBridge`, adopté les API publiques
d'ezplog 2.x et isolé l'accès temporaire à la console Rich dans
`WommPrinter.console`. L'audit Ponytail du 2026-10-27, contrôlé par une
revue architecture, qualité et configuration, confirme le nettoyage de la
surface morte mais invalide la suppression globale de `test_logging.py` :
plusieurs helpers qui y sont testés restent appelés en production.

- [ ] Supprimer `WommPrinter.console` lorsque ezplog exposera un accesseur
  public équivalent.

**Critère de sortie du lot :** l'intégration ne duplique aucune capacité
publique d'ezplog 2.x et n'accède à ses attributs privés qu'au travers du
seul adaptateur temporaire documenté. Le diff final doit établir le nombre
réel de lignes supprimées ; l'estimation préliminaire de 1 500 lignes n'est
pas retenue comme objectif.

### 3.1 Nettoyages confirmés par l'audit

- [ ] Supprimer `tests/run_tests.py`, redondant avec pytest et les tâches Poe
  `test`, `test-ci`, `test-fast` et `test-parallel` ; vérifier auparavant
  qu'aucun usage externe documenté ne subsiste.
- [ ] Supprimer les assertions factices des suites `unit`, `integration` et
  `robustness`, puis retirer les fixtures devenues orphelines.
- [ ] Déplacer le contrôle de l'export public `womm.__version__` dans un test
  d'API ou de CLI avant de supprimer `test_dummy_unit.py`.
- [ ] Retirer `install_command`, `search_command` et `list_command` de la
  configuration des gestionnaires de paquets système : aucun consommateur ne
  les lit et WOMM ne porte plus la responsabilité de l'installation.
- [ ] Remplacer les trois relais
  `SystemDetectorConfig.get_*_package_managers()` par les accesseurs nommés
  de `PackageManagerConfig`, sans répandre les littéraux de plateforme dans
  les consommateurs.
- [ ] Supprimer les dépendances inutilisées `build`, `mkdocstrings`,
  `mkdocs-coverage` et `mike` de `pyproject.toml` et
  `requirements-dev.in`, puis régénérer `uv.lock` et valider la CI et le
  build documentaire.
- [ ] Supprimer de `ProjectManagerInterface` les seules méthodes sans appelant
  de production (`setup_development_environment` et
  `get_available_project_types`) après vérification de l'API publique ;
  conserver la façade utilisée par la commande `setup`.

### 3.2 Décisions de compatibilité et exclusions

- [ ] Décider explicitement du sort de `--log-level`, `--log-file` et
  `--log-json` : les implémenter, les déprécier avant retrait, ou annoncer
  leur suppression comme rupture CLI. Ne pas les traiter comme un simple
  nettoyage interne.
- [ ] Conserver `ContextConfig` : la façade est utilisée par quatre modules de
  production et réduit actuellement leur couplage aux configurations
  spécialisées. Toute suppression future exige une migration des
  consommateurs et une décision sur la compatibilité de l'export public.

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

1. Finaliser la migration ezplog 2.x.
2. Reconstruire la documentation produit.
3. Finaliser le renommage PyPI en `womm-cli`, `install.ps1` et le canal
   standalone, puis valider la chaîne CI/release complète.
