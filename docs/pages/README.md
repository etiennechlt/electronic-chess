# Pages d'explication

Les trois textes de vulgarisation du projet, en pages autonomes : un
seul fichier chacune, schémas embarqués, lisible hors du dépôt et
envoyable telle quelle.

| Page | Le même texte en note | Ce qu'elle explique |
|---|---|---|
| [facteur-q.html](facteur-q.html) | [note 18](../notes/18-facteur-q.md) | le facteur Q sans électronique préalable, avec les chiffres réels du projet |
| [cerveau-banc.html](cerveau-banc.html) | [note 19](../notes/19-cerveau-et-banc-nucleo.md) | ce que fait la carte cerveau, et le banc Nucleo qui va confronter le calcul à la mesure |
| [tuto-banc.html](tuto-banc.html) | [note 20](../notes/20-tuto-banc.md) | quoi commander, comment assembler, comment tester, du dépôt à la première mesure |

Elles sont générées, jamais écrites à la main :

```bash
PYTHONPATH=tools python3 -m docfig pages
```

Mêmes fonctions et même `config/board.yaml` que les figures de
`docs/images` et que les notes : un chiffre du projet ne peut donc pas
diverger entre une note et sa page. `tests/test_docfig.py` vérifie
qu'aucun gabarit ne reste dans une page, qu'aucun chemin absolu ne s'y
glisse et que les douze notes du plan de fréquences y sont.
