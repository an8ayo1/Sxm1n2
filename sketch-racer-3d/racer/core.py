"""Deterministic planar vehicle dynamics, independent of the renderer.

SI units. Fixed 120 Hz integration; bicycle yaw, lateral tire damping,
quadratic drag, impulse collisions. This is an arcade handling model,
not a full suspension or motorsport simulator.
"""
from dataclasses import dataclass, field
import math

TAU = math.tau
DT = 1 / 120
LAPS = 3
TIME_LIMIT = 240.0


def clamp(x, a, b):
    return max(a, min(b, x))


def angle_diff(a, b):
    return (a - b + math.pi) % TAU - math.pi


@dataclass
class Control:
    throttle: float = 0
    brake: float = 0
    steer: float = 0  # positive is left
    boost: bool = False
    drift: bool = False


class Track:
    width = 19.0

    def __init__(self):
        self.points = []
        for i in range(360):
            t = i / 360 * TAU
            r = 83 + 14 * math.sin(3*t) + 7 * math.cos(2*t)
            self.points.append((r * math.cos(t), r * math.sin(t)))
        self.lengths = [0.0]
        for i, (x, y) in enumerate(self.points):
            xx, yy = self.points[(i+1) % len(self.points)]
            self.lengths.append(self.lengths[-1] + math.hypot(xx-x, yy-y))
        self.length = self.lengths[-1]

    def at(self, distance, offset=0):
        import bisect
        s = distance % self.length
        i = min(359, bisect.bisect_right(self.lengths, s)-1)
        x, y = self.points[i]
        xx, yy = self.points[(i+1) % 360]
        dx, dy = xx-x, yy-y
        length = self.lengths[i+1] - self.lengths[i]
        f = (s-self.lengths[i])/length
        return (x+dx*f-dy/length*offset, y+dy*f+dx/length*offset,
                math.atan2(dy, dx))

    def project(self, x, y):
        best = (float('inf'), 0, 0, 0, 0, 0)
        for i, (ax, ay) in enumerate(self.points):
            bx, by = self.points[(i+1) % 360]
            dx, dy = bx-ax, by-ay
            d2 = dx*dx+dy*dy
            f = clamp(((x-ax)*dx+(y-ay)*dy)/d2, 0, 1)
            px, py = ax+f*dx, ay+f*dy
            sq = (x-px)**2+(y-py)**2
            if sq < best[0]:
                norm = math.sqrt(d2)
                best = (sq, self.lengths[i]+f*norm,
                        ((x-px)*-dy+(y-py)*dx)/norm,
                        math.atan2(dy, dx), px, py)
        return best[1:]


@dataclass
class Car:
    name: str
    color: tuple
    x: float
    y: float
    heading: float
    vx: float = 0
    vy: float = 0
    progress: float = 0
    track_s: float = 0
    next_gate: int = 1
    laps: int = 0
    lap_start: float = 0
    lap_times: list = field(default_factory=list)
    energy: float = 100
    health: float = 100
    score: float = 0
    hit_cooldown: float = 0
    boost_pad_cooldown: float = 0
    pad_boost: float = 0
    boosted: bool = False
    finished: bool = False
    finish_time: float = 0
    steer: float = 0
    lane: float = 0
    target_speed: float = 30

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)


