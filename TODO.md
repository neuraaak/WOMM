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

### 4.3 Déploiement de la documentation

Le site publié date du 2026-10-25 et décrit encore `works-on-my-machine` :
`04-docs.yml` ne fait que **construire** la doc, et les Pages sont servies
depuis la branche `gh-pages` que rien ne met à jour. Le README et la page PyPI
pointent dessus.

- [ ] Ajouter au workflow `04-docs` le job de déploiement du modèle de
  référence (`ezcompiler` déploie avec `mike`, `contents: write`, selon le
  `tag_action`), ou déployer une première fois à la main.

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

### 4.5 Publication PyPI et notes de version

> **Nommage arrêté le 2026-10-29 :** le projet reste `womm` partout — dépôt,
> paquet importable, commande, données `~/.womm`. Seul le nom de
> distribution est `womm-cli`, parce que `womm` est pris sur PyPI ; il
> n'apparaît qu'à l'installation et à la mise à jour via uv ou pip. L'écart
> est assumé, non bloquant. `[project] name`, l'URL `PyPI`, le badge du
> README et `uv.lock` sont alignés.

`womm-cli` 4.0.0 est publié depuis le 2026-10-29 par le Trusted Publisher,
sans jeton. Piège rencontré : PyPI compare le nom de dépôt **à la casse près**,
`womm` ne correspond pas à `WOMM`.

**Critère de sortie du lot :** les canaux développement et `uv tool`
appellent la même entrée, préservent les données utilisateur et sont
vérifiés avant publication.

---

## Ordre de reprise recommandé

1. Reconstruire la documentation produit — la migration ezplog 2.x est
   bloquée en amont et ne tient plus la file.
2. Finaliser le renommage PyPI en `womm-cli`, puis valider la chaîne
   CI/release complète.
3. Reprendre la suppression de `WommPrinter.console` dès qu'ezplog expose un
   accesseur public.
