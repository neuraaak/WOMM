# Backlog consolidé — WOMM

> État vérifié le **2026-10-25** sur `optimisations-and-refactoring`.
> Vue actionnable de la mémoire du projet :
> `~/.agents/memory/projects/e-dev-python-womm/current-backlog.md`.
> La numérotation des lots est conservée pour les références existantes ;
> les sections terminées ont été retirées.

---

## Priorité 2 — terminer le rework `create` / `template`

### 2.1 Setup générique — tâches 10 et 11 restantes

Les tâches 1 à 8 sont intégrées à la branche. `setup_project` est piloté par
`_womm.setup` dans les templates Copier ; la liste figée des types de projet
a été supprimée. Le plan et sa spécification sont disponibles dans
`.superpowers/` (gitignoré) :

- `.superpowers/plans/2026-08-07-generic-project-setup.md`
- `.superpowers/specs/2026-08-07-generic-project-setup-design.md`

- [ ] **Tâche 10** — confirmer l'absence d'appelant en production de
  `ConflictResolutionService`, puis supprimer ce service, ses réexports et
  son test. Vérifier la suite après la suppression.
- [ ] **Tâche 11** — exécuter tests, Ruff, Ty et import-linter, puis exercer
  manuellement `womm create python <destination> --defaults --setup` et
  `womm setup detect --path <destination>`.

### 2.3 Nettoyage du flux legacy après le setup générique

- [ ] Retirer `src/womm/assets/languages/` et le chemin `copy_asset_type`
  encore utilisé par `setup_interface.py`, après avoir remplacé ce flux par
  les assets issus des templates Copier.
- [ ] Rechercher les consommateurs des anciennes tables de variantes dans
  `shared/configs/project/` et `utils/project/`, puis supprimer le code
  devenu mort en cascade. Garder le contrat `--force` de
  `destination_guard.py` ; il ne dépend pas de
  `ConflictResolutionService`.
- [ ] Vérifier les suggestions affichées à la fin de `create` et `setup` :
  elles doivent correspondre aux commandes et à l'outillage réellement
  générés.

---

## Priorité 3 — reliquats non bloquants des templates

- [ ] Préserver la variante choisie dans les réponses Copier
  (framework/TypeScript) lorsque `create` enchaîne sur `--setup` ;
  actuellement la configuration VS Code JS appliquée reste plate.
- [ ] Vérifier si `_exclude` du template JavaScript masque les exclusions
  par défaut de Copier, puis corriger si nécessaire.
- [ ] Décider séparément du pre-commit et de la CI JavaScript
  (`husky`/`lint-staged`, `with_ci`) ; cette décision avait été reportée.

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

1. Terminer les tâches 10 et 11 du setup générique.
2. Nettoyer le flux legacy et traiter la perte de variante de `--setup`.
3. Reconstruire la documentation produit.
4. Finaliser le renommage PyPI en `womm-cli`, `install.ps1` et le canal
   standalone, puis valider la chaîne CI/release complète.
