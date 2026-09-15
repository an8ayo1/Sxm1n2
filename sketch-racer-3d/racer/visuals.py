"""Original procedural geometry: no downloaded art or model dependencies."""
import math
import random
from panda3d.core import (GeomVertexData, GeomVertexFormat, GeomVertexWriter,
    GeomTriangles, Geom, GeomNode, Vec3, LineSegs, TextNode)


def mesh(parent, name, faces, color):
    data = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
    vertex, normal, colors = (GeomVertexWriter(data, key) for key in ('vertex', 'normal', 'color'))
    triangles = GeomTriangles(Geom.UHStatic)
    count = 0
    for face in faces:
        n = (Vec3(*face[1])-Vec3(*face[0])).cross(Vec3(*face[2])-Vec3(*face[0]))
        n.normalize()
        for p in face:
            vertex.addData3(*p)
            normal.addData3(n)
            colors.addData4(*color)
        for i in range(1, len(face)-1):
            triangles.addVertices(count, count+i, count+i+1)
        count += len(face)
    geometry = Geom(data)
    geometry.addPrimitive(triangles)
    node = GeomNode(name)
    node.addGeom(geometry)
    result = parent.attachNewNode(node)
    result.setTwoSided(True)
    return result


def box(parent, pos, size, color, name='box'):
    x, y, z = (v/2 for v in size)
    faces = [((-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)),
        ((-x,y,-z),(x,y,-z),(x,-y,-z),(-x,-y,-z)),
        ((-x,-y,-z),(x,-y,-z),(x,-y,z),(-x,-y,z)),
        ((x,y,-z),(-x,y,-z),(-x,y,z),(x,y,z)),
        ((-x,y,-z),(-x,-y,-z),(-x,-y,z),(-x,y,z)),
        ((x,-y,-z),(x,y,-z),(x,y,z),(x,-y,z))]
    node = mesh(parent, name, faces, color)
    node.setPos(*pos)
    return node


def cylinder(parent, pos, radius, height, color, sides=16, top_radius=None):
    top_radius = radius if top_radius is None else top_radius
    bottom = [(radius*math.cos(i*math.tau/sides), radius*math.sin(i*math.tau/sides), 0) for i in range(sides)]
    top = [(top_radius*math.cos(i*math.tau/sides), top_radius*math.sin(i*math.tau/sides), height) for i in range(sides)]
    faces = [tuple(reversed(bottom)), tuple(top)]
    faces += [(bottom[i], bottom[(i+1)%sides], top[(i+1)%sides], top[i]) for i in range(sides)]
    node = mesh(parent, 'cylinder', faces, color)
    node.setPos(*pos)
    return node


def lines(parent, points, color, thickness=2):
    pen = LineSegs()
    pen.setColor(*color)
    pen.setThickness(thickness)
    pen.moveTo(*points[0])
    for p in points[1:]:
        pen.drawTo(*p)
    return parent.attachNewNode(pen.create())


def text3d(parent, label, pos, size, color):
    t = TextNode(label)
    t.setText(label)
    t.setAlign(TextNode.ACenter)
    t.setTextColor(*color)
    node = parent.attachNewNode(t)
    node.setPos(*pos)
    node.setScale(size)
    node.setLightOff()
    return node


def build_car(parent, color):
    root = parent.attachNewNode('sketch-pickup')
    dark = (.025,.038,.055,1)
    body = box(root, (0,0,.88), (2.05,4.55,.68), color)
    box(root, (0,-1.55,1.25), (1.88,1.15,.12), (.075,.09,.12,1))
    # Extruded side profile preserves the sketch's squared bed and sloping roof/hood.
    profile = [(-.55,1.2),(-.5,2.15),(.05,2.28),(.95,2.15),(1.7,1.25)]
    left = [(-.96,y,z) for y,z in profile]
    right = [(.96,y,z) for y,z in profile]
    mesh(root,'angular-cabin',[tuple(reversed(left)),tuple(right)]+
         [(left[i],right[i],right[(i+1)%5],left[(i+1)%5]) for i in range(5)], color)
    for sign in (-1,1):
        x = sign*.972
        mesh(root, 'side-glass', [[(x,-.39,1.4),(x,-.35,2.02),(x,.03,2.14),
             (x,.78,2.03),(x,1.32,1.4)]], (.075,.19,.25,1))
        lines(root, [(x,.34,1.3),(x,.34,2.16)], dark, 3)
        box(root,(x,.1,1.29),(.045,.25,.05),dark)
        lines(root, [(x,-2.22,1.23),(x,-.5,1.23),(x,1.7,1.23),(x,2.2,1.05)], dark,2)
    mesh(root, 'windshield', [[(-.83,.99,2.09),(.83,.99,2.09),(.83,1.57,1.4),(-.83,1.57,1.4)]],(.09,.24,.30,1))
    box(root,(0,2.29,.83),(1.8,.11,.2),dark)
    for x in (-.68,.68):
        lamp=box(root,(x,2.31,1.02),(.45,.08,.13),(.75,.98,1,1))
        lamp.setLightOff()
        tail=box(root,(x,-2.29,1.02),(.4,.08,.14),(1,.12,.05,1))
        tail.setLightOff()
    wheels = []
    for x in (-1.12,1.12):
        for y in (-1.43,1.43):
            hub = root.attachNewNode('wheel-hub')
            hub.setPos(x,y,.68)
            wheel=cylinder(hub,(0,0,0),.73,.36,dark,24)
            wheel.setR(90)
            rim=cylinder(hub,(-.02 if x<0 else .38,0,0),.43,.04,(.5,.6,.67,1),12)
            rim.setR(90)
            wheels.append(hub)
    # Flat translucent contact shadow.
    shadow=box(root,(0,0,.025),(2.7,5,.02),(0,0,0,.35))
    shadow.setTransparency(True)
    shadow.setLightOff()
    flames=[]
    for x in (-.62,.62):
        flame=box(root,(x,-2.75,.65),(.28,1.2,.26),(.12,.85,1,1))
        flame.setLightOff()
        flame.hide()
        flames.append(flame)
    return root, wheels, flames


