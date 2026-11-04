"""Reglages du joueur appliques au jeu en cours (son, texte, defilement, vitesse)."""
import time
from dq4_pc.persistance import reglages as RG
from dq4_pc.fenetre.constantes import SE_APERCU, SE_BOUTON


class OptionsMixin:
    """Reglages du joueur appliques au jeu en cours (son, texte, defilement, vitesse)."""

    def regler_son(self, oui):
        if bool(oui) != self.son.actif:
            self.son.basculer()
            if self.son.actif and self.moteur.etat.musique is not None: self.son.jouer_bgm(self.moteur.etat.musique)

    def regler_vol_musique(self, v): self.son.regler_volumes(v, None)

    def regler_vol_bruitages(self, v): self.son.regler_volumes(None, v)

    # ---- son par categorie (menu Echap > Son) : voir son.py (CATEGORIES, Mixage)
    def appliquer_mixage(self, depart=False):
        """Volumes et interrupteurs des reglages -> son.mix, tout de suite pour les sons en cours. Au depart, les volumes de la musique et des bruitages sont ceux de la ligne de commande (Son les a deja)."""
        R = self.reg; vol = dict(jingles=R['volume_jingles'], interface=R['volume_interface'])
        if not depart: vol.update(musique=R['volume_musique'], effets=R['volume_bruitages'])
        self.son.regler_mixage(general=R['volume_general'], volumes=vol, actifs=dict(musique=R['musique_active'], jingles=R['jingles_actifs'], effets=R['bruitages_actifs'], interface=R['interface_active']))

    def apercu_son(self, cat):
        """Reglage d'un volume sur la page Son : un bruitage d'essai de la categorie (un par quart de seconde au plus) ; la musique, elle, se fait entendre pendant la page (Son.ecouter)."""
        t = time.time()
        if t - self._t_apercu < 0.25: return
        self._t_apercu = t
        if cat in ('general', 'effets') and self.son.mix.gain('effets') > 0.0: self.son.jouer_se(SE_APERCU)
        elif cat in ('general', 'interface'): self.son.jouer_se(SE_BOUTON)

    # ---- vitesse du texte des dialogues et defilement des messages de combat (menu Echap > Commandes > Defilement du texte)
    def appliquer_texte(self): self.moteur.vitesse_texte = float(self.reg['vitesse_texte'])

    def appliquer_jeu(self):
        """Page « Modifications » du menu Echap (ex-« Jeu ») : options qui changent une regle du jeu (PV et PM restaures au niveau superieur)."""
        self.moteur.soin_niveau = bool(self.reg['soin_niveau'])

    def appliquer_defilement(self):
        """« Vitesse de combat » -> OptionStatus.battleSpeed impose au moteur : 4 (messages a la main) en Manuel, 0 (attente la plus courte du jeu, 12 images) sinon (RG.code_defilement) ; Rapide et Tres rapide accelerent l'horloge, donc aussi l'attente."""
        self.moteur.imposer_defilement(RG.code_defilement(self.reg['vitesse_combat']))

    def _adopter_defilement(self, code):
        """Le jeu change lui-meme la vitesse des messages (fenetre Parametres d'origine) : 4 -> Manuel, toute autre valeur -> sortie du Manuel (RG.vitesse_apres_code_jeu)."""
        self.reg['vitesse_combat'] = RG.vitesse_apres_code_jeu(code, self.reg['vitesse_combat'])
        self.appliquer_defilement()
