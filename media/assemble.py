"""Render a narrated demo from actual browser screencast frames.

Input: media/raw/sceneN/frames.json containing
  {"frames":[{"file":"00000.jpg","timestamp":1790000000.0},...],
   "startedAt":1790000000.0,"endedAt":1790000030.0}
Timestamps may be wall-clock seconds or milliseconds. They are only used for
relative frame durations. Never invent interaction frames. Extra narration time
holds the last captured application frame; audio is not sped up.
"""
import hashlib, json, pathlib, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT=pathlib.Path(__file__).resolve().parent
TITLES=["01  A BETTER SECOND LOOK","02  A USEFUL BASELINE","03  FOLLOW THE DIFFERENCE","04  CHECK THE LIGHT","05  ASK FOR A BETTER IMAGE","06  RECORD AN INTERPRETATION","07  KEEP THE EVIDENCE"]

def duration(path):
 return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],text=True))

def call(args):
 subprocess.run(args,check=True)

def stamp(t):
 total=int(round(t*1000));hours=total//3600000;minutes=total%3600000//60000;seconds=total%60000//1000;millis=total%1000
 return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'

def quote(path):return str(path).replace("'", "'\\''")

def main():
 (ROOT/'renders').mkdir(exist_ok=True)
 audio_durations=[duration(ROOT/f'scene-{i:02}.mp3') for i in range(1,8)]
 pacing=json.loads((ROOT/'pacing.json').read_text())
 edits=json.loads((ROOT/'edit-manifest.json').read_text())
 parts=[];offset=0;subtitles=[];chapter_lines=[];subtitle_index=0
 for i,audio_len in enumerate(audio_durations,1):
  scene=ROOT/'raw'/f'scene{i}'
  if not (scene/'frames.json').exists():
   print(json.dumps({'waiting_for_scene':i,'completed_renders':[str(p) for p in parts]}));return
  def ftime(frame):
   value=frame.get('timestamp',frame.get('at',frame.get('time',frame.get('t'))))
   if value is None:raise ValueError('Every frame needs its captured timestamp')
   return float(value)/1000 if float(value)>1e11 else float(value)
  manifests=sorted((ROOT/'raw').glob(f'scene{i}*/frames.json'))
  frames=[];timeline=0
  for manifest_path in manifests:
   manifest=json.loads(manifest_path.read_text());chunk=manifest['frames'] if isinstance(manifest,dict) else manifest
   if not chunk:continue
   chunk=sorted(chunk,key=ftime)
   first_time=ftime(chunk[0]);last_time=first_time
   for frame in chunk:
    name=frame.get('file',frame.get('path',frame.get('name')));path=pathlib.Path(name)
    if not path.is_absolute():path=manifest_path.parent/path
    captured=ftime(frame)
    if captured<last_time:raise ValueError('Frame times are not monotonic within a capture')
    frames.append({'file':str(path),'timestamp':timeline+captured-first_time});last_time=captured
   timeline+=last_time-first_time+1.0
  for extra in edits['chapters'].get(str(i),{}).get('append_frames',[]):
   frames.append({'file':str(ROOT/'raw'/extra['file']),'timestamp':timeline})
   timeline+=extra.get('duration',1.0)
  if not frames:raise ValueError(f'No real frames in scene {i}')
  times=[ftime(f) for f in frames]
  if any(b<a for a,b in zip(times,times[1:])):raise ValueError('Frame times are not monotonic')
  target=audio_len+1.5
  records=[]
  for index,frame in enumerate(frames):
   name=frame.get('file',frame.get('path',frame.get('name')));path=pathlib.Path(name)
   if not path.is_absolute():path=scene/path
   if not path.exists():raise ValueError(f'Missing captured frame: {path}')
   delta=times[index+1]-times[index] if index+1<len(frames) else 1.0
   delta+=pacing.get(str(path.relative_to(ROOT/'raw')),0)
   records.extend([f"file '{quote(path)}'",f'duration {max(delta,0.001):.6f}'])
  records.append(f"file '{quote(path)}'")
  concat=ROOT/'renders'/f'scene-{i:02}.ffconcat';concat.write_text('\n'.join(records)+'\n')
  label=ROOT/'renders'/f'title-{i:02}.png'
  bar=Image.new('RGB',(1920,64),'#243e33');draw=ImageDraw.Draw(bar)
  font=ImageFont.truetype('/System/Library/Fonts/Monaco.ttf',20);small=ImageFont.truetype('/System/Library/Fonts/Monaco.ttf',16)
  draw.text((40,18),TITLES[i-1],font=font,fill='#d2dcb1')
  right='STREAMPROOF  /  WORKING PROTOTYPE';draw.text((1880-draw.textlength(right,font=small),21),right,font=small,fill='#d2dcb1');bar.save(label)
  rendered=ROOT/'renders'/f'scene-{i:02}.mp4';parts.append(rendered)
  vf=f"[0:v]scale=1920:980:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:70:color=0xf3f2e9,setsar=1,tpad=stop_mode=clone:stop_duration={target:.3f}[footage];[footage][2:v]overlay=0:0:shortest=0[video]"
  newest_input=max(*[p.stat().st_mtime for p in manifests],(ROOT/f'scene-{i:02}.mp3').stat().st_mtime)
  signature=hashlib.sha256(('\n'.join(records)+vf).encode()).hexdigest()
  signature_file=ROOT/'renders'/f'scene-{i:02}.signature'
  if not rendered.exists() or rendered.stat().st_mtime<newest_input or not signature_file.exists() or signature_file.read_text()!=signature:
   call(['ffmpeg','-y','-v','warning','-threads','2','-f','concat','-safe','0','-i',str(concat),'-i',str(ROOT/f'scene-{i:02}.mp3'),'-i',str(label),'-filter_complex_threads','2','-filter_complex',vf,'-map','[video]','-map','1:a','-af','adelay=500|500,apad','-t',f'{target:.3f}','-r','30','-c:v','libx264','-threads','2','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(rendered)])
   signature_file.write_text(signature)
  text=(ROOT/f'scene-{i:02}.txt').read_text().strip();words=text.split();chunks=[];chunk=[]
  for word in words:
   chunk.append(word)
   if len(' '.join(chunk))>100 and (word.endswith(('.',',',';',':')) or len(chunk)>=23):chunks.append(' '.join(chunk));chunk=[]
  if chunk:chunks.append(' '.join(chunk))
  spoken=0;word_total=sum(len(c.split()) for c in chunks)
  for chunk in chunks:
   start=offset+.5+audio_len*spoken/word_total;spoken+=len(chunk.split());end=offset+.5+audio_len*spoken/word_total;subtitle_index+=1
   subtitles.append(f'{subtitle_index}\n{stamp(start)} --> {stamp(end)}\n'+ '\n'.join(textwrap.wrap(chunk,72))+'\n')
  chapter_lines.append(f'{int(offset//60):02}:{int(offset%60):02} {TITLES[i-1][4:].title()}')
  offset+=target
 final_concat=ROOT/'renders'/'final.ffconcat';final_concat.write_text('\n'.join(f"file '{quote(p)}'" for p in parts)+'\n')
 (ROOT/'streamproof-demo.srt').write_text('\n'.join(subtitles))
 (ROOT/'CHAPTERS.txt').write_text('\n'.join(chapter_lines)+'\n')
 call(['ffmpeg','-y','-v','warning','-threads','2','-f','concat','-safe','0','-i',str(final_concat),'-i',str(ROOT/'streamproof-demo.srt'),'-map','0:v','-map','0:a','-map','1:0','-c:v','copy','-c:a','aac','-threads','2','-af','aresample=async=1:first_pts=0','-b:a','192k','-c:s','mov_text','-metadata:s:s:0','language=eng','-metadata','title=Streamproof — A better second look','-metadata','comment=Actual local prototype. Stock synthetic narration. Historical photo and labeled synthetic controls. AI-assisted demo operator assessment, not human field review. No water chemistry or AWS deployment claim.','-movflags','+faststart',str(ROOT/'streamproof-demo.mp4')])
 print(json.dumps({'video':str(ROOT/'streamproof-demo.mp4'),'duration':duration(ROOT/'streamproof-demo.mp4'),'chapters':chapter_lines},indent=2))

if __name__=='__main__':main()
