import pathlib,json,subprocess,concurrent.futures,math,wave,struct,glob
from PIL import Image,ImageDraw,ImageFont
ROOT=pathlib.Path(__file__).resolve().parents[1]; AS=ROOT/'assets'; AU=ROOT/'audio'; AS.mkdir(exist_ok=True); AU.mkdir(exist_ok=True)
scenes=json.loads((ROOT/'production'/'scenes.json').read_text())
fontjp=glob.glob('/System/Library/Fonts/*角*W6.ttc')[0]; fontregular=glob.glob('/System/Library/Fonts/*角*W3.ttc')[0]
mono='/System/Library/Fonts/Menlo.ttc'
def font(n,bold=True):return ImageFont.truetype(fontjp if bold else fontregular,n)
def center(d,txt,y,f,fill):d.text((960,y),txt,font=f,anchor='mt',fill=fill)
def disk(d,x,y,s):
 d.rectangle((x,y,x+16*s,y+16*s),fill='#cfe9d8');d.rectangle((x+2*s,y+2*s,x+14*s,y+14*s),fill='#114c38');d.rectangle((x+5*s,y+2*s,x+11*s,y+6*s),fill='#fffaf0');d.rectangle((x+9*s,y+3*s,x+10*s,y+5*s),fill='#114c38');d.rectangle((x+4*s,y+9*s,x+12*s,y+13*s),fill='#fffaf0')
for s in scenes:
 im=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,102),fill=(17,60,45,247));disk(d,54,22,3.5);d.text((130,22),'floppy.io',font=ImageFont.truetype(mono,39),fill='#fffaf0');d.text((480,29),s['label'],font=font(31),fill='#d9ebdf');d.text((1834,34),s['id']+' / 09',font=ImageFont.truetype(mono,24),fill='#b9d8c7',anchor='rt')
 if s['caption']:
  d.rectangle((68,863,1852,1030),fill=(13,46,34,244));d.rectangle((68,863,78,1030),fill='#b8dfca')
  lines=s['caption'];top=907 if len(lines)==1 else 887
  for i,line in enumerate(lines):d.text((116,top+i*61),line,font=font(42),fill='#fffaf0')
 im.save(AS/(s['id']+'_overlay.png'))
# End card and matching thumbnail, using the app's palette.
im=Image.new('RGB',(1920,1080),'#113c2d');d=ImageDraw.Draw(im)
for x in range(24,1920,32):
 for y in range(24,1080,32):d.point((x,y),fill='#254d3d')
d.rectangle((68,64,1852,1016),outline='#83ae96',width=2);disk(d,836,132,15.5)
center(d,'floppy.io',432,ImageFont.truetype(mono,91),'#fffaf0')
center(d,'1.44MBしか使えない静寂のレトロSNS',568,font(47),'#d3e9db')
center(d,'小さな1枚に、あなたは何を残しますか？',697,font(39),'#fffaf0')
d.rectangle((455,818,1465,905),fill='#cfe9d8');center(d,'fdd.wawa-app.me/floppy.io/',841,ImageFont.truetype(mono,36),'#113c2d')
center(d,'HEROES LEAGUE 2026  /  PRODUCT DEMO',959,ImageFont.truetype(mono,21),'#a7cbb7')
im.save(AS/'end_card.png')
thumb=Image.new('RGB',(1920,1080),'#fffaf0');d=ImageDraw.Draw(thumb);d.rectangle((0,0,1920,1080),outline='#cfe9d8',width=45);disk(d,1370,330,25)
d.text((130,120),'floppy.io',font=ImageFont.truetype(mono,72),fill='#114c38');d.text((120,330),'1.44MB',font=ImageFont.truetype(mono,170),fill='#114c38');d.text((133,550),'しか、使えない。',font=font(83),fill='#202923');d.text((137,728),'1投稿＝フロッピー1枚分',font=font(46),fill='#114c38');d.text((138,820),'静寂のレトロSNS',font=font(46),fill='#114c38');thumb.save(ROOT/'floppy_io_thumbnail.png')

# Voice credit on the closing card.
im=Image.open(AS/'end_card.png');d=ImageDraw.Draw(im)
d.rectangle((300,929,1620,1000),fill='#113c2d')
center(d,'HEROES LEAGUE 2026  /  PRODUCT DEMO',934,ImageFont.truetype(mono,18),'#a7cbb7')
center(d,'VOICEVOX：春日部つむぎ',969,font(22,False),'#d3e9db')
im.save(AS/'end_card.png')
