import math
import unittest
from racer.core import Race, Control, DT, TIME_LIMIT


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
        c.x,c.y,c.heading=r.track.at(20,9.4)
        c.vx=-math.sin(c.heading)*20
        c.vy=math.cos(c.heading)*20
        r._drive(c,Control(),DT)
        self.assertLess(c.health,100)
        self.assertLess(abs(r.track.project(c.x,c.y)[1]),8.5)
        c.hit_cooldown=0
        c.x,c.y,c.vx,c.vy=1,0,-15,0
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
        r._car_collisions()
        self.assertAlmostEqual(math.hypot(a.x-b.x,a.y-b.y),2.5)
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
