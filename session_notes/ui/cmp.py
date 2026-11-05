import sys
from PIL import Image, ImageDraw
shot = Image.open('/mnt/user-data/attachments/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/59a3d7d5-image.png').convert('RGB')   # 405 x 114
mine = Image.open('fr35_s2.png').convert('RGB')
# plaque dans mon rendu : x 313..624, y 113..195 ; la capture : x 5..315, y 14..97
ox, oy = 313 - 5, 113 - 14
crop = mine.crop((ox, oy, ox + 405, oy + 114))
W = 405; canvas = Image.new('RGB', (W, 114 * 2 + 6), (255, 0, 255)); canvas.paste(shot, (0, 0)); canvas.paste(crop, (0, 120))
canvas = canvas.resize((W * 2, (114 * 2 + 6) * 2), Image.LANCZOS); canvas.save('cmp_capture_vs_rendu.png'); print(canvas.size)
