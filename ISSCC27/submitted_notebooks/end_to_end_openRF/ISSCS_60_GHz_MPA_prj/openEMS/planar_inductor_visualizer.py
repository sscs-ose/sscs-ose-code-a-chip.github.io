"""Interactive planar spiral-inductor calculator; needs only Python's standard library.

Run: python3 planar_inductor_visualizer.py
The app opens in the default browser.  Diameter controls are in millimetres and
are converted to metres in the modified Wheeler calculation.
"""
from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Planar Inductor Visualizer</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,sans-serif}body{margin:0;background:Canvas;color:CanvasText}main{max-width:1180px;margin:auto;padding:26px}h1{margin:0;font-size:1.55rem}.intro{margin:.35rem 0 1.25rem;color:GrayText}.top{display:grid;grid-template-columns:minmax(280px,1fr) minmax(260px,.7fr);gap:18px}fieldset{border:1px solid color-mix(in srgb,CanvasText 30%,transparent);border-radius:8px;padding:14px}legend{font-weight:650;padding:0 5px}.constants{display:grid;grid-template-columns:auto 1fr;gap:9px 12px;align-items:center}input[type=number]{width:100%;min-width:0;box-sizing:border-box;font:inherit;padding:5px}.result{display:grid;align-content:center;min-height:118px}#result{color:#087ea4;font-size:2rem;font-weight:700;margin-top:7px}#detail,#error{margin-top:7px}#detail{color:GrayText}#error{color:#b42318;min-height:1.2em}.diameters{margin-top:18px}.slider-row{display:grid;grid-template-columns:180px 1fr 75px;gap:12px;align-items:center;margin:8px 0}input[type=range]{width:100%}.value{font-variant-numeric:tabular-nums;text-align:right}.plots{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}figure{margin:0}canvas{display:block;width:100%;height:300px;border:1px solid color-mix(in srgb,CanvasText 25%,transparent);border-radius:7px;background:#fff}figcaption{font-weight:650;margin:0 0 7px}.formula{margin-top:20px;color:GrayText;font-size:.93rem}@media(max-width:720px){main{padding:16px}.top,.plots{grid-template-columns:1fr}.slider-row{grid-template-columns:1fr 58px;gap:5px 10px}.slider-row label{grid-column:1/3}.slider-row input{grid-column:1}.value{grid-column:2}}
</style></head><body><main>
<h1>Planar spiral inductor</h1><p class="intro">Modified Wheeler calculator. Set the formula constants, then adjust the two diameters.</p>
<section class="top"><fieldset><legend>Formula constants</legend><div class="constants">
<label for="k1">K₁</label><input id="k1" type="number" step="any" value="2.34">
<label for="k2">K₂</label><input id="k2" type="number" step="any" value="2.75">
<label for="mu0">μ₀ (H/m)</label><input id="mu0" type="number" step="any" value="1.2566370614e-6">
<label for="turns">Turns n</label><input id="turns" type="number" step="any" min="0" value="10">
</div></fieldset><fieldset class="result"><legend>Inductance</legend><output id="result" aria-live="polite">—</output><div id="detail"></div><div id="error" role="alert"></div></fieldset></section>
<fieldset class="diameters"><legend>Diameters</legend>
<div class="slider-row"><label for="dout">Outer diameter D<sub>out</sub></label><input id="dout" type="range" min="0.001" max="1" step="0.001" value="0.800"><span id="doutValue" class="value"></span></div>
<div class="slider-row"><label for="din">Inner diameter D<sub>in</sub></label><input id="din" type="range" min="0.001" max="1" step="0.001" value="0.400"><span id="dinValue" class="value"></span></div></fieldset>
<section class="plots"><figure><figcaption>Inductance versus D<sub>out</sub></figcaption><canvas id="outerPlot" aria-label="Inductance over outer diameter"></canvas></figure><figure><figcaption>Inductance versus D<sub>in</sub></figcaption><canvas id="innerPlot" aria-label="Inductance over inner diameter"></canvas></figure></section>
<p class="formula">L ≈ K₁μ₀n²d<sub>avg</sub> / (1 + K₂ρ), &nbsp; d<sub>avg</sub> = (D<sub>out</sub> + D<sub>in</sub>)/2, &nbsp; ρ = (D<sub>out</sub> − D<sub>in</sub>)/(D<sub>out</sub> + D<sub>in</sub>). Diameters are displayed in mm and converted to m.</p>
</main><script>
const $=id=>document.getElementById(id),MIN=0.001,MAX=1;
function params(){return['k1','k2','mu0','turns'].map(id=>Number($(id).value))}
function inductance(k1,k2,mu0,n,dout,din){if(!(dout>din)||!(mu0>0)||n<0)return NaN;const a=dout/1000,b=din/1000,rho=(a-b)/(a+b),den=1+k2*rho;return den===0?NaN:k1*mu0*n*n*((a+b)/2)/den}
function formatH(h){const a=Math.abs(h);if(a>=1e-3)return(h*1e3).toPrecision(6)+' mH';if(a>=1e-6)return(h*1e6).toPrecision(6)+' µH';if(a>=1e-9)return(h*1e9).toPrecision(6)+' nH';return(h*1e12).toPrecision(6)+' pH'}
function axisNum(v){return Math.abs(v)>=1000?(v/1000).toPrecision(3)+' µH':v.toPrecision(3)}
function plot(canvas,points,selected,xlabel,fixed){
 const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*dpr;canvas.height=h*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);const left=59,right=16,top=18,bottom=45,pw=w-left-right,ph=h-top-bottom;
 if(!points.length){c.fillStyle='#b42318';c.font='14px system-ui';c.textAlign='center';c.fillText('Set D_out greater than D_in',w/2,h/2);return}
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),xmin=Math.min(...xs),xmax=Math.max(...xs);let ymin=Math.min(...ys),ymax=Math.max(...ys),pad=(ymax-ymin)*.08||1;ymin-=pad;ymax+=pad;const sx=x=>left+(x-xmin)/(xmax-xmin)*pw,sy=y=>top+(ymax-y)/(ymax-ymin)*ph;
 c.font='11px system-ui';c.fillStyle='#596775';c.strokeStyle='#e6ebf0';c.lineWidth=1;for(let i=0;i<5;i++){let f=i/4,y=top+f*ph,v=ymax-f*(ymax-ymin);c.beginPath();c.moveTo(left,y);c.lineTo(w-right,y);c.stroke();c.textAlign='right';c.fillText(axisNum(v),left-7,y+4)}
 c.strokeStyle='#eef1f4';for(let i=0;i<5;i++){let f=i/4,x=left+f*pw,v=xmin+f*(xmax-xmin);c.beginPath();c.moveTo(x,top);c.lineTo(x,h-bottom);c.stroke();c.textAlign='center';c.fillStyle='#596775';c.fillText(v.toFixed(3),x,h-bottom+16)}
 c.strokeStyle='#8391a1';c.strokeRect(left,top,pw,ph);c.textAlign='left';c.fillStyle='#374151';c.fillText('L (nH)',left,top-5);c.textAlign='center';c.fillText(xlabel,left+pw/2,h-11);c.textAlign='right';c.fillStyle='#596775';c.fillText(fixed,w-right,top-5);
 c.strokeStyle='#087ea4';c.lineWidth=2;c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(sx(x),sy(y)):c.moveTo(sx(x),sy(y)));c.stroke();
 if(selected>=xmin&&selected<=xmax){let p=points.reduce((best,q)=>Math.abs(q[0]-selected)<Math.abs(best[0]-selected)?q:best),x=sx(selected),y=sy(p[1]);c.setLineDash([3,3]);c.strokeStyle='#d06b1b';c.beginPath();c.moveTo(x,top);c.lineTo(x,h-bottom);c.stroke();c.setLineDash([]);c.fillStyle='#d06b1b';c.beginPath();c.arc(x,y,4,0,Math.PI*2);c.fill()}
}
function update(){
 const[k1,k2,mu0,n]=params(),dout=Number($('dout').value),din=Number($('din').value),v=inductance(k1,k2,mu0,n,dout,din);$('doutValue').textContent=dout.toFixed(3)+' mm';$('dinValue').textContent=din.toFixed(3)+' mm';$('result').textContent=Number.isFinite(v)?'L = '+formatH(v):'—';$('detail').textContent=Number.isFinite(v)?'d_avg = '+((dout+din)/2).toFixed(3)+' mm   ·   fill ratio ρ = '+((dout-din)/(dout+din)).toFixed(4):'';$('error').textContent=dout<=din?'D_out must be greater than D_in.':(!Number.isFinite(v)?'Enter valid numeric constants (μ₀ must be positive).':'');
 const outer=[],inner=[];for(let i=0;i<161;i++){const lo=Math.min(MAX-.001,din+.001),do_=lo+(MAX-lo)*i/160,hi=Math.max(MIN,dout-.001),di=MIN+(hi-MIN)*i/160;outer.push([do_,inductance(k1,k2,mu0,n,do_,din)*1e9]);inner.push([di,inductance(k1,k2,mu0,n,dout,di)*1e9])}
 plot($('outerPlot'),outer.filter(p=>Number.isFinite(p[1])),dout,'D_out (mm)','D_in fixed: '+din.toFixed(3)+' mm');plot($('innerPlot'),inner.filter(p=>Number.isFinite(p[1])),din,'D_in (mm)','D_out fixed: '+dout.toFixed(3)+' mm')}
document.querySelectorAll('input').forEach(x=>x.addEventListener('input',update));addEventListener('resize',update);update();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        data = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format: str, *_args: object) -> None:
        pass


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Planar Inductor Visualizer is running at {url}")
    print("Press Ctrl+C in this terminal to stop it.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
