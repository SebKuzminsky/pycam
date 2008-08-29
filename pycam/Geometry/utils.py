
INFINITE = 10000
epsilon = 0.0001

def sqr(x):
    return x*x

def min3(x,y,z):
    if x<y:
        xy = x
    else:
        xy = y

    if xy<z:
        return xy
    else:
        return z

def max3(x,y,z):
    if x>y:
        xy = x
    else:
        xy = y

    if xy>z:
        return xy
    else:
        return z
