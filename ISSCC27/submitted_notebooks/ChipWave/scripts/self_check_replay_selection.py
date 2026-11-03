"""The reproduction representative follows time order, never the best PPA."""
from replay_benchmark_study import first_per_workflow

def check():
    def row(flow,repeat,candidates):
        return dict(job=dict(workflow=flow,repetition=repeat,id=f"{flow}-{repeat}"),
                    candidates=[dict(candidate_index=i,rank_eligible=ok,score=score) for i,ok,score in candidates])
    data=dict(rows=[row("F0",2,[(1,True,0.5)]),row("F0",1,[(1,False,0.1),(2,True,1.2),(3,True,1.1)]),
                    row("F1",1,[(1,False,0.1)]),row("F2",1,[(1,True,1.0)])])
    selected=first_per_workflow(data)
    assert [(session,candidate["candidate_index"]) for candidate,session in selected]==[("F0-1",2),("F2-1",1)]
    assert first_per_workflow(dict(rows=[]))==[]
    print("FIRST_QUALIFIED_REPLAY_SELECTION_PASS")

if __name__=="__main__":check()
