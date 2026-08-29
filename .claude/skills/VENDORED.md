# Skills tiers embarqués dans le projet

Ces skills sont copiés dans le dépôt pour être disponibles dans toute
session de travail, y compris les environnements distants éphémères.
Ne pas les modifier localement : pour mettre à jour, recloner l'amont
et recopier.

| Skills | Origine | Commit | Licence |
|---|---|---|---|
| kicad, spice, emc, datasheets, bom, digikey, mouser, lcsc, element14, jlcpcb, pcbway | https://github.com/aklofas/kicad-happy (v2.2.0) | 43dad23 | MIT, voir LICENSE-kicad-happy |
| parametric-3d-printing | https://github.com/flowful-ai/cad-skill | fe42159 | PolyForm Noncommercial 1.0.0, voir parametric-3d-printing/LICENSE |

Notes :

- Le répertoire docs/ (images d'illustration) et les métadonnées git de
  cad-skill ne sont pas embarqués.
- PolyForm Noncommercial : usage non commercial uniquement. Compatible
  avec ce projet personnel ; à reconsidérer si le projet devenait
  commercial.
- Ces répertoires sont exclus du lint du projet (ruff) : contenu amont,
  conventions amont.
