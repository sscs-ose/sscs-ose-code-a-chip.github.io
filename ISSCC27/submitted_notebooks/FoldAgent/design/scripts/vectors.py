"""Independent integer oracle and deterministic workload, without DUT imports."""
import random


def selected_targets(code):
    targets=[]
    for lane in range(8):
        sel=(code>>(2*lane))&3
        if sel==3: return None
        targets.append(lane if sel==0 else 7+sel)
    return targets if len(set(targets))==8 else None


def legal_maps():
    return [code for code in range(65536) if selected_targets(code) is not None]


def dot(vector, weights, k):
    return [sum(vector[i]*weights[i][j] for i in range(k)) for j in range(8)]


def generate(path, seed, count, *, first_k=None):
    rng=random.Random(seed); maps=legal_maps()
    with path.open('w') as out:
        for n in range(count):
            k=(4,16,64)[n%3]
            if n==0 and first_k is not None:k=first_k
            code=maps[n%len(maps)]
            values=[rng.randrange(-128,128) for _ in range(64)]
            weights=[[rng.randrange(-128,128) for _ in range(8)] for _ in range(64)]
            if n<3:
                values=[(-128,127,0)[n]]*64
                weights=[[(-128,127,0)[n]]*8 for _ in range(64)]
            error=int(n%19==18)
            fields=[k,code,error,*values,*[v for row in weights for v in row],*dot(values,weights,k)]
            out.write(' '.join(map(str,fields))+'\n')
