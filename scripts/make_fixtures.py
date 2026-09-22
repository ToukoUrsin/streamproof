"""Create labeled synthetic control images. These are not field observations."""
from pathlib import Path
import json
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"
rng = np.random.default_rng(20260921)
h, w = 800, 1200
base = np.zeros((h, w, 3), np.uint8)
base[:] = (65, 92, 73)
noise = rng.normal(0, 8, (h, w, 1))
base = np.clip(base.astype(float) + noise, 0, 255).astype(np.uint8)
# Stable, deliberately diagrammatic bank features for registration.
for _ in range(900):
    x,y=rng.integers(0,w),rng.integers(0,h)
    if x < 360 or x > 840 or y < 220:
        color=tuple(int(x) for x in rng.integers(40,170,3))
        cv2.circle(base,(int(x),int(y)),int(rng.integers(3,20)),color,-1)
water=np.clip(np.array([125,116,72])+rng.normal(0,7,(580,480,1)),0,255).astype(np.uint8)
base[220:800,360:840]=water
for y in range(236,790,10):
    for x in range(375,824,55):
        cv2.line(base,(x+int(rng.integers(-7,7)),y),(x+35,y+int(rng.integers(-3,4))),(151,141,104),1)
cv2.rectangle(base,(16,16),(1184,93),(30,45,36),-1)
cv2.putText(base,'SYNTHETIC CONTROL / NOT A FIELD PHOTO',(38,49),cv2.FONT_HERSHEY_SIMPLEX,.65,(222,240,219),1,cv2.LINE_AA)
cv2.putText(base,'Engineered texture + fixed bank landmarks',(38,77),cv2.FONT_HERSHEY_SIMPLEX,.45,(176,194,176),1,cv2.LINE_AA)
changed=base.copy()
patch=changed[350:700,400:810]
changed[350:700,400:810]=np.clip(patch.astype(np.int16)+np.array([-38,22,55]),0,255).astype(np.uint8)
blur=cv2.GaussianBlur(base,(71,71),0)
glare=base.copy();glare[300:760,380:820]=(254,254,254)
dark=np.clip(base.astype(float)*.1,0,255).astype(np.uint8)
light=np.clip(base.astype(float)*1.5+25,0,255).astype(np.uint8)
for name,img in [('control-baseline',base),('control-change',changed),('control-blur',blur),('control-glare',glare),('control-dark',dark),('control-light',light)]:
    cv2.imwrite(str(OUT/(name+'.png')),img)
manifest=[]
for name,label,description in [
    ('control-baseline','Baseline control','A synthetic stream-like image with fixed bank features.'),
    ('control-change','Visible change control','The same synthetic scene with a deliberately altered color patch.'),
    ('control-blur','Blur control','A deliberately blurred synthetic scene; the quality gate should stop.'),
    ('control-glare','Reflection control','An artificial bright patch; the reflection check should stop.'),
    ('control-dark','Exposure control','An artificially darkened frame; the exposure check should stop.'),
    ('control-light','Lighting shift control','A global synthetic exposure change, not local water change.')]:
    manifest.append({'id':name,'file':name+'.png','label':label,'description':description,'site':'Illustrated stream · control case','roi':[.32,.32,.68,.94],
      'provenance':{'kind':'synthetic_fixture','label':'Synthetic control · not field evidence','author':'Streamproof fixture generator','license':'MIT','generator':'scripts/make_fixtures.py','seed':20260921,'field_validation':False,'description':description}})
for key,file,label,roi in [('river-ver','river-ver.jpg','River Ver, England',[.49,.61,.71,.92]),('river-liffey','river-liffey.jpg','River Liffey, Ireland',[.28,.62,.70,.95])]:
    provenance=json.loads((OUT/(file+'.json')).read_text())
    provenance.update(kind='historical_public_photo',label='Historical CC0 photograph · not a current incident',field_validation=False)
    manifest.append({'id':key,'file':file,'label':label,'site':label,'roi':roi,'description':provenance['use'],'provenance':provenance})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(f'Generated {len(manifest)} documented sample entries with OpenCV {cv2.__version__}')
