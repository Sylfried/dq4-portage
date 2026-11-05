"""Ecran « Sauvegardes » du menu de depart (a la place de la case « Sauv. cloud » du jeu mobile) : exporter et importer les fichiers de sauvegarde.

N'existe pas dans le jeu d'origine : fenetre dessinee dans le style des autres menus (cadre noir, plaques et bouton retour du jeu). La logique des fichiers est dans `saves.py`.
Le choix du fichier passe par la boite de dialogue de Windows (tkinter, dans un fil a part : la fenetre du jeu reste vivante) ; sans tkinter, repli sur des dossiers du portage (`saves/export`, `saves/import`)."""
import os
import pyglet
from pyglet import gl
from dq4_pc.persistence import saves as S
from dq4_pc import language as LG
from dq4_pc.language import tr, N_

BORDER = (-215.0, -215.0, 215.0, 215.0)                 # unites d'interface, origine au centre de la colonne de 450 x 800, Y vers le haut
WHITE = (255, 255, 255, 255); HELPTEXT = (170, 170, 170, 255); GRAY = (128, 128, 128, 255); RED = (255, 110, 110, 255); GREEN = (150, 235, 160, 255)
YELLOW = (255, 235, 4)
SFX_BUTTON = 300                                          # bruitage d'appui sur un bouton de menu (comme fenetre.SFX_BUTTON)
TITLE = N_('Sauvegardes')
BUTTONS = (N_('Exporter'), N_('Importer'))                # (dessines par Pause._et, qui les traduit)
BTN_Y, BTN_L, BTN_H, BTN_X = -42.0, 180.0, 50.0, 100.0
BACK_WIDTH, BACK_HEIGHT = 62.0, 52.0
I_BACK = 2
EXPLANATION = (N_("Exporter : enregistre tes journaux (data1 à data5, data9) et tes états instantanés dans un fichier .zip."),
               N_("Importer : lit un .zip de ce genre, ou des fichiers data1.dat, data2.dat… (par exemple copiés depuis un téléphone Android)."),
               N_("Les fichiers remplacés sont d'abord copiés dans le dossier « before_import_… » de tes sauvegardes."))           # (traduits ligne par ligne au dessin : voir dessiner)
FILES = (N_('%d fichier de sauvegarde'), N_('%d fichiers de sauvegarde'))             # (singulier, pluriel) : l'anglais a ses propres modeles
SAVESTATES = (N_('%d état instantané'), N_('%d états instantanés'))


def _pluralize(n, models):
    """« 1 fichier de sauvegarde », « 3 fichiers de sauvegarde » : `models` = (modele du singulier, modele du pluriel). Regle du pluriel de la langue : en francais 0 et 1 sont au singulier (« 0 etat instantane »), en anglais seul 1 l'est (« 0 save states »)."""
    singular = n < 2 if LG.current_language() == 'fr' else n == 1
    return tr(models[0] if singular else models[1]) % n


