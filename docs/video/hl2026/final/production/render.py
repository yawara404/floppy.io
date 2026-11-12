import pathlib,subprocess,json
R=pathlib.Path(__file__).resolve().parents[1];S=R.parent;A=R/'assets';U=R/'audio';CUT=R/'production'/'cuts';CUT.mkdir(exist_ok=True);scenes=json.loads((R/'production'/'scenes.json').read_text())
def run(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y']+args,check=True)
for s in scenes:
 sid=s['id'];target=CUT/(sid+'.mp4')
 if s['source']:
  y=180 if sid in ('03','04') else 70
  src=['-ss',str(s['start']),'-i',str(S/(s['source']+'.mp4'))]
  vf=f'[0:v]crop=1360:765:280:{y},scale=1920:1080:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration=3[base];[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
  src+=['-loop','1','-i',str(A/(sid+'_overlay.png'))]
 else:
  src=['-loop','1','-i',str(A/'end_card.png')];vf='[0:v]format=yuv420p[v]'
 run(src+['-filter_complex',vf,'-map','[v]','-t',str(s['duration']),'-r','30','-an','-c:v','libx264','-threads','3','-preset','fast','-crf','18',str(target)])
 targetvoice=U/('scene_'+sid+'.wav');factor=max(1,s['voice_duration']/(s['duration']-.6))
 run(['-i',str(U/('narration_'+sid+'.aiff')),'-af',f'atempo={factor},loudnorm=I=-17:TP=-2:LRA=7,adelay=180:all=1,apad','-t',str(s['duration']),'-ar','48000','-ac','2','-c:a','pcm_s16le',str(targetvoice)])
 print('rendered',sid,flush=True)
(CUT/'concat.txt').write_text(''.join("file '"+str(CUT/(s['id']+'.mp4'))+"'\n" for s in scenes))
(U/'concat.txt').write_text(''.join("file '"+str(U/('scene_'+s['id']+'.wav'))+"'\n" for s in scenes))
run(['-f','concat','-safe','0','-i',str(CUT/'concat.txt'),'-c','copy','-movflags','+faststart',str(R/'production'/'picture.mp4')])
run(['-f','concat','-safe','0','-i',str(U/'concat.txt'),'-c:a','pcm_s16le',str(U/'narration_full.wav')])
run(['-i',str(R/'production'/'picture.mp4'),'-i',str(U/'narration_full.wav'),'-i',str(U/'original_bgm.wav'),'-filter_complex','[2:a]volume=0.65,afade=t=in:st=0:d=2,afade=t=out:st=57:d=3[bg];[1:a][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','60','-movflags','+faststart',str(R/'floppy_io_HL2026_60s.mp4')])
print('FINAL READY',flush=True)
