# Backlog consolidé — WOMM

> État vérifié le **2026-11-25** sur `main` (`6cb0c80`, release 5.1.0).
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
  public équivalent. **Bloqué en amont** : revérifié sur ezplog 2.3.4 le
  2026-11-23, aucun accesseur public de console n'existe encore, et
  l'adaptateur a 19 appelants de production.

**Critère de sortie du lot :** l'intégration ne duplique aucune capacité
publique d'ezplog 2.x et n'accède à ses attributs privés qu'au travers du
seul adaptateur temporaire documenté.

---

## Priorité 4 — distribution, release et documentation

> **Canal arrêté le 2026-10-29 : `uv tool install` ou pip, et rien d'autre.**
> Le canal standalone (Inno Setup) et le dispatcher `install.ps1` sont
> abandonnés : un script maison ne ferait que relayer `uv tool install`,
> tout en créant une surface d'attaque et un jumeau à maintenir pour les
> autres OS.

### 4.5 Publication PyPI

> **Nommage arrêté le 2026-10-29 :** le projet reste `womm` partout — dépôt,
> paquet importable, commande, données `~/.womm`. Seul le nom de
> distribution est `womm-cli`, parce que `womm` est pris sur PyPI.

`womm-cli` 5.1.0 est publié par le Trusted Publisher, sans jeton ; la doc
versionnée (mike) est déployée à chaque release et la racine de `gh-pages`
ne contient plus que ce que mike gère. `works-on-my-machine` 3.2.4 est
publié avec le statut *Inactive*.

- [ ] Archiver `works-on-my-machine` sur PyPI. **Manuel et irréversible** :
  dernière étape, à faire depuis l'interface PyPI.

**Critère de sortie du lot :** l'ancien nom est archivé et ne propose plus
de mise à jour silencieuse.

---

## Priorité 5 — tester les services qui écrivent sur la machine

Couverture mesurée le 2026-11-25 (globale : 71,33 %).

- [ ] `services/system/path_service.py` — **20 %**. Écrit le PATH
  utilisateur : un défaut y fait perdre des données. Priorité de ce lot.
- [ ] `services/context/registry_service.py` — **9 %**. Écrit dans le
  registre Windows (menu contextuel).
- [ ] `services/context/validation_service.py` — **10 %**.

**Critère de sortie du lot :** chaque écriture (PATH, registre) a un test
qui vérifie ce qui est écrit, et un test du chemin d'échec qui vérifie
que rien n'est perdu.

---

## Priorité 6 — corrections qui changent un comportement

- [ ] `ui/context/wizard.py` (l. 105 et l. 394, `FIXME`) :
  `PathValidator.validate()` renvoie `None`, donc le contrôle d'extension
  des scripts n'est jamais appliqué. Le réparer refuse des scripts
  aujourd'hui acceptés : **décision du user**, puis test.
- [ ] Essayer une fois `womm setup python -I` : la question VS Code
  ajoutée en 5.1.0 n'a pas de test automatique.

---

## Décisions assumées, à ne pas rouvrir sans raison

- `--setup` sur un projet pip qui demande un Python plus récent que celui de
  WOMM : pip refuse l'installation avec un message clair, affiché en
  avertissement. Non traité (2026-11-24) ; avec uv, le cas n'existe pas.
- `setup python --setup-git-hooks` lance le `pre-commit` du `.venv` du
  projet : même modèle de confiance que le `pip` du venv. Jugé non bloquant.

---

## Ordre de reprise recommandé

1. Tests de `path_service` (priorité 5) — seul risque de perte de données.
2. Tests du registre `context`, puis la décision sur le `FIXME` du wizard.
3. Archiver `works-on-my-machine` sur PyPI.
4. Reprendre la suppression de `WommPrinter.console` dès qu'ezplog expose un
   accesseur public.
