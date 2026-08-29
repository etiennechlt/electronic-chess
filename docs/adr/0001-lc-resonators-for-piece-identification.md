# ADR 0001. Identification des pièces par résonateurs LC passifs

Statut : acceptée.

## Contexte

Le plateau doit identifier type et couleur de chaque pièce, y compris
après une disposition manuelle arbitraire, à travers un entrefer
nominal de 5,1 mm, sur 64 cases, et en présence d'un aimant permanent
dans chaque base.

Technologies écartées :

- NFC / RFID 13,56 MHz : la commutation de 64 antennes est ingérable
  (capacité parasite des multiplexeurs à cette fréquence) et un aimant
  permanent dans la même base est rédhibitoire.
- TI LDC1614 : mesure L et Rp à fréquence d'oscillation fixe, ne
  restitue pas la fréquence propre du résonateur, donc ne discrimine
  pas 12 classes de façon fiable.
- Reed switches : détection binaire occupé/vide, conservés uniquement
  comme repli si la chaîne LC échoue.
- Capteur Hall analogique seul : 2 à 4 classes au mieux, conservé comme
  couche de secours possible.

## Décision

Chaque pièce embarque un résonateur LC passif : bobine plate de 45 µH
commune à toutes les classes et condensateur C0G 1 % de la série E12
qui fixe la classe (12 valeurs, 1,5 à 12 nF, soit 217 à 612 kHz). La
case excite en large bande par un front raide puis écoute le ringdown.
La classification est au plus proche voisin sur les 32 fréquences
mesurées en calibration usine et stockées en flash. Aucun trimming,
aucun tri de composants.

## Conséquences

- L'espacement des classes vaut 2,5 largeurs de résonance au pire cas
  dégradé (Q = 30) et 7,1 kHz au pire cumul de tolérances : garde-fou
  chiffré dans `check_separation`, verrouillé en CI.
- La promotion est détectée automatiquement, contrairement aux plateaux
  à reed switches.
- La mesure 2 du protocole (Q avec aimant ferrite posé) valide ou
  invalide la chaîne entière : c'est le pivot à tester en premier.
