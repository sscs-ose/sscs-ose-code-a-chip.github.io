"""Lightweight evidence checks and figures for the P0 review notebook (no EDA/model calls)."""
from pathlib import Path
import hashlib, json, math, re
ROOT = Path(__file__).resolve().parent
def read(name): return json.loads((ROOT/name).read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def compare_performance(ref,cand):
    keys=("K","mapping","seed","profile","output_stall")
    def index(d):
        assert d["verdict"]=="passed"
        records={tuple(c[k] for k in keys):c for c in d["cases"]}
        assert len(records)==len(d["cases"])==162
        return records
    a,b=index(ref),index(cand)
    assert a.keys()==b.keys()
    rows=[]
    for k,x in a.items():
        y=b[k]
        for field in ("supply_cycles","completion_cycles","useful_bytes"):
            assert isinstance(x[field],int) and isinstance(y[field],int)
            assert x[field]>0 and y[field]>0
        assert x["useful_bytes"]==y["useful_bytes"]
        assert y["supply_cycles"]<=x["supply_cycles"]
        assert y["completion_cycles"]<=x["completion_cycles"]
        rows.append(dict(zip(keys,k),completion_ratio=x["completion_cycles"]/y["completion_cycles"],
            supply_ratio=x["supply_cycles"]/y["supply_cycles"],
            reference_completion_cycles=x["completion_cycles"],P0_completion_cycles=y["completion_cycles"],
            latency_delta_cycles=y["max_latency_cycles"]-x["max_latency_cycles"]))
    return rows
def verify():
    sources=read("sources.json")
    for name,item in sources.items():
        path=(ROOT/name).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(),name
        assert sha(path)==item["sha256"],name
    rows=compare_performance(read("evidence/reference-performance.json"),read("evidence/P0-performance.json"))
    assert rows==read("data/performance-pairs.json")
    candidate=read("evidence/P0-performance.json")
    assert candidate["rtl_digest"]=="sha256:"+sha(ROOT/"design/rtl/lb_feedback.sv")
    arch=read("evidence/P0-architecture-audit.json")
    assert arch["rtl_digest"]==candidate["rtl_digest"] and arch["verdict"]=="passed"
    assert arch["resources"]["L1"]["observed_signed_8x8_products"]==32
    l0mem=arch["resources"]["L0"]["declared_memories"]
    payload=sum(l0mem[n]["bits"] for n in ["input_bank","weight_row","output_bank"])
    payload+=arch["resources"]["L1"]["declared_memories"]["accumulator"]["bits"]
    assert payload==352*8
    links=read("design/link-map.json")
    assert len(links["links"])==727 and links["functional_required"]==725
    assert links["functional_capacity"]==784 and links["capacity_pass"]
    # Compare final DEF pin origins with the link map, rather than the historical audit alone.
    pins={d:{p[0].replace(chr(92),""):p[1:3] for p in read("data/"+d+"-placement.json")["pins"]}
          for d in ["L0","L1"]}
    for link in links["links"]:
        for d in ["L0","L1"]:
            assert pins[d][link[d]]==[link["x"],link["y"]],(d,link["signal"])
    for d in ["L0","L1"]:
        assert sum(n.startswith("FOLD_PG_") for n in pins[d])==800
    L0=read("evidence/L0-qualification.json")
    L1=read("evidence/L1-acceptance.json")
    assert L0["status"]=="passed" and all(L0["checks"].values())
    assert all(v==0 for v in L0["electrical"].values())
    assert L1["status"]=="accepted" and L1["DRC_full_design"]==L1["antenna_nets"]==L1["antenna_pins"]==0
    assert all(v==0 for v in L1["full_local_ERC"].values())
    assert L1["placement"]=="passed" and all(v=="passed" for v in L1["PG"].values())
    for c in L1["joint"]["cases"].values():
        assert c["status"]=="passed" and c["annotation_constraints_path_classes"]=="passed"
        assert all(v==0 for v in c["full_ERC"].values())
        assert all(math.isfinite(c[k]) and c[k]>=0 for k in ["setup_ns","hold_ns"])
    assert set(L1["joint"]["cases"])=={"min","nominal","max"}
    e=read("evidence/L1-export-consistency.json")
    assert e["status"]=="passed" and e["native_exit"]==0
    assert e["per_pin_checks"]==64810 and e["per_pin_database_vs_export_differences"]==0
    for k in ["setup","hold"]:
        assert math.isfinite(L1["local_timing_ns"][k]) and L1["local_timing_ns"][k]>=0
        assert abs(e["exported_worst_slack_ns"][k]-L1["local_timing_ns"][k])<=e["timing_tolerance_ns"]
    assert L1["RCX_geometry_mismatch_nets"]==0
    return dict(source_files_checked=len(sources),performance_pairs=len(rows),endpoint_pairs=727,
        power_pins_each=800,parallel_products=32,payload_bytes=352,
        setup_ns=L1["local_timing_ns"]["setup"],hold_ps=1000*L1["local_timing_ns"]["hold"],
        max_RC_setup_ns=L1["joint"]["cases"]["max"]["setup_ns"],per_pin_ERC_checks=e["per_pin_checks"])
def setup_plots():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,
        "axes.spines.right":False,"figure.facecolor":"white","savefig.facecolor":"white"})
    return plt