class SavesScreen:
    def __init__(self, J):
        self.J = J; self.cur = 0; self.zones = []; self.hovered = None; self.dialogue = None; self.action = None; self.msg = []; self.msg_clr = WHITE
        self.needs_reload = False                          # vrai apres un import reussi : la fenetre du jeu relit les journaux

    # ---- logique
    def _folders(self):
        a = self.J.args
        return a.saves_write, a.saves_read

    def export_saves(self):
        if self.dialogue is not None: return
        wdir, _ = self._folders()
        self.action = 'export'; self.dialogue = S.Dialogue('enregistrer', tr('Exporter les sauvegardes'), wdir if os.path.isdir(wdir) else None, S.default_export_name())
        self._say([tr("Choisis où enregistrer le fichier dans la fenêtre qui vient de s'ouvrir…")], HELPTEXT)

    def import_saves(self):
        if self.dialogue is not None: return
        wdir, _ = self._folders()
        self.action = 'import'; self.dialogue = S.Dialogue('ouvrir', tr('Importer des sauvegardes'), None)
        self._say([tr("Choisis le .zip ou les fichiers de sauvegarde dans la fenêtre qui vient de s'ouvrir…")], HELPTEXT)

    def _say(self, lines, clr=WHITE):
        self.msg = list(lines); self.msg_clr = clr

    def do_update(self):
        """Appelee a chaque image : traite la reponse de la boite de dialogue."""
        d = self.dialogue
        if d is None or d.result is None: return
        self.dialogue = None; wdir, rdir = self._folders(); action, self.action = self.action, None
        try:
            if action == 'export':
                if d.unavailable:                                     # pas de boite de dialogue : un dossier du portage
                    path = os.path.join(wdir, 'export', S.default_export_name())
                elif not d.result: self._say([tr('Export annulé.')], HELPTEXT); return
                else: path = d.result[0]
                nj, n_savestates = S.export_saves(wdir, rdir, path)
                self._say([tr('Exporté : %s et %s.') % (_pluralize(nj, FILES), _pluralize(n_savestates, SAVESTATES)), path], GREEN)
            elif action == 'import':
                if d.unavailable:
                    folder = os.path.join(wdir, 'import'); os.makedirs(folder, exist_ok=True)
                    if not any(os.scandir(folder)):
                        try: os.startfile(folder)                      # (Windows) ouvre le dossier dans l'Explorateur
                        except Exception: pass
                        self._say([tr('Pas de boîte de dialogue disponible : dépose tes fichiers (.zip, data1.dat…) dans'), folder, tr('puis clique de nouveau sur Importer.')], RED); return
                    sources = [folder]
                elif not d.result: self._say([tr('Import annulé.')], HELPTEXT); return
                else: sources = d.result
                nj, n_savestates, copied, pb = S.import_saves(sources, wdir, rdir)
                self.needs_reload = True; eng = self.J.engine
                new = eng.reread_savefiles()                         # les listes (Continuer, Reprendre, Supprimer, Auto) affichent aussitot les nouveaux journaux
                lines = [tr('Importé : %s et %s.') % (_pluralize(nj, FILES), _pluralize(n_savestates, SAVESTATES))]
                if copied: lines.append(tr('Anciens fichiers copiés dans : %s') % copied)
                if pb: lines.append(tr('Ignorés : %s') % '; '.join(pb))
                if eng.initial_buttons_state(new) != eng.initial_buttons_state(self.J.initial_status):
                    lines.append(tr('Pour mettre à jour les boutons grisés du menu de départ, relance le jeu.'))
                self._say(lines, GREEN)
        except Exception as ex:
            self._say([tr('Impossible : %s') % (ex,)], RED)

    # ---- entrees
    def press(self, i):
        if i == 0: self.export_saves(); return True
        if i == 1: self.import_saves(); return True
        if i == I_BACK: self.J._close_saves(); return True
        return False

    def key_press(self, symbol, modifiers=0):
        K = pyglet.window.key
        if symbol in (K.ESCAPE, K.BACKSPACE) or self.J.reg.action_of(symbol) == 'B': self.J._close_saves(); return True
        if symbol in (K.LEFT, K.UP): self.cur = (self.cur - 1) % 3; return True
        if symbol in (K.RIGHT, K.DOWN, K.TAB): self.cur = (self.cur + 1) % 3; return True
        if symbol in (K.RETURN, K.ENTER, K.SPACE) or self.J.reg.action_of(symbol) == 'A':
            if self.press(self.cur): self.J.sound.play_sfx(SFX_BUTTON)
            return True
        return True

    def click(self, x, y, button):
        if button == pyglet.window.mouse.RIGHT: self.J._close_saves(); return
        for x0, y0, x1, y1, i in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1:
                self.cur = i
                if self.press(i): self.J.sound.play_sfx(SFX_BUTTON)
                return

    def hover(self, x, y):
        self.hovered = None
        for x0, y0, x1, y1, i in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: self.hovered = i; self.cur = i; return

    # ---- dessin
    def _lines(self, P, text, width_px, size_value):
        """Texte coupe aux mots (et aux caracteres pour un chemin sans espace) pour tenir dans `width_px` pixels."""
        out = []
        for para in text.split('\n'):
            cur = ''
            for word in para.split(' '):
                attempt = (cur + ' ' + word) if cur else word
                if P._label(attempt, size_value).content_width <= width_px: cur = attempt; continue
                if cur: out.append(cur)
                while P._label(word, size_value).content_width > width_px and len(word) > 1:       # mot trop long (chemin) : coupe au dernier caractere qui tient
                    n = len(word)
                    while n > 1 and P._label(word[:n], size_value).content_width > width_px: n -= 1
                    out.append(word[:n]); word = word[n:]
                cur = word
            out.append(cur)
        return out

    def draw_all(self, J, cx, cy, ui_scale):
        P = J.pause; k = ui_scale * 800.0 / 900.0
        ui_scale = min(ui_scale, 0.97 * J.height / (BORDER[3] - BORDER[1])); k = ui_scale * 800.0 / 900.0
        U = lambda x, y: (cx + x * ui_scale, cy + y * ui_scale)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        background = pyglet.shapes.Rectangle(0, 0, J.width, J.height, color=(0, 0, 0)); background.opacity = 170; background.draw()           # le menu de depart reste visible, assombri
        x0, y0 = U(BORDER[0], BORDER[1]); x1, y1 = U(BORDER[2], BORDER[3]); P._border(x0, y0, x1 - x0, y1 - y0, k)
        P._restore_blend()

        def text(t, x, y, size_value, clr=WHITE, anchor=1):
            label = P._label(t, size_value * ui_scale * 0.75, clr); w = label.content_width; px, py = U(x, y)
            label.x = px - (w / 2 if anchor == 1 else (w if anchor == 2 else 0)); label.y = py - size_value * ui_scale * 0.30; label.draw()
        text(TITLE, 0, BORDER[3] - 40, 26)
        y = BORDER[3] - 82; wid = (BORDER[2] - BORDER[0] - 40) * ui_scale
        for line in EXPLANATION:
            for l in self._lines(P, tr(line), wid, 13 * ui_scale * 0.75):          # (traduite en entier avant d'etre coupee aux mots)
                text(l, BORDER[0] + 20, y, 13, HELPTEXT, 0); y -= 17
            y -= 4
        mouse = J.last_device == 'souris'; zones = []
        for i, lib in enumerate(BUTTONS):
            xc = (i * 2 - 1) * BTN_X; a, b = U(xc - BTN_L / 2, BTN_Y - BTN_H / 2); w, h = BTN_L * ui_scale, BTN_H * ui_scale
            selected = self.cur == i; over = mouse and self.hovered == i; occupied = self.dialogue is not None
            P._plate(a, b, w, h, k, over or (selected and not mouse))                    # (souris : la plaque sous le pointeur s'assombrit, sans encadre jaune)
            if selected and not mouse: P._cursor(a - 24 * ui_scale, b + h / 2, 28 * ui_scale)
            P._restore_blend(); text(lib, xc, BTN_Y, 20, GRAY if occupied else WHITE)
            zones.append((a, b, a + w, b + h, i))
        # message de resultat
        y = BTN_Y - BTN_H / 2 - 30; msg_width = wid - (BACK_WIDTH + 14) * ui_scale                  # (le message s'arrete avant le bouton retour, en bas a droite)
        for line in self.msg:
            for l in self._lines(P, line, msg_width, 14 * ui_scale * 0.75):
                text(l, BORDER[0] + 20, y, 14, self.msg_clr, 0); y -= 18
        a, b = U(BORDER[2] - BACK_WIDTH - 14, BORDER[1] + 12); w, h = BACK_WIDTH * ui_scale, BACK_HEIGHT * ui_scale
        over = mouse and self.hovered == I_BACK
        P._back_button(a, b, w, h, over or (self.cur == I_BACK and not mouse))
        if self.cur == I_BACK and not mouse: P._cursor(a - 24 * ui_scale, b + h / 2, 28 * ui_scale)
        zones.append((a, b, a + w, b + h, I_BACK)); self.zones = zones
