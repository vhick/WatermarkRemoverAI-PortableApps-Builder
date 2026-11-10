"""Generate independently drawn community launcher branding (no upstream logo claim)."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
R = Path(__file__).parent
SZ = 512
im = Image.new('RGBA', (SZ, SZ), (0,0,0,0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((24,24,488,488), radius=104, fill=(26,58,94,255))
d.ellipse((92,90,418,410), outline=(84,216,226,255), width=26)
d.line([(135,170),(195,342),(255,232),(312,342),(375,170)], fill=(247,252,255,255), width=33, joint='curve')
d.arc((92,90,418,410), 205, 325, fill=(112,231,205,255), width=28)
for size in [16,32,48,128,256]:
    im.resize((size,size), Image.Resampling.LANCZOS).save(R/f'appicon_{size}.png')
im.save(R/'appicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
