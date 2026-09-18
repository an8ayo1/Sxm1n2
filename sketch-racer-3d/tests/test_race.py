import math
import unittest
from racer.core import Race, Control, DT, TIME_LIMIT, CAR_HALF_WIDTH, CAR_HALF_LENGTH


class RaceTests(unittest.TestCase):
    def race(self):
        r=Race()
        r.reset('racing')
        return r

    def test_acceleration_brake_and_left_right(self):
        r=self.race()
        c=r.player
        for _ in range(100):
            r._drive(c,Control(throttle=1),DT)
        speed=c.speed
        self.assertGreater(speed,8)
        for _ in range(50):
            r._drive(c,Control(brake=1),DT)
        self.assertLess(c.speed,speed*.3)
        for steer in (-1,1):
            r=self.race()
            c=r.player
            h=c.heading
            c.vx,c.vy=math.cos(h)*15,math.sin(h)*15
            for _ in range(15):
                r._drive(c,Control(steer=steer),DT)
            self.assertGreater((c.heading-h)*steer,0)

    def test_boost_energy_and_pad(self):
        r=self.race()
        c=r.player
        r._drive(c,Control(throttle=1,boost=True),DT)
        self.assertTrue(c.boosted)
        self.assertLess(c.energy,100)
        x,y,h,s=r.pads[0]
        c.x,c.y,c.heading,c.track_s=x,y,h,s
        r._drive(c,Control(),DT)
        self.assertGreater(c.pad_boost,1)
        self.assertIn('BOOST PAD  +150',r.events)

    def test_barrier_and_obstacle_collision(self):
        r=self.race()
        c=r.player
        c.x,c.y,c.heading=r.track.at(20,r.track.width/2-.2)
        c.vx=-math.sin(c.heading)*20
        c.vy=math.cos(c.heading)*20
        r._drive(c,Control(),DT)
        self.assertLess(c.health,100)
        self.assertLess(abs(r.track.project(c.x,c.y)[1]),r.track.width/2-CAR_HALF_WIDTH+.02)
        c.hit_cooldown=0
        c.x,c.y,c.vx,c.vy=1,0,-15,0
        c.heading=math.pi/2
        before=c.health
        r._solid_collision(c,0,0,1.5)
        self.assertGreaterEqual(c.x,2.65)
        self.assertGreater(c.vx,0)
        self.assertLess(c.health,before)

    def test_car_collision_separates_and_transfers_momentum(self):
        r=self.race()
        a,b=r.cars[:2]
        a.x,a.y,b.x,b.y=0,0,2,0
        a.vx,b.vx=20,0
        a.heading=b.heading=math.pi/2
        r._car_collisions()
        self.assertAlmostEqual(math.hypot(a.x-b.x,a.y-b.y),2*CAR_HALF_WIDTH,places=3)
        self.assertGreater(b.vx,0)
        self.assertLess(a.vx,20)

    def test_pause_countdown_and_reset(self):
        r=Race()
        r.reset()
        r.step(Control(throttle=1))
        self.assertEqual(r.player.speed,0)
        r.pause()
        snapshot=(r.countdown,r.elapsed,r.player.x)
        for _ in range(60):
            r.step(Control(throttle=1))
        self.assertEqual(snapshot,(r.countdown,r.elapsed,r.player.x))
        r.pause()
        self.assertEqual(r.state,'countdown')
        r.player.health=0
        r.reset()
        self.assertEqual(r.player.health,100)
        self.assertEqual(r.player.laps,0)

    def test_wrong_way_and_teleport_do_not_award_laps(self):
        r=self.race()
        c=r.player
        c.x,c.y,c.heading=r.track.at(r.track.length*.95)
        r._drive(c,Control(),DT)
        self.assertEqual(c.next_gate,1)
        self.assertEqual(c.laps,0)
        self.assertLess(c.progress,2)
        c.track_s=0
        c.x,c.y,c.heading=r.track.at(-.5)
        r._drive(c,Control(),DT)
        self.assertLess(c.progress,0)
        self.assertEqual(c.laps,0)

    def test_gameover_and_recover(self):
        r=self.race()
        r.player.score=200
        r.recover()
        self.assertEqual(r.player.score,100)
        r.player.health=0
        r.step(Control())
        self.assertEqual(r.state,'gameover')
        r.reset('racing')
        r.elapsed=TIME_LIMIT
        r.step(Control())
        self.assertEqual(r.state,'gameover')

    def test_wrong_way_delay_and_immediate_clear(self):
        r=self.race()
        c=r.player
        c.x,c.y,tangent=r.track.at(50)
        c.track_s=50
        c.heading=tangent+math.pi
        c.vx,c.vy=-math.cos(tangent)*6,-math.sin(tangent)*6
        for _ in range(110):
            r._drive(c,Control(throttle=.4),DT)
        self.assertFalse(c.wrong_way)  # Brief turns must not warn.
        for _ in range(20):
            r._drive(c,Control(throttle=.4),DT)
        self.assertTrue(c.wrong_way)
        c.heading=r.track.project(c.x,c.y)[2]
        r._drive(c,Control(),DT)
        self.assertFalse(c.wrong_way)
        c.heading+=math.pi
        c.vx=c.vy=0
        for _ in range(150):
            r._drive(c,Control(),DT)
        self.assertFalse(c.wrong_way)  # Stopped facing backward is not reverse travel.

    def test_respawn_uses_nearest_road_and_clears_motion(self):
        r=self.race()
        c=r.player
        c.x,c.y,c.heading=r.track.at(210,18)
        c.heading+=math.pi
        c.track_s=0  # Deliberately stale cache, such as after an off-road displacement.
        c.progress=25
        expected_s=r.track.project(c.x,c.y)[0]
        expected=r.track.at(expected_s)
        c.vx,c.vy,c.steer,c.wrong_way_time,c.pad_boost=12,9,1,2,1.4
        c.boosted=True
        gates=c.next_gate
        self.assertTrue(r.recover())
        for actual,target in zip((c.x,c.y,c.heading),expected):
            self.assertAlmostEqual(actual,target)
        self.assertEqual(c.speed,0)
        self.assertEqual(c.steer,0)
        self.assertEqual(c.pad_boost,0)
        self.assertFalse(c.boosted or c.wrong_way)
        self.assertEqual((c.progress,c.next_gate),(25,gates))
        r.pause()
        self.assertTrue(r.recover())
        self.assertEqual(r.state,'paused')
        r.reset('menu')
        self.assertFalse(r.recover())

    def test_centered_box_catches_bumpers_and_mirrors_sides(self):
        r=self.race()
        c=r.player
        c.heading=0
        c.x=c.y=0
        c.vx=10
        r._solid_collision(c,CAR_HALF_LENGTH+.8,0,1)
        self.assertLess(c.x,0)  # Front bumper, previously missed by center-only circles.
        self.assertLess(c.vx,0)
        positions=[]
        for sign in (-1,1):
            c.x=c.y=0
            c.vx=0
            c.vy=sign*10
            r._solid_collision(c,0,sign*(CAR_HALF_WIDTH+.8),1)
            positions.append(c.y)
        self.assertAlmostEqual(positions[0],-positions[1])

    def test_slow_pad_reduces_speed_without_damage_or_repeated_hits(self):
        r=self.race()
        for c in (r.player,r.cars[1]):
            x,y,h,s=r.slow_pads[0]
            c.x,c.y,c.heading,c.track_s=x,y,h,s
            c.vx,c.vy=30*math.cos(h),30*math.sin(h)
            c.pad_boost=1
            health=c.health
            r._drive(c,Control(throttle=1,boost=True),DT)
            self.assertLess(c.speed,19)
            self.assertEqual(c.health,health)
            self.assertEqual(c.pad_slow,1.8)
            self.assertFalse(c.boosted)
            self.assertEqual(c.pad_boost,0)
            speed=c.speed
            energy=c.energy
            r._drive(c,Control(throttle=1,boost=True,steer=1),DT)
            self.assertGreater(c.speed,speed*.9)  # No repeated 40% multiplication.
            self.assertGreaterEqual(c.energy,energy)  # No wasted nitro while slowed.
            self.assertGreater(c.steer,0)
        self.assertEqual(r.events.count('SLOW PAD  /  GRIP ZONE'),1)

    def test_slow_pad_bounds_expiry_and_respawn(self):
        r=self.race()
        c=r.player
        x,y,h,s=r.slow_pads[0]
        c.x=x-math.sin(h)*2.8
        c.y=y+math.cos(h)*2.8
        c.heading=h
        r._drive(c,Control(),DT)
        self.assertEqual(c.pad_slow,0)  # Missing the visible pad must not slow a car.
        c.pad_slow=.01
        c.x,c.y,c.heading=r.track.at(10)
        for _ in range(3):
            r._drive(c,Control(throttle=1,boost=True),DT)
        self.assertEqual(c.pad_slow,0)
        self.assertTrue(c.boosted)
        c.pad_slow=1.8
        r.recover()
        self.assertEqual(c.pad_slow,0)
        r.reset()
        self.assertEqual(r.player.slow_pad_cooldown,0)

    def test_accelerating_and_boosting_can_turn_both_directions(self):
        for steer in (-1,1):
            r=self.race()
            r.track.width=200  # Isolate input response from barriers and scenery.
            r.obstacles=[]
            c=r.player
            original=c.heading
            c.vx,c.vy=35*math.cos(original),35*math.sin(original)
            for _ in range(40):
                r._drive(c,Control(throttle=1,boost=True,steer=steer),DT)
            self.assertGreater((c.heading-original)*steer,.1)
            self.assertGreater(c.speed,25)

    def test_complete_three_laps_with_real_controls(self):
        r=self.race()
        # Uses the same steering/throttle physics as keyboard input; no teleporting.
        for _ in range(120*150):
            r.step(r.ai_control(r.player))
            if r.state != 'racing':
                break
        self.assertEqual(r.state,'finished',[(c.name,c.progress,c.health) for c in r.cars])
        self.assertEqual(r.player.laps,3)
        self.assertEqual(len(r.player.lap_times),3)
        self.assertEqual(r.player.next_gate,25)
        self.assertTrue(all(t>10 for t in r.player.lap_times))
        self.assertGreater(r.player.score,8000)
        self.assertTrue(all(c.progress>r.track.length for c in r.cars[1:]))
        self.assertEqual(r.standings()[0],r.player)


if __name__=='__main__':
    unittest.main()