def savefig(fig,name):
    plt=setup_plots()
    folder=ROOT/"figures"
    folder.mkdir(exist_ok=True)
    for suffix in ["png","svg"]:
        fig.savefig(folder/(name+"."+suffix),dpi=170,bbox_inches="tight")
    plt.close(fig)
def architecture():
    plt=setup_plots()
    from matplotlib.patches import FancyBboxPatch
    fig,ax=plt.subplots(figsize=(12,7))
    ax.set(xlim=(0,12),ylim=(0,7));ax.axis("off")
    def box(x,y,w,h,text,color):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.08",fc=color,ec="#345"))
        ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=11)
    box(.5,5.7,11, .7,"External memory service: 8 useful channels + 2 repair channels","#e8edf0")
    box(.5,3.5,11,1.4,"CONTROL & STORAGE TIER: configuration + request/response control\n128 B input banks + 128 B weight rows + 64 B output banks","#d7eaf3")
    box(.5,.9,11,1.4,"COMPUTE TIER: 32 signed INT8 products + 8 reductions + 8 INT32 accumulators (32 B)\nHost package ports and clock enter here","#f9e7c7")
    def arrow(x,y,x2,y2,label,style="<->"):
        ax.annotate("",(x2,y2),(x,y),arrowprops={"arrowstyle":style,"color":"#234c60","lw":1.6})
        ax.text((x+x2)/2+.12,(y+y2)/2,label,va="center",fontsize=9)
    arrow(1.1,4.95,1.1,5.6,"Independent requests and responses")
    arrow(1.2,3.4,1.2,2.4,"290 bits down\nX + weights + control","->")
    arrow(5.3,2.4,5.3,3.4,"256 bits up\nnext sums","->")
    arrow(9.0,2.4,9.0,3.4,"179 host bits\n+ clock/reset")
    ax.text(6,.25,"Each logic die: 1 × 1 mm  |  Projected footprint: 1 mm²  |  Total logic silicon: 2 mm²",
        ha="center",fontsize=11,fontweight="bold")
    ax.set_title("Figure 1 · Preserve the computation; move it across a physical boundary",loc="left",pad=16)
    savefig(fig,"01-architecture")
