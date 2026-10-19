# Pages d'explication

Les textes de vulgarisation du projet, en pages autonomes : un
seul fichier chacune, schémas embarqués, lisible hors du dépôt et
envoyable telle quelle.

| Page | Le même texte en note | Ce qu'elle explique |
|---|---|---|
| [facteur-q.html](facteur-q.html) | [note 18](../notes/18-facteur-q.md) | le facteur Q sans électronique préalable, avec les chiffres réels du projet |
| [cerveau-banc.html](cerveau-banc.html) | [note 19](../notes/19-cerveau-et-banc-nucleo.md) | ce que fait la carte cerveau, et le banc Nucleo qui va confronter le calcul à la mesure |
| [tuto-banc.html](tuto-banc.html) | [note 20](../notes/20-tuto-banc.md) | quoi commander, comment assembler, comment tester, du dépôt à la première mesure |
| [hall-rfid.html](hall-rfid.html) | [note 24](../notes/24-hall-et-rfid.md) | l'alternative Hall + RFID en trois lectures (simplifiée, technique, implémentation), avec les courbes de champ et le verdict du multiplexeur |
| [demonstrateur-lc.html](demonstrateur-lc.html) | [note 26](../notes/26-demonstrateur-lc.md) | le démonstrateur A, détection LC par oscillations : nature et rôle des composants, commande, assemblage, tests |
| [demonstrateur-hall-rfid.html](demonstrateur-hall-rfid.html) | [note 27](../notes/27-demonstrateur-hall-rfid.md) | le démonstrateur B, effet Hall et RFID : la carte à deux cases, la planche d'étiquettes, commande, assemblage, tests |
| [couts-demonstrateurs.html](couts-demonstrateurs.html) | [fiche de coûts](../couts-demonstrateurs.md) | ce que coûte chaque démonstrateur par catégorie, tout acheter ou souder soi-même |
| [bom-demonstrateur-a.html](bom-demonstrateur-a.html), [bom-demonstrateur-b.html](bom-demonstrateur-b.html) | [nomenclature A](../bom-demonstrateur-a.md), [nomenclature B](../bom-demonstrateur-b.md) | les composants ligne à ligne avec liens et prix LCSC et Mouser |

Elles sont générées, jamais écrites à la main :

```bash
PYTHONPATH=tools python3 -m docfig pages
```

Les quatre premières sont des jumelles écrites à côté de leur note,
avec les mêmes fonctions et le même `config/board.yaml` que les figures
de `docs/images` : un chiffre du projet ne peut donc pas diverger entre
une note et sa page. Les suivantes sont rendues depuis le document
lui-même (`docfig.page_note`) : même texte, figures SVG incorporées,
rendus des cartes embarqués, liens vers les autres pages ou vers le
dépôt sur GitHub. `tests/test_docfig.py` vérifie
qu'aucun gabarit ne reste dans une page, qu'aucun chemin absolu ne s'y
glisse et que les douze notes du plan de fréquences y sont.
