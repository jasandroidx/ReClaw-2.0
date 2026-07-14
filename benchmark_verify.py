import timeit

setup = """
class Prop:
    def __init__(self, notes=None):
        self.notes = notes

def make_props():
    return [Prop("Existing Note") for i in range(100)] + [Prop(None) for i in range(100)]
"""

code_original = """
props = make_props()
for p in props:
    p.notes = (p.notes or "") + " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code_optimized = """
props = make_props()
suffix = " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
for p in props:
    p.notes = p.notes + suffix if p.notes else suffix
"""

print("original :", timeit.timeit(code_original, setup=setup, number=100000))
print("optimized:", timeit.timeit(code_optimized, setup=setup, number=100000))