def placement():
    plt=setup_plots()
    from matplotlib.patches import Rectangle
    spec=read("design/folding-spec.json")
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for ax,die in zip(axes,["L0","L1"]):
        d=read("data/"+die+"-placement.json")
        cells=[c for c in d["cells"] if "__fill_" not in c[1] and "__tapvpwrvgnd_" not in c[1] and "__decap_" not in c[1]]
        ax.scatter([c[2] for c in cells],[c[3] for c in cells],s=.35,c="#8f9a9f",rasterized=True,label="Component origins")
        links=read("design/link-map.json")["links"]
        pins={p[0].replace(chr(92),""):p for p in d["pins"]}
        xy=[pins[x[die]][1:3] for x in links]
        ax.scatter([p[0] for p in xy],[p[1] for p in xy],s=3,c="#087d9e",label="727 signal pins")
        pg=[p for p in d["pins"] if p[0].startswith("FOLD_PG_")]
        ax.scatter([p[1] for p in pg],[p[2] for p in pg],s=2,c="#bc6c25",label="800 PG pins")
        for x,y,z,w in spec["geometry"]["link_windows_um"]:
            ax.add_patch(Rectangle((x,y),z-x,w-y,fill=False,ec="#234c60",lw=.8))
        ax.set(xlim=(0,1000),ylim=(0,1000),aspect="equal",xlabel="x (µm)",ylabel="y (µm)",
            title={"L0":"Control & storage tier","L1":"Compute tier"}[die]+" · accepted placement")
        ax.legend(loc="upper center",fontsize=8,markerscale=2)
    fig.suptitle("Figure 2 · Actual final placements and cross-tier pin positions",fontsize=14)
    fig.tight_layout()
    savefig(fig,"02-placement")

def gds_layout():
    """Compose unchanged KLayout view pixels with physical-coordinate annotations."""
    plt=setup_plots()
    from matplotlib.patches import Rectangle, Patch
    d=read("data/gds/render.json")
    for key,v in d["views"].items():
        assert sha(ROOT/"data/gds"/(key+".png"))==v["sha256"]
    for die,name in [("L0","control-storage.gds"),("L1","compute.gds")]:
        assert sha(ROOT/"physical/gds"/name)==d["layouts"][die]["gds_sha256"]
    fig,axes=plt.subplots(2,2,figsize=(12,12),gridspec_kw={"height_ratios":[1,.8]})
    fig.subplots_adjust(left=.055,right=.975,top=.88,bottom=.14,hspace=.24,wspace=.10)
    keys=["L0-full","L1-full","L0-link","L1-diodes"]
    titles=["CONTROL & STORAGE · 1 × 1 mm","COMPUTE · 1 × 1 mm",
            "A · Cross-tier terminal window · 50 × 50 µm",
            "B · Final diode access · 8 × 8 µm"]
    for ax,key,title in zip(axes.flat,keys,titles):
        x0,y0,x1,y1=d["views"][key]["box"]
        ax.imshow(plt.imread(ROOT/"data/gds"/(key+".png")),extent=(x0,x1,y0,y1),origin="upper",interpolation="none")
        ax.set(xlim=(x0,x1),ylim=(y0,y1),aspect="equal")
        ax.set_title(title,loc="left",fontsize=11,pad=11,fontweight="bold")
        ax.axis("off")
        length={"L0-full":200,"L1-full":200,"L0-link":10,"L1-diodes":2}[key]
        x=x0+.06*(x1-x0);y=y0+.06*(y1-y0)
        ax.plot([x,x+length],[y,y],lw=3,color="white",solid_capstyle="butt")
        ax.text(x,y+.025*(y1-y0),str(length)+" µm",color="white",fontsize=8,
                bbox=dict(fc="#0b1323",ec="none",alpha=.85,pad=2))
    windows=read("design/folding-spec.json")["geometry"]["link_windows_um"]
    for ax in axes[0]:
        for x0,y0,x1,y1 in windows:
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec="white",lw=.8,ls="--"))
    axes[0,0].add_patch(Rectangle((20,210),50,50,fill=False,ec="#fff4b3",lw=2))
    axes[0,0].annotate("A",xy=(45,235),xytext=(280,150),color="white",fontsize=13,fontweight="bold",
        bbox=dict(fc="#0b1323",ec="none",pad=3),arrowprops=dict(arrowstyle="->",color="#fff4b3",lw=1.5))
    axes[0,1].add_patch(Rectangle((797,32),8,8,fill=False,ec="#fff4b3",lw=2))
    axes[0,1].annotate("B",xy=(801,36),xytext=(870,165),color="white",fontsize=13,fontweight="bold",
        bbox=dict(fc="#0b1323",ec="none",pad=3),arrowprops=dict(arrowstyle="->",color="#fff4b3",lw=1.5))
    route=read("data/local-route-view.json")
    for name,item in route["diodes"].items():
        x,y=[v/1000 for v in item["access"]]
        axes[1,1].annotate("D"+name.split("_")[-1],xy=(x,y),xytext=(x,39.35),
            ha="center",color="white",fontsize=9,fontweight="bold",
            bbox=dict(fc="#0b1323",ec="none",pad=2),
            arrowprops=dict(arrowstyle="->",color="white",lw=1))
    fig.suptitle("Figure 2 · From the two-tier design to the actual GDS layout",
                 x=.055,y=.975,ha="left",fontsize=17,fontweight="bold")
    fig.text(.055,.933,"Both die views use the same scale and orientation. Dashed boxes mark the four cross-tier interface windows.",
             fontsize=10,color="#526873")
    handles=[Patch(facecolor=d["palette"][str(n)][1],label="M"+str(n-67)) for n in range(68,73)]
    handles.append(Patch(facecolor="#d6dae3",label="Contacts / vias"))
    handles.append(Patch(facecolor="#64748b",label="Device / LI"))
    fig.legend(handles=handles,loc="lower left",bbox_to_anchor=(.055,.085),ncol=7,frameon=False,fontsize=9)
    fig.text(.055,.065,"Overview and A: metal 1–5 and vias. B: device/local-interconnect geometry, metal 1–2 and contacts.",
             fontsize=9,color="#526873")
    fig.text(.055,.043,"D244 and D242 mark the two final diode accesses; Figure 4 explains their +8.16 µm relocation.",
             fontsize=9,color="#526873")
    fig.text(.055,.021,"KLayout renderings of the final layout artifacts · labels and location boxes are explanatory overlays.",
             fontsize=9,color="#526873")
    savefig(fig,"02-gds-layout")

