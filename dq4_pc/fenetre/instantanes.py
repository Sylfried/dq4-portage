"""Etats instantanes (sauvegarde / chargement a n'importe quel moment)."""
import os
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc import chemins as CH
from dq4_pc.noyau import moteur as MO
from dq4_pc.persistance import etats as ET


class InstantanesMixin:
    """Etats instantanes (sauvegarde / chargement a n'importe quel moment)."""

    @staticmethod
    def _num_etat(symbol):
        K = pyglet.window.key
        chiffres = {K._1: 1, K._2: 2, K._3: 3, K._4: 4, K._5: 5, K._6: 6, K._7: 7, K._8: 8, K._9: 9,
                    K.NUM_1: 1, K.NUM_2: 2, K.NUM_3: 3, K.NUM_4: 4, K.NUM_5: 5, K.NUM_6: 6, K.NUM_7: 7, K.NUM_8: 8, K.NUM_9: 9}
        return chiffres.get(symbol)

    # ---- etats instantanes (savestates)
    def chemin_etat(self, n): return os.path.join(CH.DOSSIERS.dossier_etats(self.args.saves_ecriture), 'etat_%02d.dqs' % n)

    def infos_etat(self, n):
        """(infos, miniature PNG) de l'etat n, ou None."""
        return ET.infos(self.chemin_etat(n))

    def _lieu(self):
        e = self.moteur.etat
        if e.partie == MO.PARTIE_CASINO: return 'Casino : poker' if e.carte == 'ev04' else ('Casino : machine à sous' if e.carte == 'ev05' else 'Casino')          # (cartes ev04 / ev05 : voir Global::setMinigame)
        if e.partie == MO.PARTIE_BESTIAIRE: return 'Bestiaire'
        return 'Carte du monde' if e.partie == MO.PARTIE_CHAMP else ('Combat' if e.partie == MO.PARTIE_COMBAT else (e.carte or '?'))

    def _etat_complet(self):
        """Etat instantane du moteur + de la visionneuse (objets animes de la carte compris)."""
        viewer = {'objets_etat': self.objets.etat if self.objets is not None else None, 'objets_auto': self.objets.auto if self.objets is not None else None,
                  'palettes': self.palettes.etat() if self.palettes is not None else None, 'carte_nom': self.carte_nom, 'motif_n': self.motif_n, 'motif_acc': self.motif_acc.copy(), 'musique': self.son.etat_bgm()}
        return ET.instantane(self.moteur, viewer)

    def sauver_etat(self, n, miniature_png=b''):
        """Enregistre l'etat du jeu dans l'emplacement n."""
        d = self._etat_complet()
        ET.ecrire(self.chemin_etat(n), d, {'lieu': self._lieu(), 'carte': self.moteur.etat.carte, 'partie': self.moteur.etat.partie, 'images': self.moteur.images}, miniature_png)

    def charger_etat(self, n):
        """Recharge l'emplacement n ; l'etat d'avant le chargement est gardé en memoire (annuler_chargement)."""
        d = ET.lire(self.chemin_etat(n))
        try: self.etat_annul = self._etat_complet()
        except Exception as ex: self.etat_annul = None; print('etat avant chargement non garde :', ex, flush=True)
        self._appliquer_etat(d)

    def annuler_chargement(self):
        """Revient a l'etat juste avant le dernier chargement (un deuxieme appel refait le chargement)."""
        if self.etat_annul is None: self.toast('Aucun chargement à annuler'); return False
        actuel = self._etat_complet(); d, self.etat_annul = self.etat_annul, actuel
        self._appliquer_etat(d); self.toast('Chargement annulé')
        return True

    def _appliquer_etat(self, d):
        """Remet le moteur dans l'etat `d`, puis tout ce que la fenetre en a deduit (fenetres de menu, carte, objets animes, musique)."""
        mo = self.moteur
        viewer = ET.appliquer(mo, d)
        self.ui_g_reset()
        self.carte_nom = None; self.champ_cle = None; self.prec = None; self.canevas_cle = None; self.msg_cle = None
        self.pad_prec = 0; self.rep = {}; self.menu_relacher = None; self.survol = None; self.appui = None; self.survol_nd = None; self.cur_local = {}; self.cur_pas = {}; self.effet_ref = None; self.effet_tex_prete = False
        self.acc = 0.0; self.t_boucle = None; self.effet_ancre = {}
        self.n_combat = 0 if mo.etat.partie != MO.PARTIE_COMBAT else self.n_combat
        e = mo.etat
        if e.carte and e.partie != MO.PARTIE_CHAMP and not e.carte.startswith('btl_'):
            self._charger_carte(e.carte)
        elif e.carte and e.partie == MO.PARTIE_COMBAT: self._charger_carte(e.carte)
        if viewer and 'motif_acc' in viewer: self.motif_n = viewer['motif_n']; self.motif_acc[:] = viewer['motif_acc']; self.champ_acc_vu = None          # eau animee de la carte du monde
        if viewer and viewer.get('objets_etat') and self.objets is not None:
            self.objets.reinit(); self.objets.restaurer(viewer['objets_etat'], viewer.get('objets_auto'))
            for tex, vl, key in self.carte_vl:
                vl.position[:] = self.objets.cur[key].ravel(); vl.tex_coords[:] = self.objets.uv(key).ravel(); vl.colors[:] = self.objets.col(key).ravel()
            self.objets.sale = set(); self.objets.sale_uv = set(); self.objets.sale_col = set()
        if viewer and viewer.get('palettes') and self.palettes is not None: self.palettes.regler(viewer['palettes'])
        for sp in list(e.sprites.values()): self._feuille(sp['id'] - 4096 if (e.partie == MO.PARTIE_CHAMP and sp['id'] >= 4096) else sp['id'], self.mode)
        self.son.restaurer_bgm(viewer.get('musique') if viewer else None, e.musique)         # la musique repart du moment enregistre
        e.sons = []

    def _copier_miniature(self):
        """Copie l'image du jeu (sans le menu) dans une texture, sur la carte graphique seulement : le menu s'ouvre sans attendre une relecture ; le PNG n'est fait qu'a l'enregistrement d'un etat."""
        try:
            w, h = self.get_framebuffer_size()
            t = pyglet.image.Texture.create(w, h, internalformat=gl.GL_RGBA8)
            gl.glBindTexture(t.target, t.id); gl.glCopyTexSubImage2D(t.target, 0, 0, 0, 0, 0, w, h)
            return t
        except Exception as ex:
            print('miniature impossible :', ex, flush=True); return None

    def _png_miniature(self, t):
        """Texture de _copier_miniature -> PNG reduit (miniature des etats)."""
        if t is None: return b''
        try:
            import io
            from PIL import Image
            img = t.get_image_data()
            a = np.frombuffer(img.get_data('RGB', img.width * 3), np.uint8).reshape(img.height, img.width, 3)[::-1]
            im = Image.fromarray(np.ascontiguousarray(a)); im.thumbnail((320, 180)); b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()
        except Exception as ex:
            print('miniature impossible :', ex, flush=True); return b''
