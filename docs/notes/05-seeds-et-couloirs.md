# 05. Seeds structurels et couloirs LED : la méthode

Certaines liaisons ne doivent rien au hasard du routeur : rails,
contrôles du mux, sous-système LED. Cette note fixe la méthode qui a
fini par marcher pour les poser, et la topologie LED de la carte
bobines.

## La méthode des seeds (carte analogique)

1. **Répéter hors build.** Avant d'installer un seed, un script de
   répétition reconstruit les pads réels (`_pad_instances`) et mesure
   chaque candidat en géométrie exacte contre tous les pads
   étrangers, les seeds déjà posés, les rails et leurs vias. On itère
   les points de passage jusqu'à des marges d'au moins 0,145 mm
   (0,225 obtenus sur la dernière série).
2. **Garde au build.** `_hand_seeds` revalide tout à chaque
   génération : `T()` (pistes) contre pads étrangers et seeds entre
   eux par couche, `V()` (vias) contre pads et seeds sur les deux
   couches, rails pré-posés inclus. Un changement de placement fait
   échouer le build bruyamment au lieu de chevaucher en silence.
3. **Leçons payées** (à re-vérifier à chaque nouveau seed) :
   - le rayon d'un via (0,3) déborde bien plus que le demi-trait
     (0,125) : vérifier les vias contre les lanes ET les lanes contre
     les vias des rails ;
   - les moignons de sortie d'un passage en face arrière frôlent les
     lanes voisines : compter la sortie, pas seulement le tunnel ;
   - les empilements de terminaux des spirales percent toutes les
     couches et dépassent du cercle r_out : ce sont des obstacles à
     part entière ;
   - un seed qui ferme une liaison peut en déplacer deux : mesurer le
     bilan global sur une génération complète avant d'adopter.

## Les couloirs LED de la carte bobines

Contexte : à p = 50 les quatre spirales remplissent la carte ; le
cuivre libre se réduit aux couloirs entre cercles (bandes de ~10 mm
sur les axes médians, ~4,5 mm en périphérie) et aux coins des cases.
Les couches internes sont vierges hors spirales (les échappées de
bobines n'utilisent que F et B) : c'est la ressource clé.

- **Données (In1)** : la chaîne WS2812 serpente de LED en LED dans les
  couloirs ; chaque saut est décrit par quelques points de passage et
  un coude intelligent qui choisit, entre les deux équerres possibles,
  celle qui maximise la distance aux spirales et aux barillets. Le
  cuivre In1 des spirales culmine à r_out (arcs de liaison), les
  lanes tiennent centre à au moins r_out + 1,1.
- **5V (In2)** : boucle plus croix centrale, seule équipotentielle de
  la couche donc croisements libres avec elle-même ; esquives locales
  des empilements de terminaux (x = 25 et 75 en haut) et plongée sous
  la rangée de pads du joint.
- **Masse (B)** : boucle, épine centrale décalée de la croix 5V, et
  éperons choisis par un petit solveur gardé (droit, en L avec
  balayage du coude, secours In1 avec via vers l'épine pour les
  recoins clôturés par les échappées).
- **LED aux coins opposés** de chaque case, en retrait
  `corner_inset_mm` ; la case 2 est sur la diagonale NE-SO car son
  coin NO tombe sous la rangée du connecteur. L'ordre de chaîne vit
  dans le yaml (`leds.chain_squares`), partagé avec le firmware.
- **Condensateurs** : un 100 nF par LED avec sa propre paire de vias,
  côté et décalage choisis par dégagement mesuré (la première règle
  « vers l'extérieur » posait des condos hors de la carte, la bonne
  est « vers le centre de la case », avec recherche locale).

## Les gardes de la carte bobines

Au build, tout le cuivre LED (pistes et vias, par couche) est vérifié
contre : les cercles de spirales, les terminaux, les barillets du
joint (exemption même-net), les routes d'échappée des bobines, le
bord de carte, et le débordement hors carte. En plus, le test
`test_cross_net_copper_clearance` échantillonne l'écart entre tout
couple de nets sur toute la carte : c'est lui qui a attrapé chaque
conflit résiduel pendant l'intégration.