def performance():
    plt=setup_plots()
    import numpy as np
    rows=read("data/performance-pairs.json")
    assert len(rows)==162 and all(r["completion_ratio"]==r["supply_ratio"]==1 for r in rows)
    fig,axes=plt.subplots(1,3,figsize=(12,5.5))
    profiles=["fast","jitter","burst"]
    vmax=max(r["P0_completion_cycles"]/1000 for r in rows)
    for ax,k in zip(axes,[4,16,64]):
        values=[];ranges=[]
        for profile in profiles:
            line=[];bounds=[]
            for stall in [0,1]:
                subset=[r["P0_completion_cycles"]/1000 for r in rows if r["K"]==k and r["profile"]==profile and r["output_stall"]==stall]
                assert len(subset)==9
                line.append(sum(subset)/9);bounds.append((min(subset),max(subset)))
            values.append(line);ranges.append(bounds)
        im=ax.imshow(values,vmin=0,vmax=vmax,cmap="Blues",aspect="auto")
        for y in range(3):
            for x in range(2):
                lo,hi=ranges[y][x];value=values[y][x]
                detail=f"{lo:.3f}–{hi:.3f}" if hi!=lo else "all nine equal"
                ax.text(x,y,f"{value:.3f}\n{detail}",ha="center",va="center",fontsize=10,
                        color="white" if value>vmax*.55 else "#163d51",linespacing=1.6)
        ax.set(xticks=[0,1],xticklabels=["Always ready","Periodic stall"],yticks=[0,1,2],
               yticklabels=["Fast service","Jittered service","Burst service"] if k==4 else [""]*3,
               title=f"K = {k}",xlabel="Output consumer")
        ax.tick_params(length=0)
    fig.subplots_adjust(left=.15,right=.88,bottom=.28,top=.76,wspace=.14)
    cax=fig.add_axes([.91,.28,.015,.48])
    fig.colorbar(im,cax=cax,label="Mean completion interval (cycles/job)")
    fig.suptitle("Figure 3 · Throughput is preserved across all service conditions",x=.06,ha="left",fontsize=15,fontweight="bold")
    fig.text(.06,.85,"Every paired supply and completion throughput ratio = 1.000",fontsize=12,color="#18765e",fontweight="bold")
    fig.text(.06,.10,"Each cell: mean interval, then range over 3 repair mappings × 3 seeds (9 paired scenarios).\n"
             "3 job lengths × 3 service profiles × 2 output conditions × 9 = 162 paired scenarios.",
             fontsize=10,linespacing=1.5,color="#526873")
    savefig(fig,"03-performance")

