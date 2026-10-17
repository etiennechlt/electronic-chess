# Serveur KiCad MCP

Le serveur [KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server)
(MIT) donne à l'assistant de session 244 outils sur KiCad : ouvrir une
carte ou un schéma, lire et modifier composants, pistes, zones et
règles, lancer le DRC, exporter gerbers, BOM et rendus, chercher les
symboles et empreintes des bibliothèques, interroger le catalogue de
pièces JLCPCB. Il complète les générateurs du dépôt (`tools/*gen`),
qui restent la source des cartes : le serveur sert à inspecter, relire
et retoucher une carte générée, pas à la dessiner à la main.

## Installation

Le serveur n'est pas embarqué dans le dépôt (plusieurs centaines de
mégaoctets une fois construit). Le script le clone, le construit et le
déclare :

```bash
sudo apt-get install -y kicad kicad-symbols kicad-footprints   # KiCad 7.0.11 convient
tools/mcp/install-kicad-mcp.sh          # clone stable dans .mcp/, npm install, build, pip
tools/mcp/install-kicad-mcp.sh --check  # vérifie pcbnew, node et le build
```

`.mcp.json` à la racine déclare le serveur `kicad`, lancé par
`tools/mcp/kicad-mcp.sh` (qui expose le Python de KiCad au serveur).
Au démarrage suivant de la session, `/mcp` montre le serveur connecté.
Le dossier `.mcp/` est ignoré par git ; `KICAD_MCP_REF=main` installe la
branche de développement plutôt que `stable`.

## Vérifié dans ce dépôt

Le 17/10/2026, avec KiCad 7.0.11 (paquets Ubuntu 24.04) et Node 22 :
le serveur démarre, valide `pcbnew`, liste ses 244 outils, et
`open_board` ouvre `hardware/bench/bench.kicad_pcb`. Son README vise
KiCad 9 ou plus ; les outils qui passent par l'API IPC (interface en
direct) ne fonctionnent pas sur KiCad 7, ceux qui passent par `pcbnew`
(ouverture, lecture, DRC, exports) oui.

## Ce qu'il ne remplace pas

- `tools/drc.py`, `tools/gerbers.py`, `tools/plot.py` : les mêmes
  opérations, scriptées et reproductibles, utilisées par la CI et les
  tests ; le serveur les double en interactif.
- Les générateurs : une carte retouchée par le serveur diverge de sa
  source. Pour une correction durable, modifier le générateur ou le
  yaml et regénérer (note 08).
- Le catalogue JLCPCB du serveur (`download_jlcpcb_database`) télécharge
  une base de 1 Go depuis GitHub Pages : utile sur un poste avec accès
  réseau, inutile dans un environnement distant filtré.
