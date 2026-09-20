import timeit

setup = """
class Prop:
    def __init__(self, notes=None):
        self.notes = notes

def make_props():
    return [Prop(f"Note {i}" if i % 2 == 0 else None) for i in range(100)]
"""

code_original = """
props = make_props()
for p in props:
    p.notes = (p.notes or "") + " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code_f_string = """
props = make_props()
for p in props:
    p.notes = f"{p.notes or ''} [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
"""

code_f_string_optimized = """
props = make_props()
suffix = " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
for p in props:
    p.notes = f"{p.notes or ''}{suffix}"
"""

code_join = """
props = make_props()
suffix = " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
for p in props:
    p.notes = "".join([p.notes or "", suffix])
"""

code_concat_optimized = """
props = make_props()
suffix = " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
for p in props:
    n = p.notes
    p.notes = n + suffix if n else suffix
"""

print("original        :", timeit.timeit(code_original, setup=setup, number=100000))
print("f_string        :", timeit.timeit(code_f_string, setup=setup, number=100000))
print("f_string_opt    :", timeit.timeit(code_f_string_optimized, setup=setup, number=100000))
print("join            :", timeit.timeit(code_join, setup=setup, number=100000))
print("concat_optimized:", timeit.timeit(code_concat_optimized, setup=setup, number=100000))