def joint():
    plt=setup_plots()
    from matplotlib.patches import Rectangle
    d=read("evidence/L1-acceptance.json")
    fig=plt.figure(figsize=(12,8.2))
    fig.suptitle("Figure 5 · Does data arrive inside the allowed time window?",x=.06,ha="left",fontsize=16,fontweight="bold")
    ax=fig.add_axes([.07,.72,.87,.19]);ax.set(xlim=(0,10),ylim=(0,2));ax.axis("off")
    for x,w,color,label in [(0,2,"#fce5e5","Too early"),(2,6,"#e0f1e8","Allowed arrival window"),(8,2,"#fce5e5","Too late")]:
        ax.add_patch(Rectangle((x,.65),w,.45,fc=color,ec="white"))
        ax.text(x+w/2,.875,label,ha="center",va="center",fontsize=11)
    ax.text(2,.38,"Earliest allowed arrival\nHold checks this boundary",ha="center",va="top",fontsize=10)
    ax.text(8,.38,"Latest allowed arrival\nSetup checks this boundary",ha="center",va="top",fontsize=10)
    ax.text(5,1.65,"Conceptual guide · each path has its own timing window",ha="center",color="#526873",fontsize=10)
    ax.text(5,1.3,"A positive margin puts the checked arrival on the safe side.",ha="center",fontsize=11)
    names=["min","nominal","max"]
    labels=["Light link\n0.25 Ω · 15 fF","Nominal link\n0.5 Ω · 50 fF","Heavy link\n1 Ω · 100 fF"]
    for pos,key,scale,xmax,title,unit in [([.24,.30,.30,.33],"setup_ns",1,65,"Margin to the late boundary","ns"),
                                        ([.65,.30,.28,.33],"hold_ns",1000,105,"Margin to the early boundary","ps")]:
        ax=fig.add_axes(pos)
        vals=[d["joint"]["cases"][n][key]*scale for n in names]
        for y,v in enumerate(vals):
            ax.plot([0,v],[y,y],lw=8,color="#c9e5db",solid_capstyle="round")
            ax.scatter(v,y,s=85,c="#18765e",zorder=3)
            ax.text(v+2,y,f"{v:.3f}",va="center",fontsize=11,fontweight="bold",color="#17624f")
        ax.axvline(0,c="#53636d",lw=1)
        ax.set(xlim=(-1,xmax),ylim=(2.6,-.6),yticks=range(3),yticklabels=labels if key=="setup_ns" else [""]*3,
               xlabel=f"Positive margin ({unit})",title=title)
        ax.tick_params(axis="y",length=0,pad=18)
        ax.spines["left"].set_visible(False)
        ax.text(0,-.16,"0 = boundary",transform=ax.get_xaxis_transform(),fontsize=9,color="#53636d")
        ax.grid(axis="x",alpha=.15)
    fig.text(.07,.66,"MEASURED · both tiers connected · all three link models pass",fontsize=12,fontweight="bold",color="#17624f")
    hold=d["local_timing_ns"]["hold"]*1000
    fig.text(.08,.13,f"NEXT ROBUSTNESS CHECK   ·   Compute-tier local hold margin = {hold:.3f} ps",
             fontsize=12,fontweight="bold",color="#8a511a",bbox=dict(boxstyle="round,pad=.9",fc="#fff1df",ec="#edcfaa"))
    fig.text(.08,.055,"The local check uses temporary tier I/O budgets. Test its small margin across process, voltage and temperature.\n"
             "All measured rows above use the same typical cell library: 1.8 V, 25°C, 100 ns clock.  1 ns = 1,000 ps.",
             fontsize=10,color="#526873",linespacing=1.5)
    savefig(fig,"05-joint-timing")

