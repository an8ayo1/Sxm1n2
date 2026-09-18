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


def text3d(parent, label, pos, size, color, font=None):
    t = TextNode(label)
    if font is not None:
        t.setFont(font)
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
            hub.setPos(x,y,.75)
            # Center tire thickness around each hub; mirror the outer rim exactly.
            wheel=cylinder(hub,(-.18,0,0),.73,.36,dark,24)
            wheel.setR(90)
            rim=cylinder(hub,(-.22 if x<0 else .18,0,0),.43,.04,(.5,.6,.67,1),12)
            rim.setR(90)
            wheels.append(hub)
    # Flat translucent contact shadow.
    shadow=box(root,(0,0,.025),(2.7,5,.02),(.12,.18,.20,.13))
    shadow.setTransparency(True)
    shadow.setLightOff()
    flames=[]
    for x in (-.62,.62):
        flame=box(root,(x,-2.75,.65),(.28,1.2,.26),(.12,.85,1,1))
        flame.setLightOff()
        flame.hide()
        flames.append(flame)
    return root, wheels, flames


def build_world(parent, race, korean_font=None):
    world = parent.attachNewNode('circuit')
    track = race.track
    half = track.width/2
    road, curbs_a, curbs_b, sidewalks = [], [], [], []
    def point(s, offset, z):
        x,y,_=track.at(s,offset)
        return x,y,z
    for i in range(360):
        a,b=track.lengths[i:i+2]
        road.append((point(a,-half,.02),point(b,-half,.02),point(b,half,.02),point(a,half,.02)))
        for side in (-1,1):
            face=(point(a,side*half,.045),point(b,side*half,.045),point(b,side*(half+.8),.045),point(a,side*(half+.8),.045))
            (curbs_a if i%8<4 else curbs_b).append(face)
            sidewalks.append((point(a,side*(half+.8),.06),point(b,side*(half+.8),.06),
                              point(b,side*(half+5),.06),point(a,side*(half+5),.06)))
        if i%8<3:
            mesh(world,'lane-marker',[(point(a,-.09,.04),point(b,-.09,.04),point(b,.09,.04),point(a,.09,.04))],(.97,.96,.87,1))
    mesh(world,'asphalt',road,(.43,.49,.53,1))
    mesh(world,'sidewalk',sidewalks,(.88,.85,.76,1))
    mesh(world,'curb-white',curbs_a,(.82,.85,.81,1))
    mesh(world,'curb-orange',curbs_b,(1,.24,.075,1))
    box(world,(0,0,-.35),(1600,1600,.5),(.63,.80,.53,1))
    for side in (-1,1):
        points=[point(s,side*(half+.9),.85) for s in track.lengths]
        rail=lines(world,points,(.12,.74,.83,1) if side<0 else (.99,.32,.13,1),3)
        rail.setLightOff()
        for i in range(0,360,5):
            box(world,point(track.lengths[i],side*(half+.9),.4),(.22,.22,.8),(.67,.76,.78,1))
    gates=[]
    for i in range(8):
        s=track.length*i/8
        x,y,h=track.at(s)
        gate=world.attachNewNode('gate')
        gate.setPos(x,y,0)
        gate.setH(math.degrees(h)-90)
        color=(1,.37,.12,1) if i==0 else (.13,.72,.8,1)
        for sign in (-1,1):
            box(gate,(sign*(half+.5),0,3.7),(.65,.8,7.4),(.86,.92,.9,1))
            beam=box(gate,(sign*(half+.1),0,3.7),(.12,.95,7.4),color)
            beam.setLightOff()
        box(gate,(0,0,7.2),(track.width+1.6,1,.8),(.12,.43,.49,1))
        text3d(gate,'SEOUL / CIRCUIT' if i==0 else f'CHECKPOINT  0{i}',(0,-.56,6.98),.48,color)
        gates.append(gate)
        if i==0:
            for row in range(2):
                for col in range(int(track.width)):
                    box(gate,(-half+.5+col,row-.5,.055),(.95,.95,.035),(.9,.92,.89,1) if (row+col)%2 else (.02,.025,.03,1))
    for x,y,h,s in race.pads:
        pad=world.attachNewNode('boost-pad')
        pad.setPos(x,y,.07)
        pad.setH(math.degrees(h)-90)
        box(pad,(0,0,0),(4.8,5.5,.08),(.035,.25,.31,1))
        for v in (-1.6,0,1.6):
            arrow=lines(pad,[(-1.8,v-.5,.08),(0,v+.45,.08),(1.8,v-.5,.08)],(.24,1,1,1),5)
            arrow.setLightOff()
    # Warm hazard stripes and SLOW distinguish these from cyan acceleration pads.
    for x,y,h,s in race.slow_pads:
        pad=world.attachNewNode('slow-pad')
        pad.setPos(x,y,.07)
        pad.setH(math.degrees(h)-90)
        box(pad,(0,0,0),(4.8,5.5,.08),(.95,.48,.08,1))
        for v in (-2.1,-1.5,1.5,2.1):
            stripe=box(pad,(0,v,.055),(4.5,.22,.025),(.22,.15,.10,1))
            stripe.setLightOff()
        label=text3d(pad,'SLOW',(0,-.4,.1),.85,(.14,.10,.07,1))
        label.setP(-90)
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
    # Compact Korean shopping streets: cream facades, colorful fascia and hangul signs.
    names=[('서울상회','SEOUL MART'),('한강카페','HANGANG CAFE'),('봄날분식','BOM SNACK'),
           ('게임센터','GAME CENTER'),('초록약국','GREEN PHARMACY'),('도시문구','CITY BOOKS')]
    palettes=[(.95,.83,.67,1),(.73,.88,.87,1),(.96,.77,.73,1),(.82,.85,.98,1)]
    accents=[(.10,.51,.63,1),(.95,.43,.24,1),(.21,.65,.45,1),(.48,.42,.72,1)]
    for i in range(34):
        x,y,h=track.at(i*track.length/34,-(half+13))
        shop=world.attachNewNode('korean-storefront')
        shop.setPos(x,y,0)
        shop.setH(math.degrees(h)-180)  # Front faces the road, not the city perimeter.
        height=10+(i%4)*3
        box(shop,(0,0,height/2),(11,9,height),palettes[i%4])
        box(shop,(0,0,height+.2),(11.6,9.6,.45),(.96,.95,.89,1))
        box(shop,(0,-4.54,2),(10,.12,3.5),(.31,.63,.73,1))
        for xx in (-4,-2,0,2,4):
            box(shop,(xx,-4.66,2),(.12,.15,3.5),(.94,.96,.92,1))
        box(shop,(0,-4.8,4.9),(11.4,.6,1.65),accents[i%4])
        label=names[i%6][0 if korean_font is not None else 1]
        text3d(shop,label,(0,-5.12,4.45),.8,(1,1,.94,1),korean_font)
        # Repeated windows and slim vertical signs read as an Asian high street.
        for z in range(7,height-1,3):
            for xx in (-3.5,0,3.5):
                box(shop,(xx,-4.56,z),(2.1,.14,1.9),(.34,.64,.77,1))
                box(shop,(xx,-4.67,z-1.05),(2.5,.35,.13),(.98,.96,.87,1))
        if i%3==0:
            box(shop,(5,-5,8.2),(1.2,.7,4.2),accents[(i+1)%4])
            text3d(shop,'24\nH',(5,-5.4,8.8),.57,(1,1,.94,1))
    # Pale numbered apartment blocks give a Seoul skyline without enclosing the track.
    for i in range(24):
        t=i/24*math.tau
        radius=rng.uniform(164,215)
        tower=world.attachNewNode('apartment')
        tower.setPos(radius*math.cos(t),radius*math.sin(t),0)
        tower.setH(math.degrees(t)-90)
        height=rng.uniform(22,43)
        box(tower,(0,0,height/2),(13,12,height),(.88,.91,.86,1))
        box(tower,(0,0,height-2),(13.1,12.1,1.3),(.53,.73,.77,1))
        for z in range(4,int(height)-4,4):
            for xx in (-4,0,4):
                box(tower,(xx,-6.03,z),(2,.08,2.1),(.40,.66,.78,1))
        text3d(tower,str(101+i),(0,-6.12,height-6),1.3,(.15,.34,.42,1))
    # Street trees and planters stay outside the physical road boundary.
    for i in range(32):
        for side in (-1,1):
            x,y,_=track.at(i*track.length/32,side*(half+3.3))
            box(world,(x,y,.22),(2.6,2.6,.44),(.81,.77,.64,1))
            cylinder(world,(x,y,.3),.23,3.4,(.54,.35,.20,1),8)
            cylinder(world,(x,y,2.7),1.8,2.5,(.27,.66,.34,1),9,.65)
            cylinder(world,(x,y,4),1.3,1.5,(.45,.78,.38,1),9,.3)
    # Zebra crossings and Korean-style horizontal traffic lights are scenery;
    # this closed race route always has green lights for the racers.
    for s in (32,190,335,510):
        x,y,h=track.at(s)
        crossing=world.attachNewNode('crosswalk-and-signal')
        crossing.setPos(x,y,0)
        crossing.setH(math.degrees(h)-90)
        for col in range(int(track.width/1.8)):
            box(crossing,(-half+1+col*1.8,0,.065),(1,5,.035),(.98,.98,.91,1))
        for side in (-1,1):
            box(crossing,(side*(half+1.6),3,3.6),(.23,.23,7.2),(.40,.49,.50,1))
        box(crossing,(0,3,7.1),(track.width+3.4,.23,.23),(.40,.49,.50,1))
        box(crossing,(0,3,6.8),(3.1,.6,.9),(.14,.23,.25,1))
        for xx,col in [(-.95,(.45,.18,.17,1)),(0,(.48,.40,.17,1)),(.95,(.15,1,.38,1))]:
            lamp=box(crossing,(xx,2.67,6.8),(.48,.06,.48),col)
            lamp.setLightOff()
    # Low green hills and a small pavilion keep the center and horizon open.
    for i in range(14):
        t=i/14*math.tau
        cylinder(world,(350*math.cos(t),350*math.sin(t),-1),75,48,
                 (.52,.75,.56,1),7,9)
    cylinder(world,(0,0,.01),20,.25,(.85,.86,.72,1),48)
    for x in (-4,4):
        for y in (-4,4):
            box(world,(x,y,2.7),(.55,.55,5.4),(.62,.31,.21,1))
    cylinder(world,(0,0,5.3),8,2.6,(.22,.43,.48,1),4,1.5)
    text3d(world,'SEOUL CITY RUN',(0,-8,1),1.2,(.12,.37,.43,1))
    world.flattenStrong()
    return world
