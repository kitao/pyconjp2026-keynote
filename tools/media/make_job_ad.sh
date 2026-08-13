#!/bin/sh
# P.4 の求人票を高解像度で切り出して assets/quote/job_ad.png を作り直す。
# P.4 のデザインや文言を直したら、これを走らせて P.6 の引用画像を更新する。
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
# P.6 での表示は 732px 幅。ファイルはその3倍あれば足りるので縮めておく
# （切り出しの原寸のままだと4200px超で、リポジトリと PDF を無駄に太らせる）
c.thumbnail((2198, 10000), Image.LANCZOS)
c.save('assets/quote/job_ad.png')
print(f'assets/quote/job_ad.png {c.width}x{c.height}  比 {c.width/c.height:.3f}')
"
rm -f _job_tmp.md _job_tmp*.png
