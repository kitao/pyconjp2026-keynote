#!/bin/sh
# Re-cut the job ad on slide 4 at high resolution into assets/quote/job_ad.png.
# Run this after changing the design or wording of slide 4, so the quoted image
# on slide 6 matches.
set -e
cd "$(dirname "$0")/../.."

python3 -c "
md=open('slides.md').read().split('\n---\n')
p5=[p for p in md if 'アルバイト募集' in p and '受け取る額' in p][0]
open('_job_tmp.md','w').write(md[0]+'\n---\n'+p5)
"
npx --yes @marp-team/marp-cli@latest _job_tmp.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --images png --image-scale 4 -o _job_tmp.png </dev/null >/dev/null 2>&1

python3 -c "
from PIL import Image
import glob
f=sorted(glob.glob('_job_tmp*.png'))[0]
im=Image.open(f).convert('RGB'); px=im.load(); W,H=im.size; s=W/1920
xs=[];ys=[]
for y in range(int(230*s),int(1020*s)):
    for x in range(int(300*s),int(1700*s)):
        r,g,b=px[x,y]
        if abs(r-0xcf)<18 and abs(g-0xc8)<18 and abs(b-0xb6)<18:
            xs.append(x); ys.append(y)
c=im.crop((min(xs),min(ys),max(xs)+1,max(ys)+1))
# Slide 6 shows it 732 px wide, so three times that is plenty. Left at the
# original crop it would be over 4200 px and would bloat both the repository
# and the PDF.
c.thumbnail((2198, 10000), Image.LANCZOS)
c.save('assets/quote/job_ad.png')
print(f'assets/quote/job_ad.png {c.width}x{c.height}  ratio {c.width/c.height:.3f}')
"
rm -f _job_tmp.md _job_tmp*.png
