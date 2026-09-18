"""Procedural racing geometry with a user-supplied Seoul backdrop."""
import math
import random
from pathlib import Path
from panda3d.core import (GeomVertexData, GeomVertexFormat, GeomVertexWriter,
    GeomTriangles, Geom, GeomNode, Vec3, LineSegs, TextNode, TexturePool)


def mesh(parent, name, faces, color, smooth=False):
    data = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
    vertex, normal, colors = (GeomVertexWriter(data, key) for key in ('vertex', 'normal', 'color'))
    triangles = GeomTriangles(Geom.UHStatic)
    count = 0
    averaged={}
    if smooth:
        for face in faces:
            n=(Vec3(*face[1])-Vec3(*face[0])).cross(Vec3(*face[2])-Vec3(*face[0]))
            for p in face:
                averaged[p]=averaged.get(p,Vec3(0))+n
        for n in averaged.values():
            n.normalize()
    for face in faces:
        n = (Vec3(*face[1])-Vec3(*face[0])).cross(Vec3(*face[2])-Vec3(*face[0]))
        n.normalize()
        for p in face:
            vertex.addData3(*p)
            normal.addData3(averaged[p] if smooth else n)
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


def build_player_car(parent, color):
    """Blue rear-engine coupe inspired by the supplied 911 Turbo blueprint.

    Same centered footprint / return contract as build_car; AI models are untouched.
    """
    root=parent.attachNewNode('player-blue-turbo')
    dark=(.022,.029,.043,1)
    silver=(.57,.65,.75,1)
    glass=(.075,.18,.27,1)
    # Rounded wide rear quarters and a low nose, lofted along the car's +Y forward axis.
    sections=[(-2.23,.78,.76),(-2.02,1.0,.9),(-1.6,1.13,1.05),
              (-1.2,1.15,1.1),(-.65,1.03,1.03),(0,1.0,.97),
              (.7,1.05,.96),(1.25,1.13,1.1),(1.65,1.10,1.08),
              (2.0,.99,.94),(2.23,.8,.69)]
    rings=[]
    for y,w,top in sections:
        rings.append([(w*math.sin(i*math.tau/32),y,
                       .36+(top-.36)*(.5+.5*math.cos(i*math.tau/32))) for i in range(32)])
    faces=[tuple(reversed(rings[0])),tuple(rings[-1])]
    for a,b in zip(rings,rings[1:]):
        faces.extend((a[i],a[(i+1)%32],b[(i+1)%32],b[i]) for i in range(32))
    mesh(root,'rounded-blue-body',faces,color,smooth=True)
    profile=[(-1.48,1.0),(-.81,1.61),(-.45,1.77),(.22,1.73),(.74,1.29),(.94,.98)]
    left=[(-.79,y,z) for y,z in profile]
    right=[(.79,y,z) for y,z in profile]
    mesh(root,'coupe-roof',[tuple(reversed(left)),tuple(right)]+
         [(left[i],right[i],right[(i+1)%6],left[(i+1)%6]) for i in range(6)],color)
    for side in (-1,1):
        x=side*.802
        mesh(root,'quarter-glass', [[(x,-1.26,1.08),(x,-.75,1.54),(x,-.55,1.62),(x,-.57,1.1)]],glass)
        mesh(root,'door-glass', [[(x,-.49,1.1),(x,-.47,1.65),(x,.19,1.61),(x,.65,1.25),(x,.71,1.1)]],glass)
        lines(root,[(x,-.52,.59),(x,-.52,1.68)],dark,2)
        lines(root,[(side*1.025,-.65,.46),(side*1.025,.68,.46)],dark,3)
        box(root,(side*.96,-.34,1.0),(.1,.23,.045),silver)
        mirror=box(root,(side*1.06,.52,1.2),(.27,.25,.16),color)
        mirror.setH(side*10)
    mesh(root,'front-windscreen',[[(-.7,.25,1.70),(.7,.25,1.70),(.73,.84,1.09),(-.73,.84,1.09)]],glass)
    mesh(root,'rear-windscreen',[[(-.69,-.84,1.60),(.69,-.84,1.60),(.71,-1.4,1.1),(-.71,-1.4,1.1)]],glass)
    # Hood seams, round headlamps and black accordion-style bumper trim.
    for side in (-1,1):
        lines(root,[(side*.56,.9,1.02),(side*.52,1.8,.91)],(.05,.12,.24,1),1.4)
        bezel=cylinder(root,(side*.79,1.89,.96),.265,.10,silver,32)
        bezel.setP(-72)
        lamp=cylinder(root,(side*.79,1.99,.99),.216,.025,(1,.95,.73,1),32)
        lamp.setP(-72)
        lamp.setLightOff()
        box(root,(side*.86,2.08,.57),(.24,.08,.11),(1,.57,.16,1)).setLightOff()
    box(root,(0,2.18,.47),(1.72,.16,.15),dark)
    box(root,(0,-2.17,.48),(1.83,.14,.15),dark)
    box(root,(0,-2.18,.78),(1.70,.055,.14),(.88,.075,.055,1)).setLightOff()
    plate=box(root,(0,-2.255,.53),(.55,.028,.16),(.86,.9,.96,1))
    # Whale-tail spoiler and horizontal engine grille are the blueprint's key rear details.
    for side in (-1,1):
        box(root,(side*.62,-1.65,1.10),(.09,.35,.30),dark)
    box(root,(0,-1.78,1.27),(2.02,.73,.12),color)
    box(root,(0,-2.1,1.33),(2.08,.13,.16),dark)
    for i in range(9):
        box(root,(-.61+i*.15,-1.63,1.341),(.06,.37,.018),dark)
    wheels=[]
    for x in (-1.09,1.09):
        for y in (-1.23,1.23):
            hub=root.attachNewNode('wheel-hub')
            hub.setPos(x,y,.59)
            tire=cylinder(hub,(-.18,0,0),.57,.36,dark,32)
            tire.setR(90)
            outer=-.22 if x<0 else .18
            rim=cylinder(hub,(outer,0,0),.38,.04,silver,32)
            rim.setR(90)
            inset=cylinder(hub,(-.230 if x<0 else .222,0,0),.29,.008,dark,24)
            inset.setR(90)
            for j in range(5):
                angle=j*math.tau/5
                spoke=box(hub,(-.24 if x<0 else .24,math.sin(angle)*.17,math.cos(angle)*.17),(.025,.09,.34),silver)
                spoke.setP(-math.degrees(angle))
            cap=cylinder(hub,(-.265 if x<0 else .25,0,0),.09,.015,silver,16)
            cap.setR(90)
            wheels.append(hub)
    shadow=box(root,(0,0,.025),(2.6,4.7,.02),(0,0,0,.22))
    shadow.setTransparency(True)
    shadow.setLightOff()
    flames=[]
    for x in (-.66,.66):
        flame=box(root,(x,-2.6,.39),(.18,.9,.18),(.12,.65,1,1))
        flame.setLightOff()
        flame.hide()
        flames.append(flame)
    return root,wheels,flames