def repair():
    plt=setup_plots()
    from matplotlib.patches import Rectangle, FancyBboxPatch
    moves=read("data/diode-move.json")
    shifts=[m["after_um"][1]-m["before_um"][1] for m in moves.values()]
    assert len(moves)==2 and all(abs(s-8.16)<1e-9 for s in shifts)
    d=read("evidence/L1-acceptance.json")
    fig,axes=plt.subplots(1,2,figsize=(12,7))
    fig.subplots_adjust(top=.77,bottom=.22,wspace=.15)
    fig.suptitle("Figure 4 · Move the protection diodes to clear the route",x=.06,ha="left",fontsize=16,fontweight="bold",y=.98)
    fig.text(.06,.89,"Why add a diode?  It drains manufacturing charge from a long routed signal wire.\n"
             "The added contact must also fit beside existing metal.",fontsize=11,linespacing=1.5,color="#40545f")
    for ax,after in zip(axes,[False,True]):
        ax.set(xlim=(0,10),ylim=(0,6));ax.axis("off")
        ax.set_title("AFTER · connect beside the same signal wire" if after else "BEFORE · the contact branch crosses a neighbor",
                     fontsize=11,fontweight="bold",loc="left",pad=14,color="#18765e" if after else "#aa3a3a")
        ax.plot([.4,9.2],[4.55,4.55],c="#167e9c",lw=6,solid_capstyle="round")
        ax.text(.4,5.15,"Existing host-output signal wire",color="#156a84",fontsize=10)
        ax.add_patch(Rectangle((.4,2.35),8.8,.45,fc="#89949d"))
        ax.text(.45,1.95,"Fixed neighboring metal",color="#5e6b74",fontsize=10)
        for x in [3.5,6.4]:
            y=3.35 if after else .65
            ax.plot([x,x],[4.55,y+.65],c="#167e9c",lw=3)
            ax.add_patch(FancyBboxPatch((x-.85,y),1.7,.65,boxstyle="round,pad=.04",fc="#f8e5c6",ec="#b16b22",lw=1.4))
            ax.text(x,y+.325,"Diode",ha="center",va="center",fontsize=10,color="#754812")
            if not after:
                ax.scatter(x,2.57,s=420,facecolors="none",edgecolors="#c23f42",linewidths=2,zorder=5)
                ax.text(x,2.57,"×",c="#c23f42",ha="center",va="center",fontsize=20,zorder=6)
        if after:
            ax.text(5,.75,"Short contacts reach the existing wire;\nold conflicting branches are removed.",
                    ha="center",fontsize=10,color="#18765e",linespacing=1.5)
        else:
            ax.text(5,-.05,"Red circles: local metal conflicts",ha="center",fontsize=10,color="#aa3a3a")
    fig.text(.06,.14,f"MEASURED CHANGE    {len(moves)} diodes moved +{shifts[0]:.2f} µm in y    ·    1 signal route changed",
             fontsize=12,fontweight="bold",color="#254653")
    fig.text(.06,.085,f"FINAL CHECKS    Full-design routing violations: {d['DRC_full_design']}    ·    Antenna-violating nets: {d['antenna_nets']}",
             fontsize=11,fontweight="bold",color="#18765e")
    fig.text(.06,.025,"Mechanism schematic · geometry not to scale. Actual diode coordinates and final route are included in the evidence.",
             fontsize=9,color="#596c76")
    savefig(fig,"04-local-repair")
    route_detail()


