from math import ceil

def make_paths(node, offset=0):
    if offset == node:
        return [(node, offset)]

    bootstrap = math.ceil((node - offset) / 2) + offset

