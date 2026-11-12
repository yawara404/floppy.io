import pathlib,json,subprocess,concurrent.futures,math,wave,struct,glob
from PIL import Image,ImageDraw,ImageFont
ROOT=pathlib.Path(__file__).resolve().parents[1]; AS=ROOT/'assets'; AU=ROOT/'audio'; AS.mkdir(exist_ok=True); AU.mkdir(exist_ok=True)
scenes=[
 dict(id='01',source='01_hero',start=0,duration=6,label='もし、SNSの1投稿が…',caption=['もし、SNSの1投稿が','フロッピーディスク1枚分だったら？'],voice='もし、SNSの一投稿が、フロッピーディスク一枚分だったら？'),
 dict(id='02',source='01_hero',start=0,duration=6,label='1 POST = 1 DISK',caption=['1投稿、1.44MB。','静けさと制約を楽しむ、レトロSNS。'],voice='フロッピー・アイオーは、一投稿1.44メガバイトの、静かなレトロSNSです。'),
 dict(id='03',source='05_draw_floppy',start=1,duration=13,label='小さく描く。',caption=['ブラウザで描く、小さなドット絵。','16色のパレットから、自分だけの1枚を。'],voice='ブラウザで、小さなドット絵を描く。十六色のパレットから色を選んで、ひとマスずつ、自分だけの一枚を仕上げます。'),
 dict(id='04',source='06_text_and_aa',start=2,duration=8,label='言葉を添える。',caption=['今日のひと言に、懐かしいAAも。','スタンプ感覚で、気持ちを添える。'],voice='今日のひと言に、懐かしいアスキーアートも。スタンプ感覚で、気持ちを添えられます。'),
 dict(id='05',source='07_capacity_meter',start=3,duration=8,label='容量と、相談する。',caption=['本文も、絵も、添付ファイルも。','合計1.44MBに収める。'],voice='本文も、絵も、添付ファイルも。使った容量を確かめながら、合計1.44メガバイトに収めます。'),
 dict(id='06',source='04_disks',start=0,duration=6,label='趣味を、持ち寄る。',caption=['コミュニティ「ディスク」で、','好きなものを持ち寄る。'],voice='趣味のコミュニティ、ディスクで、好きなものを持ち寄れます。'),
 dict(id='07',source='03_share_preview',start=4,duration=5,label='小さな作品を、共有する。',caption=['投稿は、プレビューを確かめて共有。'],voice='投稿は、プレビューを確かめて共有できます。'),
 dict(id='08',source='02_pixel_post',start=0,duration=3,label='Nuxt 4 × FastAPI',caption=['容量は、画面とAPIの両方で検証。'],voice='画面とAPIで、容量を検証。'),
 dict(id='09',source=None,start=0,duration=5,label='あなたの1枚を。',caption=[],voice='小さな一枚に、あなたは何を残しますか？')
]
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
(ROOT/'production'/'scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2))
def gen(s):
 p=AU/('narration_'+s['id']+'.aiff');subprocess.run(['say','-v','Kyoko','-r','210','-o',str(p),s['voice']],check=True);dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)]));print(s['id'],'voice',round(dur,2),'scene',s['duration'],flush=True);return dur
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:durations=list(ex.map(gen,scenes))
for s,t in zip(scenes,durations):s['voice_duration']=t
(ROOT/'production'/'scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2))
def stamp(t):
 n=round(t*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
time=0;captions=[];text=[]
for i,s in enumerate(scenes):
 captions.append(f'{i+1}\n{stamp(time)} --> {stamp(time+s["duration"])}\n'+('\n'.join(s['caption']) if s['caption'] else '小さな1枚に、あなたは何を残しますか？')+'\n');text.append(f'{stamp(time)}  {s["voice"]}');time+=s['duration']
(ROOT/'floppy_io_captions.srt').write_text('\n'.join(captions));(ROOT/'ナレーション原稿.txt').write_text('\n\n'.join(text))
# Quiet, original pentatonic bed. No third-party recording or song is used.
sr=48000;length=60;notes=[60,67,64,69,62,67,64,72];buf=bytearray()
for i in range(sr*length):
 t=i/sr;v=0.0
 for lane,step in [(0,1.5),(1,6.0)]:
  k=int(t/step);a=t-k*step;freq=440*2**(((notes[k%len(notes)] if lane==0 else 48)-69)/12)
  env=(1-math.exp(-a*60))*math.exp(-a*(3.8 if lane==0 else .8));v+=((math.sin(2*math.pi*freq*a)+.12*math.sin(2*math.pi*2*freq*a))*env*(.028 if lane==0 else .012))
 v*=min(1,t/2,(length-t)/3);q=int(max(-1,min(1,v))*32767);buf.extend(struct.pack('<hh',q,q))
with wave.open(str(AU/'original_bgm.wav'),'wb') as w:w.setparams((2,2,sr,0,'NONE','not compressed'));w.writeframes(buf)
print('assets ready',flush=True)
