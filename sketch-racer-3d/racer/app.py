import json
import math
from pathlib import Path

from panda3d.core import (loadPrcFileData, Vec3, Vec4, AmbientLight,
    DirectionalLight, Fog, TextNode, WindowProperties, ClockObject, ModifierButtons)
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectWaitBar
from direct.gui.OnscreenText import OnscreenText

from .core import Race, Control, DT, LAPS, TIME_LIMIT
from .visuals import build_world, build_car, lines
from .audio import Audio

ROOT = Path(__file__).resolve().parent.parent
ORANGE=(.94,.34,.12,1)
CYAN=(.03,.43,.52,1)
TEXT=(.09,.20,.26,1)
MUTED=(.29,.42,.46,1)
PANEL=(.96,.985,.96,.95)


def time_text(seconds):
    return f'{int(seconds)//60:02d}:{seconds%60:05.2f}'


class Game(ShowBase):
    def __init__(self, smoke=False, screenshot=None, offscreen=False):
        loadPrcFileData('', '\n'.join([
            'window-title SKETCH RACER / Seoul City Run', 'win-size 1440 900',
            'sync-video true', 'framebuffer-multisample 1', 'multisamples 4',
            'show-frame-rate-meter false', 'textures-power-2 none',
            'audio-library-name p3openal_audio' if not smoke else 'audio-library-name null',
            'notify-level warning', 'default-directnotify-level warning',
            'window-type offscreen' if offscreen else 'window-type onscreen']))
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(.54,.81,.97,1)
        self.camLens.setNearFar(.15,1100)
        self.camLens.setFov(68)
        self.race=Race()
        self.keys={}
        self.accumulator=0.0
        self.camera_mode=0
        self.smoke=smoke
        self.screenshot=screenshot
        self.frames=0
        self.last_state=None
        self.toast_t=0
        self.visual_time=0
        self.saved=False
        self.record_path=ROOT/'.save'/'records.json'
        self.records={}
        try:
            data=json.loads(self.record_path.read_text())
            if isinstance(data,dict):
                self.records={k:v for k,v in data.items() if k in ('best_lap','best_score') and isinstance(v,(float,int)) and math.isfinite(v) and v>=0}
        except (OSError, ValueError):
            pass
        ambient=AmbientLight('ambient')
        ambient.setColor(Vec4(.80,.82,.78,1))
        self.render.setLight(self.render.attachNewNode(ambient))
        sunlight=DirectionalLight('daylight-key')
        sunlight.setColor(Vec4(.52,.49,.42,1))
        light=self.render.attachNewNode(sunlight)
        light.setHpr(-35,-48,0)
        self.render.setLight(light)
        fog=Fog('daylight-atmosphere')
        fog.setColor(.54,.81,.97)
        fog.setExpDensity(.0018)
        self.render.setFog(fog)
        # Use an installed Korean font when available; retain a portable English fallback.
        korean_font = None
        for path in ('/System/Library/Fonts/AppleSDGothicNeo.ttc',
                     'C:/Windows/Fonts/malgun.ttf',
                     '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
            if Path(path).is_file():
                korean_font = self.loader.loadFont(path, okMissing=True)
                if korean_font is not None:
                    break
        build_world(self.render,self.race,korean_font)
        self.car_nodes=[build_car(self.render,c.color) for c in self.race.cars]
        self.audio=Audio(self.loader,ROOT/'.cache'/'audio')
        self._build_ui()
        # Keep Shift+W/A/D and Shift+arrows as independent held keys. Otherwise
        # Panda prefixes events (e.g. "shift-a") and the steering binding misses them.
        if self.mouseWatcherNode:
            self.mouseWatcherNode.setModifierButtons(ModifierButtons())
        for thrower in self.buttonThrowers or []:
            thrower.node().setModifierButtons(ModifierButtons())
        for key in ['w','a','s','d','arrow_up','arrow_down','arrow_left','arrow_right','space','shift']:
            self.accept(key,self._key,[key,True])
            self.accept(key+'-up',self._key,[key,False])
        self.accept('escape',self.toggle_pause)
        self.accept('p',self.toggle_pause)
        self.accept('enter',self.enter)
        self.accept('r',self.restart_race)
        self.accept('c',self.cycle_camera)
        self.accept('m',self.toggle_audio)
        self.accept('f',self.recover_player)
        self.accept('window-event',self.window_event)
        self.taskMgr.add(self.update,'race-loop')
        self.camera.setPos(self.race.player.x+10,self.race.player.y-15,10)

    def label(self, parent, text, x, z, scale=.04, color=TEXT, align=TextNode.ALeft):
        return OnscreenText(parent=parent,text=text,pos=(x,z),scale=scale,
            fg=color,align=align,mayChange=True,shadow=(1,1,1,.12))

    def panel(self,parent,frame,color=PANEL):
        return DirectFrame(parent=parent,frameSize=frame,frameColor=color)

    def button(self,parent,text,x,z,command,width=.66,primary=False):
        return DirectButton(parent=parent,text=text,pos=(x,0,z),scale=1,
            frameSize=(-width/2,width/2,-.058,.058),
            frameColor=ORANGE if primary else (.80,.92,.91,1),
            text_fg=(.04,.06,.075,1) if primary else TEXT,
            text_scale=.035,text_pos=(0,-.012),relief=1,command=command,
            rolloverSound=None,clickSound=None)

    def _build_ui(self):
        self.ui=self.aspect2d.attachNewNode('responsive-ui')
        self.ui.setScale(min(1,self.getAspectRatio()/1.78))
        self.hud=self.ui.attachNewNode('hud')
        self.panel(self.hud,(-1.64,1.64,.77,.94))
        self.label(self.hud,'SKETCH / RACER',-1.58,.835,.048)
        self.label(self.hud,'SEOUL CITY RUN',-.92,.84,.025,CYAN)
        self.lap_label=self.label(self.hud,'LAP  01 / 03',-.3,.83,.043)
        self.time_label=self.label(self.hud,'00:00.00',.24,.83,.043)
        self.button(self.hud,'PAUSE [P]',1.34,.85,self.toggle_pause,.48)
        self.reset_button=self.button(self.hud,'RESET [F]',.79,.85,self.recover_player,.48)
        self.panel(self.hud,(-.96,.87,-.9,-.73))
        self.panel(self.hud,(-1.64,1.64,-.99,-.925))
        self.panel(self.hud,(-1.64,-1.03,-.64,.67))
        self.label(self.hud,'LIVE STANDINGS',-1.57,.57,.03,CYAN)
        self.rank_labels=[]
        for i in range(5):
            self.rank_labels.append(self.label(self.hud,'',-1.57,.44-i*.092,.031))
        self.label(self.hud,'CIRCUIT MAP',-1.57,-.15,.025,MUTED)
        self.map_root=self.hud.attachNewNode('minimap')
        self.map_root.setPos(-1.34,0,-.4)
        map_points=[(x*.0021,0,y*.0021) for x,y in self.race.track.points]
        lines(self.map_root,map_points+[map_points[0]],(.25,.4,.47,1),3)
        self.dots=[]
        for car in self.race.cars:
            self.dots.append(self.label(self.map_root,'o',0,0,.035,car.color,TextNode.ACenter))
        self.panel(self.hud,(.93,1.64,-.83,-.24))
        self.speed_label=self.label(self.hud,'000',1.56,-.47,.155,TEXT,TextNode.ARight)
        self.label(self.hud,'KM/H',1.57,-.54,.026,MUTED,TextNode.ARight)
        self.label(self.hud,'NITRO  /  SHIFT',1,-.61,.022,CYAN)
        self.nitro=DirectWaitBar(parent=self.hud,range=100,value=100,
            pos=(1.28,0,-.65),frameSize=(-.28,.28,-.017,.017),
            frameColor=(.72,.83,.83,1),barColor=CYAN,relief=0)
        self.label(self.hud,'INTEGRITY',1,-.72,.022,MUTED)
        self.health=DirectWaitBar(parent=self.hud,range=100,value=100,
            pos=(1.28,0,-.76),frameSize=(-.28,.28,-.017,.017),
            frameColor=(.72,.83,.83,1),barColor=ORANGE,relief=0)
        self.score_label=self.label(self.hud,'SCORE  00000',-.88,-.79,.037)
        self.gate_label=self.label(self.hud,'NEXT CP  01 / 08',-.88,-.86,.025,CYAN)
        self.laptime_label=self.label(self.hud,'LAP --:--.--',.02,-.79,.027,MUTED)
        self.best_label=self.label(self.hud,'BEST --:--.--',.02,-.85,.027,MUTED)
        self.label(self.hud,'WASD / ARROWS  DRIVE     SPACE  DRIFT     SHIFT  NITRO     C  CAMERA     F  RESET     M  AUDIO',0,-.955,.023,MUTED,TextNode.ACenter)
        self.toast=self.label(self.ui,'',0,.54,.065,CYAN,TextNode.ACenter)
        self.counter=self.label(self.ui,'',0,.03,.24,ORANGE,TextNode.ACenter)
        self.wrong_way_banner=self.ui.attachNewNode('wrong-way-warning')
        self.panel(self.wrong_way_banner,(-.43,.43,.61,.725),(1,.91,.68,.98))
        self.label(self.wrong_way_banner,'WRONG WAY',0,.65,.051,(.73,.19,.06,1),TextNode.ACenter)
        self.wrong_way_banner.hide()

        self.menu=self.ui.attachNewNode('menu')
        self.panel(self.menu,(-1.72,-.25,-.91,.94),(.96,.985,.96,.97))
        self.label(self.menu,'S T U D I O   /   0 1',-1.58,.77,.03,CYAN)
        self.label(self.menu,'SKETCH',-1.59,.51,.18)
        self.label(self.menu,'RACER.',-1.59,.29,.18,ORANGE)
        self.label(self.menu,'YOUR DRAWING. FULL THROTTLE.',-1.57,.13,.032)
        self.label(self.menu,'SEOUL CITY RUN  /  SUNNY DAY',-1.57,-.02,.027,CYAN)
        self.label(self.menu,'3 laps. 4 rivals. One finish line.\nHit every checkpoint in order.\nFind the boost pads. Own the corners.',-1.57,-.14,.034,MUTED)
        self.button(self.menu,'START RACE   /   ENTER',-.98,-.43,self.start,1.15,True)
        self.label(self.menu,'WASD / ARROWS   Drive & brake\nSHIFT   Nitro      SPACE   Drift\nP / ESC   Pause      R   Restart\nC   Camera      F   Reset      M   Audio',-1.57,-.60,.03,MUTED)
        self.label(self.menu,'01  /  SKETCH-BUILT PICKUP',.05,-.76,.04)
        self.label(self.menu,'A handwritten silhouette, reimagined in 3D.',.05,-.83,.028,MUTED)

        self.overlay=self.ui.attachNewNode('pause-results')
        self.panel(self.overlay,(-1.05,1.05,-.69,.69),(.96,.985,.96,.98))
        self.overlay_title=self.label(self.overlay,'PAUSED',0,.43,.105,TEXT,TextNode.ACenter)
        self.overlay_sub=self.label(self.overlay,'',0,.28,.031,CYAN,TextNode.ACenter)
        self.overlay_body=self.label(self.overlay,'',0,.02,.043,TEXT,TextNode.ACenter)
        self.primary=self.button(self.overlay,'RESUME',-.36,-.40,self.enter,.62,True)
        self.button(self.overlay,'RESTART',.36,-.40,self.restart_race,.62)
        self.button(self.overlay,'MAIN MENU',0,-.57,self.main_menu,.62)
        self.overlay.hide()

    def window_event(self, window):
        if not window or not hasattr(window,'getProperties'):
            return
        props=window.getProperties()
        aspect=max(.5,props.getXSize()/max(1,props.getYSize()))
        self.ui.setScale(min(1,aspect/1.78))
        if not props.getForeground() and self.race.state in ('racing','countdown'):
            self.keys.clear()
            self.race.pause()

    def _key(self,key,down):
        self.keys[key]=down

    def controls(self):
        key=lambda *names: any(self.keys.get(n,False) for n in names)
        return Control(float(key('w','arrow_up')),float(key('s','arrow_down')),
            float(key('a','arrow_left'))-float(key('d','arrow_right')),
            key('shift'),key('space'))

    def start(self):
        self.race.reset()
        self.saved=False
        self.keys.clear()
        self.accumulator=0

    def recover_player(self):
        if not self.race.recover():
            return
        self.keys.clear()
        self.accumulator=0
        c=self.race.player
        node, wheels, _=self.car_nodes[0]
        node.setPos(c.x,c.y,0)
        node.setHpr(math.degrees(c.heading)-90,0,0)
        for wheel in wheels:
            wheel.setP(0)
        # Snap the camera too: interpolating from an off-road/turned-over pose is disorienting.
        desired,target=self.driving_camera_pose()
        self.camera.setPos(desired)
        self.camera.lookAt(target)
        self.camLens.setFov(68)
        self.wrong_way_banner.hide()

    def driving_camera_pose(self):
        c=self.race.player
        fx,fy=math.cos(c.heading),math.sin(c.heading)
        back,height=[(11.5,5.8),(6.1,3.2),(20,16)][self.camera_mode]
        back+=c.speed*.06
        return (Vec3(c.x-fx*back,c.y-fy*back,height),
                Vec3(c.x+fx*(5+c.speed*.1),c.y+fy*(5+c.speed*.1),1.1))

    def restart_race(self):
        self.start()

    def enter(self):
        if self.race.state=='paused':
            self.toggle_pause()
        elif self.race.state in ('menu','finished','gameover'):
            self.start()

    def main_menu(self):
        self.race.reset('menu')
        self.keys.clear()

    def toggle_pause(self):
        self.keys.clear()
        self.race.pause()

    def toggle_audio(self):
        self.audio.muted=not self.audio.muted

    def cycle_camera(self):
        self.camera_mode=(self.camera_mode+1)%3

    def save_records(self):
        if self.saved:
            return
        c=self.race.player
        if c.lap_times:
            best=min(c.lap_times)
            self.records['best_lap']=min(best,self.records.get('best_lap',best))
        self.records['best_score']=max(int(c.score),self.records.get('best_score',0))
        try:
            self.record_path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.record_path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.records,indent=2))
            temp.replace(self.record_path)
        except OSError:
            self.toast.setText('Record could not be saved')
            self.toast_t=3
        self.saved=True

    def sync_ui(self):
        race=self.race
        c=race.player
        state=race.state
        if c.wrong_way and state=='racing':
            self.wrong_way_banner.show()
        else:
            self.wrong_way_banner.hide()
        if state != self.last_state:
            self.menu.hide()
            self.overlay.hide()
            self.hud.hide()
            if state=='menu':
                self.menu.show()
            else:
                self.hud.show()
            if state in ('paused','finished','gameover'):
                self.overlay.show()
                self.overlay_title.setText({'paused':'PAUSED','finished':'FINISH LINE.','gameover':'RACE OVER.'}[state])
                self.primary['text']='RESUME' if state=='paused' else 'RACE AGAIN'
                if state=='paused':
                    self.overlay_sub.setText('TAKE A BREATH. YOUR RACE IS WAITING.')
                    self.overlay_body.setText('P / ESC to resume\nC to change camera\nM to toggle sound')
                else:
                    place=race.standings().index(c)+1
                    self.overlay_sub.setText(f'POSITION  {place} / 5' if state=='finished' else ('INTEGRITY DEPLETED' if c.health<=0 else 'TIME LIMIT REACHED'))
                    laps='   /   '.join(time_text(t) for t in c.lap_times) or '--:--.--'
                    self.overlay_body.setText(f'TIME  {time_text(race.elapsed)}    SCORE  {int(c.score):05d}\n\nLAPS  {laps}')
                    if not self.smoke:
                        self.save_records()
            self.last_state=state
        self.counter.setText(str(max(1,math.ceil(race.countdown))) if state=='countdown' else '')
        self.lap_label.setText(f'LAP  {min(3,c.laps+1):02d} / 03')
        self.time_label.setText(time_text(race.elapsed))
        self.speed_label.setText(f'{c.speed*3.6:03.0f}')
        self.nitro['value']=c.energy
        self.health['value']=c.health
        self.score_label.setText(f'SCORE  {int(c.score):05d}')
        self.gate_label.setText(f'NEXT CP  {(c.next_gate-1)%8+1:02d} / 08   |   LIMIT {max(0,int(TIME_LIMIT-race.elapsed))}s')
        self.laptime_label.setText('LAP  '+time_text(race.elapsed-c.lap_start))
        best=min(c.lap_times) if c.lap_times else self.records.get('best_lap')
        self.best_label.setText('BEST  '+(time_text(best) if best is not None else '--:--.--'))
        for i,car in enumerate(race.standings()):
            self.rank_labels[i].setText(f'{i+1:02d}  {car.name:5s}'+('  FIN' if car.finished else f'  L{min(3,car.laps+1)}'))
            self.rank_labels[i].setFg(ORANGE if car is c else MUTED)
        for dot,car in zip(self.dots,race.cars):
            dot.setPos(car.x*.0021,car.y*.0021-.01)

    def update(self, task):
        real_dt=min(.10,ClockObject.getGlobalClock().getDt())
        dt=1/60 if self.smoke else real_dt
        self.visual_time+=dt
        self.frames+=1
        self.accumulator+=dt
        if self.smoke and self.frames==3:
            self.start()
            self.race.countdown=.01
        u=self.race.ai_control(self.race.player) if self.smoke else self.controls()
        while self.accumulator >= DT:
            self.race.step(u,DT)
            self.accumulator-=DT
        for car,(node,wheels,flames) in zip(self.race.cars,self.car_nodes):
            node.setPos(car.x,car.y,0)
            # The root is the physics center. Keep it level and rotate only about its center.
            node.setHpr(math.degrees(car.heading)-90,0,0)
            for wheel in wheels:
                wheel.setP(wheel.getP()-car.speed*dt*78)
            for flame in flames:
                flame.show() if car.boosted and self.race.state=='racing' else flame.hide()
        c=self.race.player
        if self.race.state=='menu':
            t=self.visual_time*.13
            desired=Vec3(c.x+math.cos(t)*11,c.y+math.sin(t)*11,5.6)
            target=Vec3(c.x,c.y,1)
        else:
            desired,target=self.driving_camera_pose()
            if c.hit_cooldown>.45 and self.race.state=='racing':
                desired.x+=math.sin(self.visual_time*85)*.12
                desired.z+=math.cos(self.visual_time*75)*.09
        self.camera.setPos(self.camera.getPos()+(desired-self.camera.getPos())*min(1,dt*5))
        self.camera.lookAt(target)
        fov=68+min(9,c.speed*.15)+(6 if c.boosted else 0)
        self.camLens.setFov(self.camLens.getHfov()+(fov-self.camLens.getHfov())*min(1,dt*3))
        while self.race.events:
            event=self.race.events.pop(0)
            self.audio.play(event)
            self.toast.setText(event)
            self.toast_t=1.6
        self.toast_t=max(0,self.toast_t-dt)
        if self.toast_t<=0:
            self.toast.setText('')
        self.audio.update(c.speed,self.race.state=='racing')
        self.sync_ui()
        if self.smoke and self.frames>=360:
            if self.screenshot:
                self.graphicsEngine.renderFrame()
                self.win.saveScreenshot(str(Path(self.screenshot).resolve()))
            print(json.dumps({'smoke':'passed','frames':self.frames,'state':self.race.state,
                'speed_kmh':round(c.speed*3.6,1),'position':[c.x,c.y],
                'cars':len(self.car_nodes),'health':c.health}))
            self.userExit()
            return task.done
        return task.cont