class Race:
    def __init__(self):
        self.track = Track()
        self.state = 'menu'
        self.elapsed = 0.0
        self.countdown = 3.0
        self.events = []
        self.cars = []
        self.obstacles = []
        self.pads = []
        for s, lane, radius, kind in [(75, 4, 1.25, 'barrel'),
                (152, -4, 1.6, 'crate'), (251, 3, 1.35, 'barrel'),
                (354, -4, 1.6, 'crate'), (433, 4, 1.1, 'cone'),
                (490, -3, 1.1, 'cone')]:
            x, y, _ = self.track.at(s, lane)
            self.obstacles.append((x, y, radius, kind, s, lane))
        for s, lane in [(112, 0), (290, -2), (465, 1)]:
            self.pads.append((*self.track.at(s, lane), s))
        self.reset('menu')

    @property
    def player(self):
        return self.cars[0]

    def reset(self, state='countdown'):
        self.state, self.elapsed, self.countdown = state, 0.0, 3.0
        self.events = []
        self.cars = []
        for i, (name, color) in enumerate([
            ('YOU', (1, .37, .12, 1)), ('NOVA', (.14, .85, .96, 1)),
            ('GHOST', (.8, .73, 1, 1)), ('EMBER', (1, .75, .18, 1)),
            ('JADE', (.26, .95, .58, 1))]):
            s = -i*6
            lane = -2.5 if i % 2 else 2.5
            x, y, h = self.track.at(s, lane)
            self.cars.append(Car(name, color, x, y, h,
                progress=s, track_s=s % self.track.length,
                lane=lane, target_speed=29.5+i*.7))

    def pause(self):
        if self.state in ('racing', 'countdown'):
            self.resume_state = self.state
            self.state = 'paused'
        elif self.state == 'paused':
            self.state = self.resume_state

    def recover(self):
        if self.state != 'racing':
            return
        c = self.player
        c.x, c.y, c.heading = self.track.at(c.track_s)
        c.vx = c.vy = 0
        c.score = max(0, c.score-100)
        c.health = max(1, c.health-4)
        self.events.append('RECOVERED  -100')

    def standings(self):
        return sorted(self.cars, key=lambda c: (
            1 if c.finished else 0,
            -c.finish_time if c.finished else c.progress), reverse=True)

    def ai_control(self, c):
        look = 9 + c.speed * .48
        lane = c.lane
        for ox, oy, radius, kind, s, offset in self.obstacles:
            ahead = (s-c.track_s) % self.track.length
            if ahead < 30 and abs(lane-offset) < radius+2:
                lane = -3.2 if offset > 0 else 3.2
        x, y, tangent = self.track.at(c.track_s+look, lane)
        aim = math.atan2(y-c.y, x-c.x)
        error = angle_diff(aim, c.heading)
        target = c.target_speed * (1 - min(.42, abs(error)*.45))
        steer = clamp(error*2.5, -1, 1)
        return Control(throttle=1 if c.speed < target else .15,
                       brake=.35 if c.speed > target+2 else 0,
                       steer=steer, boost=False)

    def step(self, control, dt=DT):
        if self.state == 'countdown':
            self.countdown -= dt
            if self.countdown <= 0:
                self.state = 'racing'
                self.events.append('GO!')
            return
        if self.state != 'racing':
            return
        self.elapsed += dt
        for i, car in enumerate(self.cars):
            if not car.finished:
                self._drive(car, control if i == 0 else self.ai_control(car), dt)
        self._car_collisions()
        if self.player.health <= 0 or self.elapsed >= TIME_LIMIT:
            self.state = 'gameover'
            self.events.append('CAR WRECKED' if self.player.health <= 0 else 'TIME UP')
        elif self.player.finished:
            self.state = 'finished'

    def _impact(self, c, severity):
        if c.hit_cooldown <= 0:
            c.health = max(0, c.health-min(16, max(2, severity*.48)))
            c.score = max(0, c.score-40)
            c.hit_cooldown = .65
            if c is self.player:
                self.events.append('IMPACT')

    def _drive(self, c, u, dt):
        c.hit_cooldown = max(0, c.hit_cooldown-dt)
        c.boost_pad_cooldown = max(0, c.boost_pad_cooldown-dt)
        c.pad_boost = max(0, c.pad_boost-dt)
        c.steer += (clamp(u.steer, -1, 1)-c.steer)*min(1, dt*9)
        forward_x, forward_y = math.cos(c.heading), math.sin(c.heading)
        longitudinal = c.vx*forward_x+c.vy*forward_y
        lateral = -c.vx*forward_y+c.vy*forward_x
        c.boosted = (u.boost and c.energy > 0 and u.throttle > 0) or c.pad_boost > 0
        if u.boost and c.energy > 0 and u.throttle > 0:
            c.energy = max(0, c.energy-25*dt)
        else:
            c.energy = min(100, c.energy+9*dt)
        engine = clamp(u.throttle, 0, 1)*(23 if c.boosted else 14)
        drag = .28*longitudinal+.006*longitudinal*abs(longitudinal)
        brake = clamp(u.brake, 0, 1)*32
        longitudinal = max(0, longitudinal+(engine-drag-brake)*dt)
        longitudinal = min(61 if c.boosted else 46, longitudinal)
        lateral *= math.exp(-(2.1 if u.drift else 8)*dt)
        yaw = longitudinal/3.3*math.tan(c.steer*.42)/(1+longitudinal*.065)
        c.heading += yaw*dt
        # Keep momentum in world space as the body turns; tires pull it toward heading.
        c.vx = forward_x*longitudinal-forward_y*lateral
        c.vy = forward_y*longitudinal+forward_x*lateral
        c.x += c.vx*dt
        c.y += c.vy*dt
        s, offset, tangent, px, py = self.track.project(c.x, c.y)
        border = self.track.width/2-1.2
        if abs(offset) > border:
            sign = 1 if offset > 0 else -1
            nx, ny = -math.sin(tangent)*sign, math.cos(tangent)*sign
            c.x -= nx*(abs(offset)-border)
            c.y -= ny*(abs(offset)-border)
            outward = c.vx*nx+c.vy*ny
            if outward > 0:
                c.vx -= 1.35*outward*nx
                c.vy -= 1.35*outward*ny
                self._impact(c, outward)
            c.vx *= .985
            c.vy *= .985
        for ox, oy, radius, kind, _, _ in self.obstacles:
            self._solid_collision(c, ox, oy, radius)
        for x, y, h, _ in self.pads:
            if math.hypot(c.x-x, c.y-y) < 3.2 and c.boost_pad_cooldown <= 0:
                c.pad_boost, c.boost_pad_cooldown = 1.5, 3
                c.energy = min(100, c.energy+28)
                c.score += 150
                if c is self.player:
                    self.events.append('BOOST PAD  +150')
        ds = (s-c.track_s+self.track.length/2) % self.track.length-self.track.length/2
        # Only physically plausible, on-road forward crossings can earn gates.
        if abs(ds) < max(2, c.speed*dt*3):
            c.progress += ds
        c.track_s = s
        target = c.next_gate*self.track.length/8
        if c.progress >= target and abs(offset) < self.track.width/2:
            c.next_gate += 1
            c.score += 300
            if c is self.player:
                self.events.append('CHECKPOINT  +300')
            if (c.next_gate-1) % 8 == 0:
                c.laps += 1
                c.lap_times.append(self.elapsed-c.lap_start)
                c.lap_start = self.elapsed
                c.health = min(100, c.health+12)
                if c.laps == LAPS:
                    c.finished, c.finish_time = True, self.elapsed
                    c.score += 1500+int(c.health*10)
        c.score += max(0, ds)*.8

    def _solid_collision(self, c, x, y, radius):
        dx, dy = c.x-x, c.y-y
        distance = math.hypot(dx, dy)
        minimum = radius+1.15
        if distance < minimum:
            nx, ny = (dx/distance, dy/distance) if distance > .0001 else (1, 0)
            c.x, c.y = x+nx*minimum, y+ny*minimum
            inward = c.vx*nx+c.vy*ny
            if inward < 0:
                self._impact(c, -inward)
                c.vx -= 1.4*inward*nx
                c.vy -= 1.4*inward*ny

    def _car_collisions(self):
        for i, a in enumerate(self.cars):
            for b in self.cars[i+1:]:
                if a.finished or b.finished:
                    continue
                dx, dy = a.x-b.x, a.y-b.y
                distance = math.hypot(dx, dy)
                if distance < 2.5:
                    nx, ny = (dx/distance, dy/distance) if distance > .0001 else (1, 0)
                    push = (2.5-distance)/2
                    a.x += nx*push
                    a.y += ny*push
                    b.x -= nx*push
                    b.y -= ny*push
                    relative = (a.vx-b.vx)*nx+(a.vy-b.vy)*ny
                    if relative < 0:
                        impulse = -.65*relative
                        a.vx += impulse*nx
                        a.vy += impulse*ny
                        b.vx -= impulse*nx
                        b.vy -= impulse*ny
                        self._impact(a, -relative)
                        self._impact(b, -relative)
