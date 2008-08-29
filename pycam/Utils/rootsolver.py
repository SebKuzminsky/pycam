def find_root_subdivide(f, x0, x1, tolerance, scale):
    ymin = 0
    xmin = 0
    imin = 0
    while x1-x0>tolerance:
        for i in range(0,scale):
            x = x1 + (i/scale)*(x1-x0)
            y = f(x)
            abs_y = abs(y)
            if i==0:
                ymin = abs_y
                xmin = x
                imin = 0
            else:
                if abs_y<ymin:
                    ymin = abs_y
                    xmin = x
                    imin = i
        x0 = xmin - 1/scale
        x1 = xmin + 1/scale
        scale /= 10
    return xmin

def find_root_newton_raphson(f, df, x0, tolerance, maxiter):
    x = x0
    iter = 0
    while iter<maxiter:
        y = f(x)
        if y == 0:
            return x
        dy = df(x)
        if dy == 0:
            return None
        dx = y/dy
        x = x - dx
        if dx < tolerance:
            break
        iter += 1
    return x

def find_root(f, df=None, x0=0, x1=1, tolerance=0.001):
    return find_root_subdivide(f=f,x0=x0,x1=x1,tolerance=tolerance, scale=10.0)
