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
    p.notes = (p.notes or "") + " [GIS: verify]"
"""

code2 = """
props = make_props()
for p in props:
    p.notes = f"{p.notes or ''} [GIS: verify]"
"""

code3 = """
props = make_props()
for p in props:
    p.notes = (p.notes + " [GIS: verify]") if p.notes else " [GIS: verify]"
"""

code4 = """
props = make_props()
suffix = " [GIS: verify]"
for p in props:
    p.notes = "".join([p.notes or "", suffix])
"""

print("concat_plus", timeit.timeit(code1, setup=setup, number=100000))
print("f_string", timeit.timeit(code2, setup=setup, number=100000))
print("inline_if", timeit.timeit(code3, setup=setup, number=100000))
print("join_list", timeit.timeit(code4, setup=setup, number=100000))
