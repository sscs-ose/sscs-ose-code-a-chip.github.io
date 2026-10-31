"""Source text embedded into the notebook: transistor symbols and device anatomy."""

SCHEMATIC_CODE=r'''def edu_nmos(ax,x,y,gate,instance,color='#202124',body_text='B → VSUBS'):
    # Four-terminal enhancement NMOS. D/S wires meet a three-segment channel;
    # the gate is isolated, and the body arrow points into the n-channel.
    channel=x-.18;gate_x=x-.58
    ax.plot([x,x,channel],[y+.72,y+.40,y+.40],color=color,lw=1.7)
    ax.plot([channel,x,x],[y-.40,y-.40,y-.72],color=color,lw=1.7)
    for a,b in [(-.40,-.18),(-.09,.09),(.18,.40)]:
        ax.plot([channel,channel],[y+a,y+b],color=color,lw=2.4)
    ax.plot([gate_x,gate_x],[y-.43,y+.43],color='#202124',lw=1.8)
    ax.plot([x-1.55,gate_x],[y,y],color='#202124',lw=1.5)
    ax.text(x-.65,y+.58,gate,ha='right',va='center',fontsize=10,weight='bold')
    ax.plot([x+.78,x+.26],[y,y],color='#202124',lw=1.3)
    ax.annotate('',xy=(channel+.02,y),xytext=(x+.28,y),
        arrowprops=dict(arrowstyle='-|>',lw=1.2,color='#202124',mutation_scale=9))
    ax.text(x+.90,y+.12,body_text,fontsize=8.5,va='bottom')
    ax.text(x+.35,y-.58,instance,fontsize=9,va='top',color='#475569')

def edu_draw_leaf():
    fig,ax=plt.subplots(figsize=(16,8.5))
    ax.set(xlim=(0,25),ylim=(0,12));ax.axis('off')
    ax.text(12.5,11.6,'Differential ternary CIM compute cell — 8 NMOS',
            ha='center',fontsize=19,weight='bold')
    ax.text(12.5,10.95,'Four series discharge branches; weight gates select w, wordline gates select sign(A)',
            ha='center',fontsize=11,color='#475569')
    positions=[3.2,8.7,15.0,20.5]
    meanings=['(+w, +A)','(−w, −A)','(−w, +A)','(+w, −A)']
    for i,(tag,bl,wgate,agate,middle) in enumerate(EDU_BRANCHES):
        x=positions[i];color='#175a8b' if bl=='BLP' else '#a45b21'
        ax.plot([x,x],[9.8,8.32],color=color,lw=1.8)
        ax.plot([x,x],[6.88,4.92],color=color,lw=1.8)
        ax.plot([x,x],[3.48,1.55],color=color,lw=1.8)
        edu_nmos(ax,x,7.6,wgate,f'X{tag}_W',color)
        edu_nmos(ax,x,4.2,agate,f'X{tag}_A',color)
        ax.plot(x,5.9,'o',color=color,ms=3)
        ax.text(x+.22,5.93,middle,fontsize=10,va='bottom',weight='bold')
        ax.text(x,10.22,f'{tag}: {meanings[i]}',ha='center',fontsize=11,color=color)
        ax.annotate('',xy=(x,8.6),xytext=(x,9.2),arrowprops=dict(arrowstyle='->',lw=1.2,color=color))
    for x1,x2,label,col in [(positions[0],positions[1],'BLP  / positive product','#175a8b'),
                              (positions[2],positions[3],'BLN  / negative product','#a45b21')]:
        ax.plot([x1,x2],[9.8,9.8],color=col,lw=2.0)
        ax.text((x1+x2)/2,9.9,label,ha='center',fontsize=12,weight='bold',color=col)
    ax.plot([positions[0],positions[-1]],[1.55,1.55],color='#202124',lw=1.8)
    ax.plot([12,12],[1.55,1.2],color='#202124',lw=1.6)
    for y,w in [(1.2,.6),(1.02,.4),(.84,.2)]:ax.plot([12-w,12+w],[y,y],color='#202124',lw=1.5)
    ax.text(13,1.0,'VGND',fontsize=11,va='center')
    ax.text(12.5,.35,'W/L = 0.84/0.15 µm for every NMOS; all B terminals → VSUBS; ΔV = V(BLN) − V(BLP)',
        ha='center',fontsize=11)
    fig.tight_layout()
    for suffix in ('svg','pdf','png'):
        fig.savefig(EDU_OUT/('ternary_cell_paper.'+suffix),dpi=180,bbox_inches='tight')
    fig.savefig(EDU_OUT/'ternary_cell.svg',bbox_inches='tight')
    fig.savefig(EDU_OUT/'ternary_cell.png',dpi=180,bbox_inches='tight')
    plt.show();plt.close(fig)
edu_draw_leaf()
'''

DEVICE_MARKDOWN=r'''### F2 — Phóng to một NMOS: ký hiệu điện, mặt bằng và mặt cắt

Ba hình sau giải thích cùng một thiết bị `sky130_fd_pr__nfet_01v8` của leaf:

- **Ký hiệu bốn cực:** D (drain), G (gate), S (source), B (bulk/body). Gate cách
  điện với kênh; kênh ngắt đoạn chỉ MOS tăng cường. Mũi tên body hướng vào kênh n.
- **Mặt bằng khái niệm:** active chứa vùng source/drain, poly cắt active tạo gate,
  contact đưa các vùng này lên metal; p+ tap nối body về VSUBS. W là bề rộng kênh,
  L là chiều dài kênh dưới gate, tại source bằng0.84/0.15µm.
- **Mặt cắt khái niệm:** source/drain n+ nằm trong p-substrate, gate oxide ngăn
  điện cực gate khỏi bán dẫn; khi VGS đủ lớn, kênh dẫn hình thành dưới gate.

Hình cấu trúc dùng để giải thích lớp và các cực, **không vẽ theo tỉ lệ và không
phải polygon GDS trích từ layout**. Hình GDS thật của macro được đọc bằng KLayout
ở các cell render phía sau. SVG/PDF giữ nét vector để phóng to hoặc đưa vào paper.
'''