def route_detail():
    plt=setup_plots()
    from matplotlib.patches import Rectangle
    d=read("data/local-route-view.json")
    fig,axes=plt.subplots(1,2,figsize=(11,7.0),gridspec_kw={"width_ratios":[1.2,1]})
    colors={"met1":"#137c91","met2":"#8656a2"}
    ax=axes[0]
    seen=set()
    for seg in d["segments"]:
        layer=seg["layer"];a,b=seg["xy_um"]
        ax.plot([a[0],b[0]],[a[1],b[1]],c=colors[layer],lw=2,
                label=layer+" centerline" if layer not in seen else None);seen.add(layer)
    moves=read("data/diode-move.json")
    for name,diode in d["diodes"].items():
        before=moves[name]["before_um"];after=moves[name]["after_um"]
        ax.scatter(*before,c="#bd4545",marker="x",s=50)
        ax.scatter(*after,c="#bd7726",s=45)
        ax.annotate("",xy=after,xytext=before,arrowprops=dict(arrowstyle="->",ls=":",color="#bd7726"))
    ax.set(xlim=(798,805),ylim=(26,39),aspect="equal",xlabel="x (µm)",ylabel="y (µm)",title="Measured route and diode origins")
    ax.legend(fontsize=8,loc="upper left")
    ax=axes[1];ax.set(xlim=(800.2,802.25),ylim=(35.1,38.1),aspect="equal",xlabel="x (µm)",ylabel="y (µm)",title="Zoom: final diode access metal")
    ax.plot([800.2,802.25],[37.57,37.57],color=colors["met1"],lw=3,label="Existing met1 route")
    for name,diode in d["diodes"].items():
        for layer,box in diode["shapes"]:
            a,b,c,e=[v/1000 for v in box]
            ax.add_patch(Rectangle((a,b),c-a,e-b,facecolor="#d8bd8d" if layer=="li1" else "#137c91",
                                  alpha=.35,edgecolor="#8b6126" if layer=="li1" else "#137c91"))
        x,y=[v/1000 for v in diode["access"]]
        ax.scatter(x,y,s=35,c="#18765e",zorder=4)
        ax.text(x,38.0,name.replace("R3A2_","diode "),ha="center",fontsize=8)
    ax.text(801.23,35.2,"Shaded: recorded li1 / met1 shapes",ha="center",fontsize=8)
    fig.suptitle("Figure 4b · Connect the repair mechanism to measured geometry",x=.06,ha="left",fontsize=14,fontweight="bold")
    fig.text(.06,.10,"× old origin     ● accepted origin     dotted arrows: +8.16 µm in y\n"
             "Host-output net link_out_data[46] · route centerlines and diode access shapes, in µm.\n"
             "The crop displays this net and its two diode accesses; surrounding nets and full mask layers are omitted.",
             fontsize=10,color="#526873",linespacing=1.5)
    fig.subplots_adjust(top=.84,bottom=.30,wspace=.3)
    savefig(fig,"04-route-detail")

def path_evidence():
    raw=(ROOT/"evidence/final-joint-nominal.log").read_text()
    part=raw.split("CLOSURE_PATH_CLASS L0->L1->L0\n")[1].split("CLOSURE_PATH_CLASS L1->L0->L1")[0]
    block=next(b for b in re.split(r"(?=^Startpoint: )",part,flags=re.M) if "Path Type: max" in b)
    source=re.search(r"^Startpoint: (\S+)",block,re.M)[1]
    sink=re.search(r"^Endpoint: (\S+)",block,re.M)[1]
    rows=[(float(m[2]),m[3]) for m in re.finditer(r"^\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+[\^v]\s+(L[01]/\S+)",
        block.split("data arrival time")[0],re.M)]
    begin=next(i for i,r in enumerate(rows) if r[1]==source+"/Q")
    rows=rows[begin:]
    changes=[i for i in range(1,len(rows)) if rows[i][1][:2]!=rows[i-1][1][:2]]
    assert len(changes)==2 and [rows[i][1][:2] for i in [0,*changes]]==["L0","L1","L0"]
    def metric(name):
        return float(re.search(r"^\s*([-+0-9.eE]+)\s+"+name,block,re.M)[1])
    arrival,required,slack=[metric(n) for n in ["data arrival time","data required time",r"slack \("]]
    assert all(math.isfinite(x) for x in [arrival,required,slack])
    assert abs(required-arrival-slack)<1e-5
    assert rows[-1][1]==sink+"/D" and abs(rows[-1][0]-arrival)<1e-8
    # Group by observed endpoint outputs; crossing intervals include wire and receiver delay.
    a,b=changes
    marks=[rows[i] for i in [0,a-1,a,b-1,b,len(rows)-1]]
    delays=[marks[i+1][0]-marks[i][0] for i in range(5)]
    assert all(x>=0 for x in delays) and abs(sum(delays)-(arrival-marks[0][0]))<1e-8
    assert "consume_tile" in source and "output_bank" in sink
    return dict(source=source,sink=sink,marks=marks,delays=delays,arrival=arrival,required=required,slack=slack)

