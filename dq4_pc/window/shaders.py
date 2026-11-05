"""Programmes de dessin (GLSL) de la fenetre."""


VERTEX = '''#version 330 core
in vec3 position; in vec2 tex_coords; in vec4 colors;
uniform mat4 mvp;
centroid out vec2 v_uv; out vec4 v_col;
void main() { gl_Position = mvp * vec4(position, 1.0); v_uv = tex_coords; v_col = colors; }'''

FRAG = '''#version 330 core
centroid in vec2 v_uv; in vec4 v_col; out vec4 fragColor;
uniform sampler2D tex; uniform float cutoff; uniform vec2 tsize; uniform float net; uniform float amul; uniform float a2c; uniform vec3 teinte; uniform float sepia;      // teinte : paquet 33 (decor seulement), 1, 1, 1 = neutre ; sepia : paquet 1 (decor des villes seulement), 0 = couleurs d'origine
void main() {
    vec2 uv = v_uv; float lod = 0.0;
    if (net > 0.5) { vec2 p0 = uv * tsize; vec2 dx = dFdx(p0), dy = dFdy(p0); lod = max(0.0, 0.5 * log2(max(max(dot(dx, dx), dot(dy, dy)), 1e-8))); }      // mipmaps choisies sur l'uv d'origine (l'uv decalee saute d'un texel a l'autre)
    if (net > 1.5) { uv = (floor(uv * tsize) + 0.5) / tsize; }      // pixel perfect : plus proche voisin strict, aucun adoucissement
    else if (net > 0.5) {   // pixel art : on garde des pixels nets, seule la frontiere entre deux pixels est adoucie
        vec2 p = uv * tsize; vec2 b = floor(p + 0.5); vec2 w = max(fwidth(p), vec2(1e-4));       // b = frontiere de texel la plus proche : le centre du texel reste pur, seule une bande d'un pixel d'ecran autour de la frontiere est melangee
        uv = (b + clamp((p - b) / w, -0.5, 0.5)) / tsize;
    }
    vec4 c = (net > 0.5 ? textureLod(tex, uv, lod) : texture(tex, uv)) * clamp(v_col, 0.0, 1.0);
    vec3 m = c.rgb * teinte;
    if (sepia > 0.5) m = vec3(dot(vec3(0.299, 0.587, 0.114), m)) + vec3(0.109375, -0.0546875, 0.0);      // Custom/fld_*_sepia (retours en arriere, cmd_map_effect_sepia) : gris (0,299 ; 0,587 ; 0,114) de texture x couleur de sommet x _Color, plus (0,109375 ; -0,0546875 ; 0), alpha inchange
    c.rgb = clamp(m, 0.0, 1.0);      // texture x couleur de sommet x _Color (fld_*.frag) : _Color = _OrgColor (blanc, alpha d'origine : FldObject.save_org_color) x teinte du paquet 33, qui peut depasser 1 (1,25 en rouge) : saturation a l'ecriture, comme le tampon d'image
    if (a2c > 0.5) { c.a = clamp((c.a - cutoff) / max(fwidth(c.a), 1e-4) + 0.5, 0.0, 1.0); if (c.a <= 0.0) discard; }      // decor decoupe (fleurs, feuillages, grilles) : la silhouette devient une couverture de 0 a 4 echantillons (MSAA), pas un bord dur qui scintille
    else if (c.a < cutoff) discard;
    c.a *= amul; fragColor = c; }'''

VERTEX_EFFECT = '''#version 330 core
in vec2 position; in vec2 tex_coords; in vec4 colors;
out vec2 v_uv; out vec4 v_col;
void main() { gl_Position = vec4(position, 0.0, 1.0); v_uv = tex_coords; v_col = colors; }'''

FRAG_EFFECT = '''#version 330 core
in vec2 v_uv; in vec4 v_col; out vec4 fragColor;
uniform sampler2D tex; uniform float lum; uniform float flou;
void main() { vec3 c = texture(tex, v_uv, flou).rgb; fragColor = vec4(c * v_col.rgb * lum, v_col.a * lum); }'''

BLUR_EFFECT = 1.0              # Capture.SetBlur(vrai) pendant l'effet : la capture est adoucie (biais de mipmap)

# Fond des villes (#111) : `BackColor` du jeu = un quadrilatere plein ecran (sommets (1, 1), (-1, 1), (-1, -1), (1, -1) ecrits TELS QUELS en espace de decoupe : shader « BackColor », `gl_Position = in_POSITION0`,
# `SV_Target0 = vs_COLOR0`, file Background, ZTest Always, ZWrite Off, aucune fusion) dont les deux sommets du haut ont la couleur « haut » du paquet 8 et les deux du bas la couleur « bas » (BackColor.SetColor(haut, bas, 0),
# RVA 0xCC43F8) : un degrade vertical lineaire sur toute la hauteur de l'image, derriere tout le reste.
VERTEX_GRADIENT = '''#version 330 core
in vec2 position; uniform vec3 haut; uniform vec3 bas; out vec3 v_col;
void main() { gl_Position = vec4(position, 0.0, 1.0); v_col = mix(bas, haut, position.y * 0.5 + 0.5); }'''

FRAG_GRADIENT = '''#version 330 core
in vec3 v_col; out vec4 fragColor;
void main() { fragColor = vec4(v_col, 1.0); }'''
