import timeit

setup = """
class Prop:
    def __init__(self, notes=None):
        self.notes = notes

def make_props():
    return [Prop("Existing Note") for i in range(100)] + [Prop(None) for i in range(100)]
"""

code_concat = """
props = make_props()
for p in props:
    p.notes = (p.notes or "") + " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code_append = """
props = make_props()
suffix = " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
for p in props:
    if p.notes:
        p.notes += suffix
    else:
        p.notes = suffix
"""

print("concat       :", timeit.timeit(code_concat, setup=setup, number=100000))
print("append       :", timeit.timeit(code_append, setup=setup, number=100000))
