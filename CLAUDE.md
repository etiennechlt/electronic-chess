# Conventions du projet

Ces règles s'appliquent à toute contribution, humaine ou assistée.

## Langue et typographie

- Code, identifiants, commentaires et messages de log : anglais.
- Documentation, README, ADR et messages de commit : français.
- Aucun tiret cadratin ni demi-cadratin dans les textes rédigés
  (documents, commits, commentaires, réponses). Utiliser virgules,
  deux-points ou parenthèses.

## Attribution

- Ne jamais mentionner une assistance par IA dans les commits, les
  pull requests, les commentaires ou tout artefact du dépôt : pas de
  trailer Co-Authored-By, pas de pied de page « generated with », pas
  d'identifiant de modèle.
- Auteur des commits : etiennechlt <etiennechalot@gmail.com>.
- Branche de travail : `main`. Aucun nom de branche évoquant un outil
  d'assistance ; si l'outillage impose une branche de travail à lui,
  pousser le résultat sur `main` puis supprimer cette branche avant de
  clore la session.

## Source de vérité unique

- Toute valeur numérique du projet vient de `config/board.yaml`.
  Les grandeurs dérivées sont calculées par `chessboard_calc` et
  épinglées par les tests ; ne jamais dupliquer un nombre entre le
  yaml, le code, la doc ou les générateurs.
- Le pas de case `p` (40 ou 50 mm) est ouvert : tout doit rester
  paramétrique sur `p`.

## Méthode de travail

- Avant chaque bloc de code significatif : proposer l'approche et les
  interfaces, attendre l'accord, puis implémenter.
- Livrer des fichiers complets, jamais des extraits à recoller.
- Avant tout push : `ruff check .` puis `pytest`. Le test de couloir
  (`tests/test_corridor.py`) est le garde-fou bloquant de la CI.

## Skills

Les skills KiCad (revue, EMC, SPICE, sourcing, fabrication) et
CadQuery sont embarqués dans `.claude/skills/`, voir
`.claude/skills/VENDORED.md` pour la provenance et les licences.
