"""Small synthesized engine and UI sounds; generated locally, no media downloads."""
import math
import struct
import wave
from pathlib import Path


class Audio:
    def __init__(self, loader, directory):
        self.muted = False
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.sounds = {}
        for name, freq, duration in [('engine',70,1),('impact',65,.2),('gate',660,.18),('boost',220,.25)]:
            path=directory/f'{name}.wav'
            if not path.exists():
                with wave.open(str(path),'wb') as out:
                    out.setparams((1,2,22050,0,'NONE','not compressed'))
                    samples=[]
                    for i in range(int(22050*duration)):
                        t=i/22050
                        envelope=1 if name=='engine' else (1-t/duration)**2
                        v=(math.sin(math.tau*freq*t)+.3*math.sin(math.tau*freq*2*t))*.2*envelope
                        samples.append(struct.pack('<h',int(v*32767)))
                    out.writeframes(b''.join(samples))
            self.sounds[name]=loader.loadSfx(str(path))
        self.sounds['engine'].setLoop(True)
        self.sounds['engine'].setVolume(0)
        self.sounds['engine'].play()

    def update(self, speed, active):
        self.sounds['engine'].setPlayRate(.65+speed/23)
        self.sounds['engine'].setVolume(0 if self.muted or not active else .10+speed/600)

    def play(self, event):
        if not self.muted:
            name='impact' if event=='IMPACT' else 'boost' if 'BOOST' in event else 'gate'
            self.sounds[name].play()