DEVICE_CODE=r'''def edu_draw_device():
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,3,figsize=(17,5.4))
    for ax in axes:ax.set(xlim=(0,10),ylim=(0,7));ax.axis('off')
    a,b,c=axes
    a.set_title('(a) Four-terminal enhancement NMOS',fontsize=12,weight='bold')
    edu_nmos(a,4.8,3.55,'G / gate','sky130_fd_pr__nfet_01v8',body_text='B / bulk')
    a.plot([4.8,4.8],[4.27,5.4],color='#202124',lw=1.7)
    a.plot([4.8,4.8],[2.83,1.65],color='#202124',lw=1.7)
    a.text(4.8,5.6,'D / drain',ha='center',fontsize=11)
    a.text(4.8,1.2,'S / source',ha='center',fontsize=11)
    a.text(5,.45,'W = 0.84 µm    L = 0.15 µm',ha='center',fontsize=11)

    b.set_title('(b) Conceptual top view',fontsize=12,weight='bold')
    b.add_patch(Rectangle((1.2,2.3),7,2.0,facecolor='#b9d8ac',edgecolor='#355d35',lw=1.5))
    b.add_patch(Rectangle((4.25,1.6),.6,3.7,facecolor='#d88788',edgecolor='#8c3636',lw=1.2))
    for x,lab in [(2.1,'S'),(6.8,'D')]:
        b.add_patch(Rectangle((x-.55,2.9),1.1,.75,facecolor='#b5d3e8',edgecolor='#306586'))
        for dx in (-.27,0,.27):
            b.add_patch(Rectangle((x+dx-.07,3.14),.14,.14,facecolor='#30363a'))
        b.text(x,3.9,lab,ha='center',fontsize=11,weight='bold')
    b.add_patch(Rectangle((4.35,4.7),.4,.4,facecolor='#b5d3e8',edgecolor='#306586'))
    b.add_patch(Rectangle((4.48,4.83),.14,.14,facecolor='#30363a'))
    b.text(5.05,5.05,'G / poly + contact',fontsize=9,va='center')
    b.add_patch(Rectangle((1.3,.7),1.1,.7,facecolor='#d5ba9d',edgecolor='#73563b'))
    b.add_patch(Rectangle((1.7,.96),.2,.2,facecolor='#30363a'))
    b.text(2.6,1.0,'B: p+ tap → VSUBS',fontsize=9,va='center')
    b.annotate('',xy=(8.65,4.3),xytext=(8.65,2.3),arrowprops=dict(arrowstyle='<->',lw=1))
    b.text(8.9,3.3,'W',fontsize=11,va='center')
    b.annotate('',xy=(4.85,5.7),xytext=(4.25,5.7),arrowprops=dict(arrowstyle='<->',lw=1))
    b.text(4.55,5.92,'L',fontsize=11,ha='center')
    b.text(4.8,.13,'Green: active; red: poly; blue: metal; black: contact',ha='center',fontsize=8.2)

    c.set_title('(c) Conceptual cross-section',fontsize=12,weight='bold')
    c.add_patch(Rectangle((.9,.95),8,2.5,facecolor='#ead9c4',edgecolor='#73563b',lw=1.2))
    c.add_patch(Rectangle((1.5,2.25),1.6,1.2,facecolor='#b9d8ac',edgecolor='#355d35'))
    c.add_patch(Rectangle((5.8,2.25),1.6,1.2,facecolor='#b9d8ac',edgecolor='#355d35'))
    c.add_patch(Rectangle((3.1,3.47),2.7,.14,facecolor='#d3d7db',edgecolor='#737b83'))
    c.add_patch(Rectangle((3.1,3.64),2.7,.5,facecolor='#d88788',edgecolor='#8c3636'))
    c.plot([3.1,5.8],[3.34,3.34],'--',color='#267c74',lw=2)
    for x,y,label in [(2.3,3.45,'S'),(6.6,3.45,'D'),(4.45,4.14,'G')]:
        c.plot([x,x],[y,5.05],color='#306586',lw=2.2)
        c.text(x,5.3,label,ha='center',fontsize=11,weight='bold')
    c.text(2.3,2.65,'n+',ha='center',fontsize=12);c.text(6.6,2.65,'n+',ha='center',fontsize=12)
    c.text(4.8,1.55,'p-substrate / B → VSUBS',ha='center',fontsize=10)
    c.annotate('gate oxide',xy=(5.5,3.53),xytext=(7,4.35),fontsize=9,
        arrowprops=dict(arrowstyle='->',lw=.8))
    c.annotate('channel when VGS is high',xy=(4.4,3.34),xytext=(3,2.02),fontsize=8.5,
        arrowprops=dict(arrowstyle='->',lw=.8))
    c.text(5,.35,'Device structure illustration — not drawn to scale',ha='center',fontsize=9,color='#475569')
    fig.tight_layout()
    for suffix in ('svg','pdf','png'):
        fig.savefig(EDU_OUT/('nmos_device_anatomy.'+suffix),dpi=180,bbox_inches='tight')
    plt.show();plt.close(fig)
edu_draw_device()
'''
