import timeit
import gc

def concat_plus():
    notes = None
    for _ in range(1000):
        notes = (notes or "") + " [GIS: verify]"

def f_string():
    notes = None
    for _ in range(1000):
        notes = f"{notes or ''} [GIS: verify]"

def join_list():
    notes = None
    suffix = " [GIS: verify]"
    for _ in range(1000):
        notes = "".join([notes or "", suffix])

print("concat_plus", timeit.timeit(concat_plus, number=10000))
print("f_string", timeit.timeit(f_string, number=10000))
print("join_list", timeit.timeit(join_list, number=10000))
