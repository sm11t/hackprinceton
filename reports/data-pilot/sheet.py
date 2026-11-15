import glob, os, sys
from PIL import Image, ImageDraw
D=os.path.dirname(os.path.abspath(__file__)); os.makedirs(f'{D}/sheets',exist_ok=True)
tags=sorted({os.path.basename(f).split('_loc')[0] for f in glob.glob(f'{D}/img/*_loc*.jpg')})
for t in tags:
    fs=sorted(glob.glob(f'{D}/img/{t}_loc*.jpg'),key=lambda f:(int(f.split('_loc')[1].split('_')[0]),f))
    W=360; cols=2; rows=(len(fs)+1)//2
    sheet=Image.new('RGB',(W*cols,W*rows+30),'white'); dr=ImageDraw.Draw(sheet); dr.text((6,8),t,fill='black')
    for i,f in enumerate(fs):
        im=Image.open(f).convert('RGB').resize((W,W)); sheet.paste(im,((i%cols)*W,30+(i//cols)*W))
    sheet.save(f'{D}/sheets/{t}.jpg',quality=85)
print(tags)