def build_world(parent, race):
    world = parent.attachNewNode('circuit')
    track = race.track
    road, curbs_a, curbs_b = [], [], []
    def point(s, offset, z):
        x,y,_=track.at(s,offset)
        return x,y,z
    for i in range(360):
        a,b=track.lengths[i:i+2]
        road.append((point(a,-9.5,.02),point(b,-9.5,.02),point(b,9.5,.02),point(a,9.5,.02)))
        for side in (-1,1):
            face=(point(a,side*9.5,.045),point(b,side*9.5,.045),point(b,side*10.3,.045),point(a,side*10.3,.045))
            (curbs_a if i%8<4 else curbs_b).append(face)
        if i%8<3:
            mesh(world,'lane-marker',[(point(a,-.09,.04),point(b,-.09,.04),point(b,.09,.04),point(a,.09,.04))],(.5,.57,.62,1))
    mesh(world,'asphalt',road,(.085,.115,.15,1))
    mesh(world,'curb-white',curbs_a,(.82,.85,.81,1))
    mesh(world,'curb-orange',curbs_b,(1,.24,.075,1))
    box(world,(0,0,-.35),(1600,1600,.5),(.035,.065,.085,1))
    for side in (-1,1):
        points=[point(s,side*10.5,.85) for s in track.lengths]
        rail=lines(world,points,(.12,.74,.83,1) if side<0 else (.99,.32,.13,1),3)
        rail.setLightOff()
        for i in range(0,360,5):
            box(world,point(track.lengths[i],side*10.5,.4),(.22,.22,.8),(.17,.24,.3,1))
    gates=[]
    for i in range(8):
        s=track.length*i/8
        x,y,h=track.at(s)
        gate=world.attachNewNode('gate')
        gate.setPos(x,y,0)
        gate.setH(math.degrees(h)-90)
        color=(1,.37,.12,1) if i==0 else (.13,.72,.8,1)
        for sign in (-1,1):
            box(gate,(sign*10,0,3.7),(.65,.8,7.4),(.12,.2,.26,1))
            beam=box(gate,(sign*9.6,0,3.7),(.12,.95,7.4),color)
            beam.setLightOff()
        box(gate,(0,0,7.2),(20.6,1,.8),(.1,.16,.21,1))
        text3d(gate,'SKETCH / CIRCUIT' if i==0 else f'CHECKPOINT  0{i}',(0,-.56,6.98),.48,color)
        gates.append(gate)
        if i==0:
            for row in range(2):
                for col in range(20):
                    box(gate,(-9.5+col,row-.5,.055),(.95,.95,.035),(.9,.92,.89,1) if (row+col)%2 else (.02,.025,.03,1))
    for x,y,h,s in race.pads:
        pad=world.attachNewNode('boost-pad')
        pad.setPos(x,y,.07)
        pad.setH(math.degrees(h)-90)
        box(pad,(0,0,0),(4.8,5.5,.08),(.035,.25,.31,1))
        for v in (-1.6,0,1.6):
            arrow=lines(pad,[(-1.8,v-.5,.08),(0,v+.45,.08),(1.8,v-.5,.08)],(.24,1,1,1),5)
            arrow.setLightOff()
    for x,y,r,kind,s,lane in race.obstacles:
        if kind=='crate':
            obj=box(world,(x,y,1.25),(r*1.7,r*1.7,2.5),(.42,.27,.15,1))
            obj.setH(22)
            for z in (.35,2.05):
                box(world,(x,y,z),(r*1.75,r*1.75,.15),(1,.65,.15,1))
        elif kind=='barrel':
            cylinder(world,(x,y,0),r,2.1,(.82,.2,.065,1))
            cylinder(world,(x,y,.7),r+.03,.35,(.96,.83,.61,1))
        else:
            box(world,(x,y,.12),(2.2,2.2,.24),(.03,.04,.05,1))
            cylinder(world,(x,y,.23),r,2,(1,.36,.08,1),12,.1)
            cylinder(world,(x,y,1.05),r*.63,.3,(1,.91,.77,1),12,r*.47)
    rng=random.Random(71)
    for i in range(65):
        t=i/65*math.tau
        radius=rng.uniform(158,235)
        x,y=radius*math.cos(t),radius*math.sin(t)
        height=rng.uniform(12,72)
        w=rng.uniform(5,14)
        box(world,(x,y,height/2),(w,w,height),(.065,.10,.145,1))
        for z in range(5,int(height),7):
            strip=box(world,(x,y-w/2-.04,z),(w*.75,.05,.25),(.19,.49,.56,1))
            strip.setLightOff()
    for i in range(22):
        t=i/22*math.tau
        x,y=360*math.cos(t),360*math.sin(t)
        cylinder(world,(x,y,-1),rng.uniform(50,95),rng.uniform(45,115),(.07,.12,.17,1),5,0)
    # Infield solar pylons and a monumental orange ring-like installation.
    for i in range(12):
        t=i/12*math.tau
        box(world,(27*math.cos(t),27*math.sin(t),3),(2,2,6),(.13,.25,.28,1))
    cylinder(world,(0,0,0),18,2,(.12,.2,.24,1),48)
    cylinder(world,(0,0,2),8,21,(.15,.25,.3,1),6,3)
    crown=cylinder(world,(0,0,23),7,1,(1,.35,.09,1),6)
    crown.setLightOff()
    world.flattenStrong()
    return world
