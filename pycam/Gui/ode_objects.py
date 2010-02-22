import ode


ShapeCylinder = lambda radius, height: ode.GeomCylinder(None, radius, height)
ShapeCapsule = lambda radius, height: ode.GeomCapsule(None, radius, height - (2 * radius))


def convert_triangles_to_vertices_faces(triangles):
    corners = []
    faces = []
    id_index_map = {}
    for t in triangles:
        coords = []
        for p in (t.p1, t.p2, t.p3):
            # add the point to the id/index mapping, if necessary
            if not id_index_map.has_key(p.id):
                corners.append((p.x, p.y, p.z))
                id_index_map[p.id] = len(corners) - 1
            coords.append(id_index_map[p.id]) 
        faces.append(coords)
    return corners, faces


class PhysicalWorld:

    def __init__(self):
        self._world = ode.World()
        self._space = ode.Space()
        self._geoms = []
        self._contacts = ode.JointGroup()
        self._drill = None
        self._collision_detected = False

    def reset(self):
        self._world = ode.World()
        self._space = ode.Space()
        self._geoms = []
        self._contacts = ode.JointGroup()
        self._drill = None
        self._collision_detected = False

    def _add_geom(self, geom, position, append=True):
        body = ode.Body(self._world)
        body.setPosition(position)
        body.setGravityMode(False)
        geom.setBody(body)
        self._geoms.append(geom)

    def add_mesh(self, position, triangles):
        mesh = ode.TriMeshData()
        vertices, faces = convert_triangles_to_vertices_faces(triangles)
        mesh.build(vertices, faces)
        geom = ode.GeomTriMesh(mesh, self._space)
        self._add_geom(geom, position)

    def add_sphere(self, position, radius):
        geom = ode.GeomSphere(self._space, radius)
        self._add_geom(geom, position)

    def set_drill(self, shape, position):
        geom = ode.GeomTransform(self._space)
        geom.setGeom(shape)
        self._add_geom(geom, position, append=False)
        self._drill = geom

    def set_drill_position(self, position):
        if self._drill:
            self._drill.getBody().setPosition(position)

    def _collision_callback(self, dummy, geom1, geom2):
        if geom1 is self._drill:
            obstacle = geom2
        elif geom2 is self._drill:
            obstacle = geom1
        else:
            return
        contacts = ode.collide(self._drill, obstacle)
        if contacts:
            self._collision_detected = True
        return
        for c in contacts:
            # no bounce effect
            c.setBounce(0)
            ode.ContactJoint(self._world, self._contacts, c).attach(self._drill.getBody(), obstacle.getBody())

    def check_collision(self):
        self._collision_detected = False
        self._space.collide(None, self._collision_callback)
        self._contacts.empty()
        return self._collision_detected

