"""Reglages du joueur appliques au jeu en cours (son, texte, defilement, vitesse)."""
import time
from dq4_pc.persistence import settings as RG
from dq4_pc.window.constants import SFX_PREVIEW, SFX_BUTTON


class OptionsMixin:
    """Reglages du joueur appliques au jeu en cours (son, texte, defilement, vitesse)."""

    def set_sound(self, yes):
        if bool(yes) != self.sound.active:
            self.sound.toggle()
            if self.sound.active and self.engine.state.music is not None: self.sound.play_bgm(self.engine.state.music)

    def set_music_volume(self, v): self.sound.set_volumes(v, None)

    def set_sfx_volume(self, v): self.sound.set_volumes(None, v)

    # ---- son par categorie (menu Echap > Son) : voir sound.py (CATEGORIES, Mixage)
    def apply_mix(self, initial=False):
        """Volumes et interrupteurs des reglages -> son.mix, tout de suite pour les sons en cours. Au depart, les volumes de la musique et des bruitages sont ceux de la ligne de commande (Son les a deja)."""
        R = self.reg; vol = dict(jingles=R['volume_jingles'], interface=R['volume_interface'])
        if not initial: vol.update(musique=R['volume_musique'], effets=R['volume_bruitages'])
        self.sound.set_mix(general=R['volume_general'], volumes=vol, active_flags=dict(musique=R['musique_active'], jingles=R['jingles_actifs'], effets=R['bruitages_actifs'], interface=R['interface_active']))

    def preview_sound(self, category):
        """Reglage d'un volume sur la page Son : un bruitage d'essai de la categorie (un par quart de seconde au plus) ; la musique, elle, se fait entendre pendant la page (Sound.ecouter)."""
        t = time.time()
        if t - self._t_preview < 0.25: return
        self._t_preview = t
        if category in ('general', 'effets') and self.sound.mix.gain('effets') > 0.0: self.sound.play_sfx(SFX_PREVIEW)
        elif category in ('general', 'interface'): self.sound.play_sfx(SFX_BUTTON)

    # ---- vitesse du texte des dialogues et defilement des messages de combat (menu Echap > Commandes > Defilement du texte)
    def apply_text(self): self.engine.text_speed = float(self.reg['vitesse_texte'])

    def apply_game(self):
        """Page « Modifications » du menu Echap (ex-« Jeu ») : options qui changent une regle du jeu (PV et PM restaures au niveau superieur)."""
        self.engine.level_heal = bool(self.reg['soin_niveau'])

    def apply_scroll(self):
        """« Vitesse de combat » -> OptionStatus.battleSpeed impose au moteur : 4 (messages a la main) en Manuel, 0 (attente la plus courte du jeu, 12 images) sinon (RG.scroll_code) ; Rapide et Tres rapide accelerent l'horloge, donc aussi l'attente."""
        self.engine.impose_scroll_mode(RG.scroll_code(self.reg['vitesse_combat']))

    def _adopt_scroll(self, code):
        """Le jeu change lui-meme la vitesse des messages (fenetre Parametres d'origine) : 4 -> Manuel, toute autre valeur -> sortie du Manuel (RG.speed_after_game_code)."""
        self.reg['vitesse_combat'] = RG.speed_after_game_code(code, self.reg['vitesse_combat'])
        self.apply_scroll()
