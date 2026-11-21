"""Inspect Kickmix qubit allocation handles before creating a source-lifetime ledger."""
import json
import kickmix as km

def describe(o):
    d={"class":type(o).__name__,"module":type(o).__module__,"repr":repr(o)[:160],
       "str":str(o)[:160],"hashable":False}
    try:d["len"]=len(o)
    except (TypeError,ValueError):pass
    try:d["int"]=int(o)
    except (TypeError,ValueError):pass
    try:d["hash"]=hash(o);d["hashable"]=True
    except (TypeError,ValueError):pass
    try:d["size"]=int(o.size)
    except (TypeError,ValueError,AttributeError):pass
    return d

b=km.CircuitBuilder()
r=b.create_quantum_register(3,"S0")
w=b.alloc_qubits(2)
c=b.alloc_bits(2)
items={"named":r,"named0":r[0],"named1":r[1],"temp":w,"temp0":w[0],"classic":c,"classic0":c[0],"concat":km.array([r[0],w[0]])}
for label,o in items.items(): print(json.dumps({"label":label,**describe(o)}))
for label,o in [("single0",r[0]),("single0_again",r[0]),("work0",w[0])]:
    print(json.dumps({"label":label,"attributes": sorted(n for n in dir(o) if not n.startswith("__"))[:45]}))
print("builder_properties",sorted(n for n in dir(b) if any(t in n.lower() for t in ("qubit","count","num","free","alloc","mark"))))
b.free(w)
b.free(c)
print("final_num_qubits",b.finish_circuit().num_qubits)
