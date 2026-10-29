# Backlog consolidé — WOMM

> État vérifié le **2026-10-29** sur `optimisations-and-refactoring`.
> Vue actionnable de la mémoire du projet :
> `~/.agents/memory/projects/e-dev-python-womm/current-backlog.md`.
> La numérotation des lots est conservée pour les références existantes ;
> les sections et items terminés ont été retirés.

---

## Priorité 3 — finaliser la migration ezplog 2.x

`EzplBridge` est supprimé, les API publiques d'ezplog 2.x sont adoptées et
l'accès temporaire à la console Rich est isolé dans `WommPrinter.console`.
Il ne reste que l'attente amont.

- [ ] Supprimer `WommPrinter.console` lorsque ezplog exposera un accesseur
  public équivalent. **Bloqué en amont** : vérifié sur ezplog 2.3.3, aucun
  accesseur public de console n'existe encore, et l'adaptateur a 19
  appelants de production.

**Critère de sortie du lot :** l'intégration ne duplique aucune capacité
publique d'ezplog 2.x et n'accède à ses attributs privés qu'au travers du
seul adaptateur temporaire documenté.

---

## Priorité 4 — distribution, release et documentation

> Lot différé jusqu'à stabilisation du comportement métier. Les workflows
> `00` à `04` et la matrice de tests Ubuntu/Windows existent déjà ; valider
> leur état sur le commit destiné à la release avant toute publication.
>
> **Canal arrêté le 2026-10-29 : `uv tool install` ou pip, et rien d'autre.**
> Le canal standalone (Inno Setup) et le dispatcher `install.ps1` sont
> abandonnés : un script maison ne ferait que relayer `uv tool install`,
> tout en créant une surface d'attaque et un jumeau à maintenir pour les
> autres OS. La documentation présente les deux commandes — installer `uv`,
> puis `uv tool install womm-cli`.

### 4.4 Documentation produit finale

Le reset documentaire a supprimé les anciennes pages obsolètes ; `docs/`
ne contient plus qu'un index et le changelog. Les pages produit restent à
reconstruire après stabilisation des commandes.

- [ ] Refaire le README : remplacer `womm new` et `womm lint`, qui
  n'existent pas (les commandes réelles sont `create`, `setup`, `template`,
  `deps`, `path`, `context`, `system` et `doctor`), corriger le badge
  Python 3.10+ en 3.13+ et revoir les exemples d'outillage généré.
- [ ] Documenter `womm doctor`, `path add/remove`,
  `path backup restore [name]` et `context backup`.
- [ ] Décrire `--force` comme une fusion explicite, sans promettre
  d'écrasement global.
- [ ] Vérifier qu'aucune documentation utilisateur ne suggère une commande
  inexistante ou une sémantique incorrecte.

### 4.5 Renommage PyPI et notes de version

- [ ] Renommer le paquet en `womm-cli` : `[project] name`, l'URL `PyPI` et
  les badges du README — celui-ci annonce déjà `womm-cli` alors que
  `pyproject.toml` déclare `WOMM`. L'ordre d'opérations côté PyPI est
  irréversible : consulter la mémoire projet avant d'agir.
- [ ] Enregistrer le Trusted Publisher PyPI pour le dépôt avant la première
  publication.
- [ ] Annoncer dans les notes de version les deux ruptures déjà commitées :
  le retrait de `--log-level`, `--log-file` et `--log-json`, et l'abandon de
  la migration des données de l'ancien auto-installeur (`~/.womm/.logs`,
  `.templates`, `.backup` et `.proof` ne sont plus reprises).

**Critère de sortie du lot :** les canaux développement et `uv tool`
appellent la même entrée, préservent les données utilisateur et sont
vérifiés avant publication.

---

## Priorité 5 — reliquat des templates officiels

- [ ] Échapper la description dans les fichiers rendus côté React et Vue :
  `| tojson` couvre `pyproject.toml` et `package.json`, mais une description
  contenant `{` ou `<` casse encore `App.jsx`, `App.tsx` et `App.vue`.

---

## Ordre de reprise recommandé

1. Reconstruire la documentation produit — la migration ezplog 2.x est
   bloquée en amont et ne tient plus la file.
2. Finaliser le renommage PyPI en `womm-cli`, puis valider la chaîne
   CI/release complète.
3. Reprendre la suppression de `WommPrinter.console` dès qu'ezplog expose un
   accesseur public.