def path():
    plt=setup_plots()
    from matplotlib.patches import FancyBboxPatch
    d=path_evidence()
    fig=plt.figure(figsize=(12,7.6))
    fig.suptitle("Figure 6 · Follow one signal out to the compute tier and back",x=.06,ha="left",fontsize=16,fontweight="bold")
    fig.text(.06,.88,"A compute-enable register changes → input-selection logic responds → arithmetic evaluates → output is stored.",
             fontsize=10.5,color="#40545f")
    ax=fig.add_axes([.06,.48,.88,.35]);ax.set(xlim=(0,12),ylim=(0,4));ax.axis("off")
    blocks=[(.1,"CONTROL & STORAGE","Launch: compute enable\nSelect the input value", "#deeff6"),
            (4.5,"COMPUTE","Evaluate arithmetic\nForm the next output sum","#fbe9cc"),
            (8.9,"CONTROL & STORAGE","Capture the result\nOutput-bank register","#deeff6")]
    for x,title,body,color in blocks:
        ax.add_patch(FancyBboxPatch((x,1.15),3,.95,boxstyle="round,pad=.08",fc=color,ec="#8b9aa4"))
        ax.text(x+1.5,2.5,title,ha="center",fontsize=10,fontweight="bold",color="#254653")
        ax.text(x+1.5,1.625,body,ha="center",va="center",fontsize=10,linespacing=1.5)
    for x,label in [(3.15,"Input bit\ncrosses down"),(7.55,"Result bit\nreturns up")]:
        ax.annotate("",(x+1.25,1.65),(x,1.65),arrowprops=dict(arrowstyle="->",lw=2,color="#254653"))
        ax.text(x+.62,3.1,label,ha="center",fontsize=9,linespacing=1.4)
    times=[f"{v:.3f} ns" for v in d["delays"]]
    for x,t,label in zip([1.6,3.78,6,8.18,10.4],times,["Input selection","Wire + receiver","Arithmetic + TX","Wire + receiver","Return to capture"]):
        ax.text(x,.65,t,ha="center",fontsize=12,fontweight="bold",color="#254653")
        ax.text(x,.16,label,ha="center",fontsize=8.5,color="#526873")
    ax=fig.add_axes([.08,.21,.84,.19])
    a,r,s=d["arrival"],d["required"],d["slack"]
    ax.barh([0],[a],height=.42,color="#167e9c")
    ax.barh([0],[r-a],left=a,height=.42,color="#cde9db")
    ax.text(a/2,0,f"Arrival\n{a:.3f} ns",ha="center",va="center",color="white",fontsize=11,fontweight="bold")
    ax.text(a+(r-a)/2,0,f"Time remaining before the deadline: {s:.3f} ns",ha="center",va="center",fontsize=12,color="#17624f")
    ax.axvline(r,c="#53636d",lw=1)
    ax.text(r,.42,f"Required by {r:.3f} ns",ha="right",fontsize=10)
    ax.set(xlim=(0,105),ylim=(-.7,.65),yticks=[],xlabel="Time from the launch clock's reference edge (ns)")
    for side in ["left","top","right"]:ax.spines[side].set_visible(False)
    fig.text(.08,.10,f"Register Q changes at {d['marks'][0][0]:.3f} ns; the five segments then add {sum(d['delays']):.3f} ns.\n"
             "The deadline includes the propagated capture clock, setup requirement and 1 ns clock uncertainty.",
             fontsize=10,color="#526873",linespacing=1.5)
    fig.text(.08,.025,"Measured nominal-link example · typical library, 100 ns clock. Figure 5 reports the worst margins across the full design.",
             fontsize=9,color="#526873")
    savefig(fig,"06-cross-tier-path")

def figures():
    verify()
    for fn in [architecture,placement,gds_layout,performance,repair,joint,path]:fn()
    return [str(p.relative_to(ROOT)) for p in sorted((ROOT/"figures").glob("*.png"))]
if __name__=="__main__":
    import sys
    print(json.dumps(verify(),indent=2))
    if "--figures" in sys.argv: print("\n".join(figures()))
