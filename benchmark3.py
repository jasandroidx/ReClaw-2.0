import timeit

setup = """
class Prop:
    def __init__(self, notes=None):
        self.notes = notes

def make_props():
    return [Prop(f"Note {i}" if i % 2 == 0 else None) for i in range(100)]
"""

code1 = """
props = make_props()
for p in props:
    p.notes = (p.notes or "") + " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code2 = """
props = make_props()
for p in props:
    p.notes = f"{p.notes or ''} [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code3 = """
props = make_props()
for p in props:
    p.notes = f"{p.notes} [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]" if p.notes else " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code4 = """
props = make_props()
for p in props:
    n = p.notes
    p.notes = f"{n} [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]" if n else " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

print("concat_plus", timeit.timeit(code1, setup=setup, number=100000))
print("f_string", timeit.timeit(code2, setup=setup, number=100000))
print("f_string_if", timeit.timeit(code3, setup=setup, number=100000))
print("f_string_if_var", timeit.timeit(code4, setup=setup, number=100000))
