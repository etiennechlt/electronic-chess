# Skills tiers embarqués dans le projet

Ces skills sont copiés dans le dépôt pour être disponibles dans toute
session de travail, y compris les environnements distants éphémères.
Ne pas les modifier localement : pour mettre à jour, recloner l'amont
et recopier.

| Skills | Origine | Commit | Licence |
|---|---|---|---|
| kicad, spice, emc, datasheets, bom, digikey, mouser, lcsc, element14, jlcpcb, pcbway | https://github.com/aklofas/kicad-happy (v2.2.1) | d5fd7da | MIT, voir LICENSE-kicad-happy |
| release-pcba-fabrication, operate-jlcpcb-order, pcb-layout-review | https://github.com/Keitark/pcba-design-skills (rangés sous `.agents/skills/` en amont) | d41e999 | MIT, voir LICENSE-pcba-design-skills |
| parametric-3d-printing | https://github.com/flowful-ai/cad-skill | fe42159 | PolyForm Noncommercial 1.0.0, voir parametric-3d-printing/LICENSE |

Notes :

- Le répertoire docs/ (images d'illustration) et les métadonnées git de
  cad-skill ne sont pas embarqués.
- PolyForm Noncommercial : usage non commercial uniquement. Compatible
  avec ce projet personnel ; à reconsidérer si le projet devenait
  commercial.
- Ces répertoires sont exclus du lint du projet (ruff) : contenu amont,
  conventions amont.
- Les cinq autres skills de pcba-design-skills (gestion de programme, brief produit, qualification d'approvisionnement, humanisation de schéma) ne sont pas embarqués : doublons du skill `bom` ou de la note 07, ou à contre-emploi sur des schémas générés.