def build_dusk_sky(parent):
    """A continuous sky gradient with one softly blended photographic horizon.

    Fade the reference in geometry rather than tiling the photo: this avoids
    repeating towers, hard seams, or photographic bridge edges across the sky.
    """
    data=GeomVertexData('dusk',GeomVertexFormat.getV3c4(),Geom.UHStatic)
    vertex=GeomVertexWriter(data,'vertex')
    colors=GeomVertexWriter(data,'color')
    tris=GeomTriangles(Geom.UHStatic)
    levels=[(-150,(.27,.19,.29,1)),(0,(.51,.25,.31,1)),(100,(.37,.21,.32,1)),
            (300,(.20,.15,.28,1)),(700,(.085,.10,.21,1)),(1600,(.06,.08,.17,1))]
    for z,col in levels:
        for i in range(97):
            a=i/96*math.tau
            vertex.addData3(1100*math.sin(a),1100*math.cos(a),z)
            colors.addData4(*col)
    for j in range(len(levels)-1):
        for i in range(96):
            k=j*97+i
            tris.addVertices(k,k+1,k+98)
            tris.addVertices(k,k+98,k+97)
    geom=Geom(data);geom.addPrimitive(tris)
    node=GeomNode('continuous-sunset-sky');node.addGeom(geom)
    sky=parent.attachNewNode(node)
    sky.setLightOff();sky.setFogOff();sky.setTwoSided(True)
    sky.setDepthWrite(False);sky.setBin('background',-20)
    photo=Path(__file__).resolve().parent.parent/'assets'/'seoul-dusk-reference.jpg'
    texture=TexturePool.loadTexture(str(photo)) if photo.exists() else None
    if not texture:
        return
    data=GeomVertexData('photo-horizon',GeomVertexFormat.getV3c4t2(),Geom.UHStatic)
    vertex=GeomVertexWriter(data,'vertex');colors=GeomVertexWriter(data,'color')
    uv=GeomVertexWriter(data,'texcoord');tris=GeomTriangles(Geom.UHStatic)
    cols,rows=40,24
    for j in range(rows+1):
        v=j/rows
        for i in range(cols+1):
            u=i/cols
            a=(u-.5)*math.radians(100)
            vertex.addData3(680*math.sin(a),680*math.cos(a),-95+v*280)
            alpha=min(1,u*8,(1-u)*8,v*5,(1-v)*6)*.8
            colors.addData4(1,1,1,alpha)
            uv.addData2(u,.40+v*.60)
    for j in range(rows):
        for i in range(cols):
            k=j*(cols+1)+i
            tris.addVertices(k,k+1,k+cols+2)
            tris.addVertices(k,k+cols+2,k+cols+1)
    geom=Geom(data);geom.addPrimitive(tris)
    node=GeomNode('reference-photo-horizon');node.addGeom(geom)
    photo_node=parent.attachNewNode(node)
    photo_node.setTexture(texture);photo_node.setTransparency(True)
    photo_node.setLightOff();photo_node.setFogOff();photo_node.setTwoSided(True)
    photo_node.setDepthWrite(False);photo_node.setBin('background',-10)

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
    mesh(world,'asphalt',road,(.25,.27,.34,1))
    mesh(world,'sidewalk',sidewalks,(.24,.25,.3,1))
    mesh(world,'curb-white',curbs_a,(.82,.85,.81,1))
    mesh(world,'curb-orange',curbs_b,(1,.24,.075,1))
    # Underside follows the road instead of a solid ground plane over the river.
    underside=[tuple((x,y,-.65) for x,y,z in face) for face in road]
    mesh(world,'bridge-deck-underside',underside,(.16,.17,.22,1))
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
            box(gate,(sign*(half+.5),0,3.7),(.65,.8,7.4),(.24,.29,.38,1))
            beam=box(gate,(sign*(half+.1),0,3.7),(.12,.95,7.4),color)
            beam.setLightOff()
        box(gate,(0,0,7.2),(track.width+1.6,1,.8),(.13,.2,.29,1))
        text3d(gate,'HAN RIVER / NIGHT RUN' if i==0 else f'CHECKPOINT  0{i}',(0,-.56,6.98),.48,color)
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
    # The river lies below the unchanged z=0 driving plane, so racing physics stays intact.
    water=box(world,(0,0,-7.3),(1800,1800,.15),(.075,.085,.15,1),'han-river')
    water.setLightOff()
    # Mirror-like broken ribbons suggest distant lights on a gently moving river.
    reflected=[]
    for i in range(320):
        x=rng.uniform(-330,330)
        y=rng.uniform(-330,330)
        if abs(race.track.project(x,y)[1])<half+6:
            continue
        width=rng.uniform(.2,1.6)
        for j in range(rng.randint(3,9)):
            yy=y+j*rng.uniform(1.5,3.5)
            reflected.append(((x-width,yy,-7.20),(x+width,yy,-7.20),
                              (x+width*.7,yy+.55,-7.20),(x-width*.7,yy+.55,-7.20)))
    shimmer=mesh(world,'river-reflections',reflected,(.63,.36,.29,.15))
    shimmer.setTransparency(True)
    shimmer.setLightOff()
    # Structural piers and continuous amber edge lighting turn the loop into an elevated road.
    for i in range(0,360,12):
        for side in (-1,1):
            x,y,_=track.at(track.lengths[i],side*(half-2))
            cylinder(world,(x,y,-7.15),.75,6.8,(.22,.24,.29,1),10)
    for side in (-1,1):
        rail=lines(world,[point(s,side*(half+.7),.92) for s in track.lengths],(1,.60,.22,1),4)
        rail.setLightOff()
    for i in range(40):
        for side in (-1,1):
            s=i*track.length/40
            x,y,h=track.at(s,side*(half+.9))
            lamp=world.attachNewNode('amber-streetlight')
            lamp.setPos(x,y,0)
            lamp.setH(math.degrees(h)-90)
            box(lamp,(0,0,3.3),(.11,.11,6.6),(.23,.25,.32,1))
            box(lamp,(-side*.6,0,6.55),(1.3,.15,.13),(.23,.25,.32,1))
            glow=box(lamp,(-side*1.16,0,6.5),(.48,.37,.11),(1,.75,.35,1))
            glow.setLightOff()
            # Translucent halo and road wash, deliberately soft rather than opaque cones.
            halo=box(lamp,(-side*1.16,0,6.5),(.68,.57,.25),(1,.56,.18,.14))
            halo.setTransparency(True)
            halo.setLightOff()
            wash=mesh(lamp,'lamplight-pool',[[(-side*1,-3,.095),(-side*7,-4,.095),
                      (-side*7,4,.095),(-side*1,3,.095)]],(1,.64,.3,.075))
            wash.setTransparency(True)
            wash.setLightOff()
    # Layered city skyline with lit windows on both front and side facades.
    for i in range(68):
        angle=i/68*math.tau
        radius=rng.uniform(182,300)
        x,y=radius*math.cos(angle),radius*math.sin(angle)
        height=rng.uniform(16,70)
        width=rng.uniform(7,15)
        building=world.attachNewNode('seoul-night-building')
        building.setPos(x,y,-7)
        building.setH(math.degrees(angle)-90)
        base=(rng.uniform(.11,.18),rng.uniform(.14,.21),rng.uniform(.22,.29),1)
        box(building,(0,0,height/2),(width,width,height),base)
        window_faces=[]
        for z in range(3,int(height)-2,3):
            for xx in range(-int(width/2)+1,int(width/2),2):
                if rng.random()<.28:
                    continue
                window_faces.append(((xx-.35,-width/2-.035,z),(xx+.35,-width/2-.035,z),
                                     (xx+.35,-width/2-.035,z+1),(xx-.35,-width/2-.035,z+1)))
                window_faces.append(((width/2+.035,xx-.35,z),(width/2+.035,xx+.35,z),
                                     (width/2+.035,xx+.35,z+1),(width/2+.035,xx-.35,z+1)))
        lights=mesh(building,'lit-windows',window_faces,
                    (1,.76,.40,1) if i%3 else (.62,.79,1,1))
        lights.setLightOff()
        if i%5==0:
            trim=box(building,(0,0,height+.1),(width+.12,width+.12,.16),(.47,.62,.88,1))
            trim.setLightOff()
    # Namsan ridge and landmark tower, intentionally outside the racing surface.
    for i in range(9):
        cylinder(world,(-160+i*40,350,-7),80,35+30*math.sin(i/8*math.pi),(.095,.11,.19,1),12,12)
    tower=world.attachNewNode('namsan-tower')
    tower.setPos(5,355,58)
    cylinder(tower,(0,0,0),2.1,44,(.62,.59,.54,1),16,1.2)
    for z,rad,height in [(37,6,3),(40,4,6),(46,2,3)]:
        deck=cylinder(tower,(0,0,z),rad,height,(.92,.67,.37,1),24)
        deck.setLightOff()
    cylinder(tower,(0,0,49),.45,20,(.92,.81,.67,1),12,.1).setLightOff()
    build_dusk_sky(world)
    world.flattenStrong()
    return world
