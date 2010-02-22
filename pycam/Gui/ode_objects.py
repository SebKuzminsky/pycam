import ode


ShapeCylinder = lambda radius, height: ode.GeomCylinder(None, radius, height)
ShapeCapsule = lambda radius, height: ode.GeomCapsule(None, radius, height - (2 * radius))


def convert_triangles_to_vertices_faces(triangles):
    corners = []
    faces = []
    id_index_map = {}
    for t in triangles:
        coords = []
        # TODO: check if we need to change the order of points for non-AOI models as well
        for p in (t.p1, t.p3, t.p2):
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
        self._drill_offset = None
        self._collision_detected = False

    def reset(self):
        self._world = ode.World()
        self._space = ode.Space()
        self._geoms = []
        self._contacts = ode.JointGroup()
        self._drill = None
        self._drill_offset = None
        self._collision_detected = False

    def _add_geom(self, geom, position, append=True):
        body = ode.Body(self._world)
        body.setPosition(position)
        body.setGravityMode(False)
        geom.setBody(body)
        if append:
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
        #geom = ode.GeomTransform(self._space)
        #geom.setOffset(position)
        #geom.setGeom(shape)
        #shape.setOffset(position)
        self._space.add(shape)
        self._add_geom(shape, position, append=False)
        self._drill_offset = position
        self._drill = shape

    def extend_drill(self, diff_x, diff_y, diff_z):
        try:
            func = self._drill.extend_shape
        except ValueError:
            return
        func(diff_x, diff_y, diff_z)

    def reset_drill(self):
        try:
            func = self._drill.reset_shape
        except ValueError:
            return
        func()

    def set_drill_position(self, position):
        if self._drill:
            position = (position[0] + self._drill_offset[0], position[1] + self._drill_offset[1], position[2] + self._drill_offset[2])
            self._drill.setPosition(position)

    def _collision_callback(self, dummy, geom1, geom2):
        drill_body = self._drill.getBody()
        if geom1.getBody() is drill_body:
            obstacle = geom2
        elif geom2.getBody() is drill_body:
            obstacle = geom1
        else:
            return
        # check if the drill is made up of multiple geoms
        try:
            children = self._drill.children[:]
        except AttributeError:
            children = []
        contacts = []
        for shape in children + [self._drill]:
            contacts.extend(ode.collide(shape, obstacle))
            # break early to improve performance
            if contacts:
                break
        if contacts:
            self._collision_detected = True

    def check_collision(self):
        self._collision_detected = False
        self._space.collide(None, self._collision_callback)
        self._contacts.empty()
        return self._collision_detected

    def get_space(self):
        return self._space

