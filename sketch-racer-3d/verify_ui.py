"""Opt-in graphical keyboard/menu regression check; opens a real game window."""
from pathlib import Path
import math
from panda3d.core import ClockObject
from racer.app import Game


def main():
    game=Game(smoke=True)
    game.taskMgr.remove('race-loop')
    game.frames=10  # Disable smoke auto-start; this check drives the actual input handlers.
    output=Path('test-results')
    output.mkdir(exist_ok=True)
    clock=ClockObject.getGlobalClock()
    clock.setMode(ClockObject.MNonRealTime)
    clock.setDt(1/60)

    class Task:
        cont=1
        done=0

    def tick(count=1):
        for _ in range(count):
            game.frames=10  # Keep the smoke exit threshold disabled.
            game.update(Task())
            game.graphicsEngine.renderFrame()

    # Every visual wheel has a centered tire and an exactly mirrored opposite wheel.
    root,wheels,_=game.car_nodes[0]
    for left,right in zip(wheels[:2],wheels[2:]):
        lo,hi=left.getTightBounds(root)
        rlo,rhi=right.getTightBounds(root)
        assert abs(lo.x+rhi.x)<1e-5 and abs(hi.x+rlo.x)<1e-5
    tick(50)
    assert not game.menu.isHidden()
    game.win.saveScreenshot(str((output/'start.png').resolve()))
    game.messenger.send('enter')
    game.race.countdown=.01
    tick(2)
    game.smoke=False  # Use keyboard input instead of AI control.
    # Leave room behind the player: a legitimate AI rear-end impulse must not
    # be mistaken for a failed brake-input test with the new full-length boxes.
    c=game.race.player
    c.x,c.y,c.heading=game.race.track.at(60)
    c.track_s=c.progress=60
    game.messenger.send('w')
    tick(45)
    assert game.race.player.speed>5
    game.messenger.send('w-up')
    game.messenger.send('s')
    tick(40)
    assert game.race.player.speed<.1
    game.messenger.send('s-up')
    game.messenger.send('arrow_up')
    game.messenger.send('arrow_left')
    tick(25)
    assert game.controls().throttle==1 and game.controls().steer==1
    game.messenger.send('arrow_left-up')
    game.messenger.send('arrow_right')
    assert game.controls().steer==-1
    game.messenger.send('arrow_right-up')
    game.messenger.send('shift')
    tick(4)
    assert game.race.player.boosted
    game.messenger.send('shift-up')
    game.messenger.send('arrow_up-up')
    game.messenger.send('p')
    frozen=game.race.elapsed
    tick(10)
    assert game.race.state=='paused' and game.race.elapsed==frozen
    assert not game.overlay.isHidden()
    game.win.saveScreenshot(str((output/'paused.png').resolve()))
    game.messenger.send('escape')
    tick(2)
    assert game.race.state=='racing'
    game.messenger.send('c')
    assert game.camera_mode==1
    c=game.race.player
    # Isolate the direction timer from AI head-on impacts, which correctly
    # interrupt reverse travel and reset the warning delay.
    c.x,c.y,tangent=game.race.track.at(330)
    c.track_s=330
    c.steer=0
    c.heading=tangent+math.pi
    c.vx,c.vy=-math.cos(tangent)*6,-math.sin(tangent)*6
    game.messenger.send('w')
    tick(45)
    assert game.wrong_way_banner.isHidden()
    tick(22)
    assert not game.wrong_way_banner.isHidden(), (c.wrong_way_time,c.speed,game.race.state,c.heading,game.race.track.project(c.x,c.y)[2],game.keys)
    game.win.saveScreenshot(str((output/'wrong-way.png').resolve()))
    c.heading=game.race.track.project(c.x,c.y)[2]
    tick(1)
    assert game.wrong_way_banner.isHidden()
    game.messenger.send('w-up')
    # Activate the very same command used by the on-screen Reset button.
    c.x,c.y,c.heading=game.race.track.at(200,20)
    root.setHpr(90,180,45)
    game.camera.setPos(500,500,100)
    game.reset_button['command']()
    assert c.speed==0 and abs(game.race.track.project(c.x,c.y)[1])<.001
    assert root.getP()==0 and root.getR()==0
    desired,_=game.driving_camera_pose()
    assert (game.camera.getPos()-desired).length()<.001
    game.messenger.send('f')
    assert c.speed==0
    game.smoke=True  # Do not write test records to the user's save file.
    game.race.player.health=0
    tick(2)
    assert game.race.state=='gameover'
    game.win.saveScreenshot(str((output/'gameover.png').resolve()))
    game.messenger.send('r')
    assert game.race.player.health==100 and game.race.state=='countdown'
    game.race.countdown=.001
    tick(2)
    game.race.player.finished=True
    game.race.player.laps=3
    game.race.player.lap_times=[23.5,24.6,22.9]
    tick(2)
    assert game.race.state=='finished' and not game.overlay.isHidden()
    game.win.saveScreenshot(str((output/'finish.png').resolve()))
    game.messenger.send('enter')
    assert game.race.state=='countdown'
    game.main_menu()
    tick(2)
    assert not game.menu.isHidden()
    print('UI CHECK PASSED: keyboard acceleration/brake/steering/boost, pause/resume, camera, gameover, restart, finish, menu, wrong-way, respawn, symmetry')
    game.destroy()


if __name__=='__main__':
    main()
