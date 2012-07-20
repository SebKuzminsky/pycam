def _pocket_model(model):
    """Create pocketing path."""    
    # libarea.Vertex Linetypes
    LINE = 0
    ARC_CCW = 1
    ARC_CW = -1
    
    print "Model\n#lines:", model.get_num_of_lines()
    print "#line_groups:", len(model.get_polygons())
    
    # copy pycam.Model to libarea.Area
    my_area = area.Area()
    my_pocketParams = PocketParams()    
    for lg in model.get_polygons():
        #print "line_group:", lg
        print "line_group() #Points:", len(lg.get_points())
        my_curve = area.Curve()
        if lg.is_closed is True:
            curve_type = ARC_CW
        else:
            curve_type = LINE            
        p_first = True
        p_skip = False
        for pt in lg.get_points():
            #print "point(x,y): (%f,%f)" % (pt.x, pt.y)
            if p_first:
                my_curve.append(area.Vertex(area.Point(pt.x, pt.y)))
            else:
                if p_skip:  # ugly hack to load same begin/end point only once
                    p_skip = False
                else:
                    my_curve.append(area.Vertex(area.Point(pt.x, pt.y)))
                    p_skip = True
            """
            if p_previous is None:
                p_previous = area.Point(pt.x, pt.y)
            else:
                p_next = area.Point(pt.x, pt.y)
                my_curve.append(area.Vertex(LINE, p_previous, p_next))
                p_previous = p_next
            """
        my_area.append(my_curve)

    """
    # print the copy area its content
    print "----------------------------------------"
    print "copy area # Curves:", my_area.num_curves()
    i=1
    for c in my_area.getCurves():
        print "Curve: %i, # points:%i" % ( i, c.getNumVertices())
        for v in c.getVertices():
            print "point(x,y): (%f,%f)" % ( v.p.x, v.p.y )
        i+=1
    print "----------------------------------------"
    """
    
    pocket_polygons = []
    _pocket_area(my_area, my_pocketParams, pocket_polygons)
    return pocket_polygons

def _pocket_area(a, params, polygons):
    my_params = params

    if (my_params.m_rapid_down_to_height > my_params.m_clearance_height):
        my_params.m_rapid_down_to_height = my_params.m_clearance_height
    
    a.m_round_corners_factor = params.m_round_corner_factor
    first_offset = my_params.m_tool_diameter * 0.5 + my_params.m_material_allowance
    
    # copy Area instance
    #a_firstoffset = copy.deepcopy(a) # TODO Curve deepcopy not yet fully covered, thus Area neither as it depends on it
    a_firstoffset = area.Area()
    for c in a.getCurves():
        copy_curve = area.Curve()
        for vt in c.getVertices():
            copy_curve.append(copy.deepcopy(vt))
        a_firstoffset.append(copy_curve)    
    
    a_firstoffset.Offset(first_offset)

    arealist = []
    arealist.append(a_firstoffset) # debug
    _recur(my_params, arealist, a_firstoffset);
    #print "arealist length:", len(arealist)
    
    layer_count = int((my_params.m_start_depth - my_params.m_final_depth) / my_params.m_step_down)
    if (layer_count * my_params.m_step_down + 0.00001 < params.m_start_depth - my_params.m_final_depth):
        layer_count+=1
    print "layercount:", layer_count

    """
    for i in range (1, layer_count+1):
        depth = my_params.m_final_depth
        if (i != layer_count):
            depth = my_params.m_start_depth - i * my_params.m_step_down

        for a in arealist:
            cut_area(a, depth) # generate toolpath
    """
    # add all vertices from all areas to the polygons list
    print "#area's:", len(arealist)
    for a in arealist:
        #print "areaList()"
        for c in a.getCurves():
            print "Curve() #vertices:", c.getNumVertices()
            my_poly = Polygon()
            p_previous = None
            p_next = None
            for vt in c.getVertices():
                # from 2D to 3D with Z=0
                if p_previous is None:
                    p_previous = Point(vt.p.x, vt.p.y, 0.0)
                else:
                    p_next = Point(vt.p.x, vt.p.y, 0.0)
                    my_poly.append(Line(p_previous, p_next))
                    p_previous = p_next
                #polygons.append(Line(p1, p2))
                #polygons.append(Point(vt.p.x, vt.p.y, 0.0))
            polygons.append(my_poly)

def _recur(params, arealist, a1):

    if (a1.num_curves == 0):
        return;
        
    if (params.m_from_center):
        arealist.insert(0,a1) # prepend
    else:
        arealist.append(a1)
        
    # copy Area instance
    #a_offset = copy.deepcopy(a1) # TODO Curve deepcopy not yet fully covered, thus Area neither as it depends on it
    a_offset = area.Area()
    for c in a1.getCurves():
        copy_curve = area.Curve()
        for vt in c.getVertices():
            copy_curve.append(copy.deepcopy(vt))
        a_offset.append(copy_curve)

    a_offset.Offset(params.m_step_over)

    for curve in a_offset.getCurves():
        a2 = area.Area()
        a2.append(curve)
        _recur(params, arealist, a2)
        
class PocketParams:
    """Settings used for pocketing toolpath generation."""
    m_from_center = True
    m_round_corner_factor = 1.0
    m_material_allowance = 0.0
    m_step_over = 1.5
    m_clearance_height = 5
    m_start_depth = 0
    m_step_down = 1
    m_final_depth = -1
    m_rapid_down_to_height = 2
    m_tool_diameter = 2
    m_format_style = 0
    """
    Original settings
    m_from_center = True
    m_round_corner_factor = 1.0
    m_material_allowance = 0.0
    m_step_over = 1.5
    m_clearance_height = 5
    m_start_depth = 0
    m_step_down = 1
    m_final_depth = -3
    m_rapid_down_to_height = 2
    m_tool_diameter = 3
    m_format_style = 0
    """

