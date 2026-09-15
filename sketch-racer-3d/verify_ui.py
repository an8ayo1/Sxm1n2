"""Opt-in graphical keyboard/menu regression check; opens a real game window."""
from pathlib import Path
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

    tick(50)
    assert not game.menu.isHidden()
    game.win.saveScreenshot(str((output/'start.png').resolve()))
    game.messenger.send('enter')
    game.race.countdown=.01
    tick(2)
    game.smoke=False  # Use keyboard input instead of AI control.
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
    print('UI CHECK PASSED: keyboard acceleration/brake/steering/boost, pause/resume, camera, gameover, restart, finish, menu')
    game.destroy()


if __name__=='__main__':
    main()
