import ode
import visual

def convert_triangles_to_vertices_faces(triangles):
    corners = []
    triangles = []
    id_index_map = {}
    for t in triangles:
        coords = []
        for p in (t.p1, t.p2, t.p3):
            # add the point to the id/index mapping, if necessary
            if not id_index_map.has_key(p.id):
                corners.append((p.x, p.y, p.z))
                id_index_map[p.id] = len(corners) - 1
            coords.append(id_index_map[p.id]) 
        triangles.append(coords)
    return corners, triangles

def convert_triangles_to_vertices_normals(triangles):
    vertices = []
    normals = []
    for t in triangles:
        for p in (t.p1, t.p2, t.p3):
            vertices.append((p.x, p.y, p.z))
        n = t.normal()
        normals.append((n.x, n.y, n.z))
    return vertices, normals


class PhysicalWorld:

    def __init__(self):
        self._world = ode.World()
        self._space = ode.Space()
        self._geoms = []
        self._bodies = []
        self._visuals = []
        self._contacts = ode.JointGroup()
        self._speed = None
        self._drill = None
        self._collision_detected = False

    def _add_geom(self, geom, position):
        body = ode.Body(self._world)
        body.setPosition(position)
        body.setGravityMode(False)
        geom.setBody(body)
        self._geoms.append(geom)
        self._bodies.append(body)

    def add_mesh(self, position, triangles):
        mesh = ode.TriMeshData()
        vertices, faces = convert_triangles_to_vertices_faces(triangles)
        mesh.build(vertices, faces)
        geom = ode.GeomTriMesh(mesh, self._space)
        self._add_geom(geom, position)
        # create visual object
        vertices, normal = convert_triangles_to_vertices_normals(triangles)
        visual_object = visual.faces(pos=vertices, color=len(vertices) * [visual.color.blue], normal=normal)
        self._visuals.append((visual_object, geom))
        return geom

    def add_sphere(self, position, radius):
        geom = ode.GeomSphere(self._space, radius)
        self._add_geom(geom, position)
        # create visual sphere
        visual_object = visual.sphere(pos=position, radius=radius)
        self._visuals.append((visual_object, geom))
        return geom

    def _update_drill(self):
        for obj, geom in self._visuals:
            if geom is self._drill:
                obj.pos = geom.getPosition()

    def _update_drill_speed(self):
        if (self._drill is None) or (self._speed is None):
            return
        self._drill.getBody().setLinearVel(self._speed)

    def set_drill(self, geom):
        if geom in self._geoms:
            self._drill = geom
        self._update_drill_speed()

    def set_drill_speed(self, speed):
        self._speed = speed
        self._update_drill_speed()

    def remove_body(self, geom):
        if geom in self._geoms:
            body = geom.getBody()
            if body in self._bodies:
                self._bodies.remove(body)
            self._geoms.remove(geom)

    def _collision_callback(self, geom1, geom2):
        if geom1 is self._drill:
            obstacle = geom2
        elif geom2 is self._drill:
            obstacle = geom1
        else:
            return
        contacts = ode.collide(self._drill, obstacle)
        if contacts:
            self._collision_detected = True
        for c in contacts:
            # no bounce effect
            c.setBounce(0)
            ode.ContactJoint(self._world, self._contacts, c).attach(self._drill.getBody(), obstacle.getBody())

    def calculate_step(self, stepsize):
        return
        self._collision_detected = False
        self._space.collide(self, self._collision_callback)
        self._world.step(stepsize)
        self._contacts.empty()
        self._update_drill()
        visual.rate(20)

    def check_collision(self):
        return self._collision_detected

