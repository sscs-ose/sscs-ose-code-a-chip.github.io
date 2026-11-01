import { element as el, svgElement as svg } from './dom.js';

const NS_PER_UNIT = {s:1e9,ms:1e6,us:1e3,ns:1,ps:0.001,fs:0.000001};
const decimal = (value, width) => {
  const text=String(value); if (/^[01xz]*[xz][01xz]*$/i.test(text)) return text.toUpperCase();
  return BigInt.asUintN(width,BigInt(text)).toString();
};
export function parseVCD(text, aliases={}) {
  if (text.length>32*1024*1024) throw Error('VCD exceeds the 32 MiB viewer limit.');
  const scale=text.match(/\$timescale\s+(1|10|100)\s*(s|ms|us|ns|ps|fs)\s+\$end/);
  const end=text.indexOf('$enddefinitions'); if (!scale||end<0) throw Error('VCD timescale or declarations are missing.');
  const header=text.slice(0,end), signals=[], byCode=new Map();
  for(const match of header.matchAll(/\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(.*?)\s+\$end/g)) {
    const width=Number(match[2]), original=match[4].split(/\s/)[0];
    if(!Number.isInteger(width)||width<1||width>4096) throw Error('Unsupported VCD signal width.');
    const row={name:aliases[original]||original,original,width,kind:'VCD observed',events:[]};
    signals.push(row); if(!byCode.has(match[3])) byCode.set(match[3],[]); byCode.get(match[3]).push(row);
  }
  if(!signals.length||signals.length>256) throw Error('The viewer requires 1–256 declared signals; no signals were silently discarded.');
  const headerEnd=text.indexOf('$end',end+'$enddefinitions'.length);
  if(headerEnd<0)throw Error('VCD declaration terminator is missing.');
  const body=text.slice(headerEnd+4).trim().split(/\s+/); let time=0,maxTime=0,count=0;
  const factor=Number(scale[1])*NS_PER_UNIT[scale[2]];
  for(let i=0;i<body.length;i++) {
    const token=body[i]; if(!token)continue;
    if(token[0]==='#') {const ticks=Number(token.slice(1)); if(!Number.isSafeInteger(ticks)||ticks<0||ticks*factor<time)throw Error('Unsupported or nonmonotonic VCD timestamp.');time=ticks*factor;maxTime=Math.max(maxTime,time);continue;}
    if(token[0]==='$') {if(!['$end','$dumpvars','$dumpall','$dumpon','$dumpoff'].includes(token)){while(i<body.length&&body[i]!=='$end')i++;}continue;}
    let code,bits;
    if(/^[bB]/.test(token)){bits=token.slice(1);code=body[++i];}
    else if(/^[01xXzZ]/.test(token)){bits=token[0];code=token.slice(1);}
    else throw Error('Unsupported VCD value encoding; no waveform was fabricated.');
    if(!/^[01xz]+$/i.test(bits)||!byCode.has(code))throw Error('Malformed or undeclared VCD value.');
    if(++count>200000)throw Error('VCD exceeds the 200,000-change viewer limit; no truncated trace is shown.');
    for(const row of byCode.get(code)) {
      if(bits.length>row.width)throw Error('VCD value exceeds declared width.');
      const value=/[xz]/i.test(bits)?bits.toUpperCase():BigInt('0b'+bits).toString();
      if(row.events.at(-1)?.time===time)row.events.pop();row.events.push({time,value});
    }
  }
  return {signals,end:maxTime};
}

export function waveformModel(data) {
  const ports=data.interface?.ports||[], timing=data.timing, vectors=data.vectors||[], rows=[], mismatches=[];let comparisons=0,missing=0;
  const aliases=Object.fromEntries(ports.map((p,i)=>['hc_p'+i,p.name]));
  const vcd=data.vcd?parseVCD(data.vcd,aliases):null;
  if(vcd)rows.push(...vcd.signals.map(r=>({...r,end:vcd.end})));
  const period=timing?.period_ps/1000, half=timing?.half_period_ps/1000, offset=timing?.sample_after_rising_ps/1000;
  const sampleTime=cycle=>cycle*period+half+offset;
  if(vectors.length&&(!Number.isFinite(period)||!Number.isFinite(half)||!Number.isFinite(offset)||period<=0))throw Error('Saved cycle timing is unavailable.');
  const observed=new Map((data.samples||[]).map(r=>[r.cycle+'\0'+r.signal,r.value]));
  for(const p of ports) {
    if(!vcd&&p.direction==='input') {
      const events=[];
      if(p.name===data.interface.clock.port)for(let c=0;c<vectors.length;c++){events.push({time:c*period,value:'0'},{time:c*period+half,value:'1'});}
      else vectors.forEach((v,c)=>events.push({time:c*period,value:String(p.name===data.interface.reset.port?(data.interface.reset.active==='high'?v.reset:1-Number(v.reset)):v.drive[p.name]??'X')}));
      rows.push({name:p.name,width:p.width,kind:'Saved stimulus',events});
    }
    if(p.direction==='output') {
      const expected=[], actual=[];
      vectors.forEach((v,c)=>{
        if(!Object.hasOwn(v.expect,p.name))return;
        const time=sampleTime(c), value=decimal(v.expect[p.name],p.width);
        const seen=vcd?(time<=vcd.end?vcd.signals.find(r=>r.name===p.name)?.events.findLast(e=>e.time<=time)?.value:undefined):observed.get(c+'\0'+p.name);
        expected.push({time,value,cycle:c});
        if(seen!==undefined) {
          comparisons++;
          const actualValue=decimal(seen,p.width);actual.push({time,value:actualValue,cycle:c});
          if(actualValue!==value)mismatches.push({cycle:c,time,signal:p.name,expected:value,actual:actualValue});
        }else missing++;
      });
      if(!vcd)rows.push({name:p.name,width:p.width,kind:'Observed samples',events:actual,sampled:true});
      rows.push({name:p.name+' · expected',width:p.width,kind:'Saved expected samples',events:expected,sampled:true});
    }
  }
  if(!rows.length)throw Error('This record contains no displayable waveform or observations.');
  return {rows,mismatches,comparisons,missing,end:Math.max(vcd?.end||0, vectors.length*period||0,1),period,
    mode:vcd?'Saved VCD transitions + independent expected samples':'Saved cycle samples + declared stimulus (no continuous output trace retained)'};
}

export class WaveformViewer {
  constructor(callbacks){this.callbacks=callbacks;this.views=new Map();}
  key(group,run){return JSON.stringify([this.callbacks.identity(),group,run?.id,run?.record_hash]);}
  mount(host,group,run){
    if(!host||!run)return;
    const key=this.key(group,run);if(!this.views.has(key))this.views.set(key,{data:null,busy:false,error:'',filter:'',hidden:new Set(),zoom:1,cursor:0});
    const d=this.views.get(key),card=el('section',{class:'card waveform-card','data-testid':'waveform-card'});
    const draw=()=>{if(!card.isConnected)return;this.render(card,d,key);};
    const load=async()=>{
      if(d.busy)return;d.busy=true;d.error='';draw();
      try{const data=await this.callbacks.request(`inspection/waveform/${group}/${encodeURIComponent(run.id)}`);
        if(this.key(group,this.callbacks.selected(group))!==key)return;
        d.model=waveformModel(data);d.data=data;d.cursor=d.model.period?d.model.period/2+(data.timing.sample_after_rising_ps/1000):0;
      }catch(e){d.error=e.message;}finally{d.busy=false;if(this.key(group,this.callbacks.selected(group))===key){this.callbacks.refresh(group);}}
    };
    d.load=load;host.append(card);this.render(card,d,key);
  }
  render(card,d,key){
    card.replaceChildren(el('h3',{text:'Simulation waveform'}),el('p',{class:'scope-note',text:'Read-only saved evidence. Opening, filtering and zooming start no simulation and save no project files.'}),
      el('button',{type:'button',text:d.data?'Reload saved waveform':'Open saved waveform','data-testid':'waveform-open',disabled:d.busy,onclick:d.load}));
    if(d.busy)card.append(el('p',{role:'status',text:'Reading saved waveform evidence…'}));
    if(d.error)card.append(el('p',{role:'alert',class:'generation-error',text:d.error}));
    if(!d.data)return;
    const model=d.model,choices=el('div',{class:'waveform-signals','data-testid':'waveform-signals'}),plot=el('div',{class:'waveform-scroll','data-testid':'waveform-scroll'}),values=el('div',{'data-testid':'waveform-values'});
    const redraw=()=>{this.chart(plot,values,d);};
    const renderChoices=()=>{choices.replaceChildren(...model.rows.filter(r=>r.name.toLowerCase().includes(d.filter.toLowerCase())).map((r,i)=>{
      const id=model.rows.indexOf(r);return el('label',{},el('input',{type:'checkbox',checked:!d.hidden.has(id),'aria-label':`Show ${r.name} (${r.kind})`,onchange:e=>{e.target.checked?d.hidden.delete(id):d.hidden.add(id);redraw();}}),`${r.name} · ${r.kind}`);
    }));};
    const zoom=mult=>{d.zoom=Math.max(1,Math.min(16,d.zoom*mult));redraw();};
    card.append(el('p',{'data-testid':'waveform-mode',text:model.mode}),el('details',{},el('summary',{text:'Waveform source and scope'}),el('p',{class:'scope-note',text:d.data.limits}),
      el('p',{text:`Source ${d.data.run_id} · ${d.data.source_sha256}${d.data.vcd_sha256?' · VCD '+d.data.vcd_sha256:''}`})),
      el('div',{class:'provider-actions'},el('button',{type:'button',text:'Zoom in','data-testid':'waveform-zoom-in',onclick:()=>zoom(2)}),el('button',{type:'button',text:'Zoom out',onclick:()=>zoom(.5)}),el('button',{type:'button',text:'Fit waveform','data-testid':'waveform-fit',onclick:()=>{d.zoom=1;redraw();}}),
        el('button',{type:'button',text:'Show all signals',onclick:()=>{d.hidden.clear();renderChoices();redraw();}}),el('button',{type:'button',text:'Hide all signals',onclick:()=>{d.hidden=new Set(model.rows.map((_,i)=>i));renderChoices();redraw();}})),
      el('details',{'data-testid':'waveform-signal-options'},el('summary',{text:`Select signals (${model.rows.length})`}),el('label',{},'Find signal',el('input',{type:'search','data-testid':'waveform-filter',value:d.filter,oninput:e=>{d.filter=e.target.value;renderChoices();}})),choices),
      el('label',{},'Cursor (ns)',el('input',{type:'range',min:0,max:model.end,step:'any',value:d.cursor,'data-testid':'waveform-cursor',oninput:e=>{d.cursor=Number(e.target.value);redraw();}})),
      el('p',{'data-testid':'waveform-comparison',text:`Viewer output comparisons: ${model.comparisons}. Mismatches: ${model.mismatches.length}. Missing observations: ${model.missing}. Expected values never replace missing observations.`}),
      model.mismatches.length?el('button',{type:'button',text:'Go to first mismatch','data-testid':'waveform-first-mismatch',onclick:()=>{d.cursor=model.mismatches[0].time;redraw();}}):el('span',{text:'No mismatch in the retained comparisons.'}),plot,values);
    renderChoices();redraw();
  }
  chart(host,values,d){
    const {model}=d, rows=model.rows.filter((_,i)=>!d.hidden.has(i)),width=Math.max(360,host.clientWidth||800)*d.zoom,left=205,height=52+rows.length*37, span=width-left-20;
    const x=t=>left+t/model.end*span, picture=svg('svg',{width,height,role:'img','aria-label':'Saved simulation waveform and independent expected samples','data-testid':'waveform-svg',viewBox:`0 0 ${width} ${height}`});
    picture.append(svg('rect',{width,height,fill:'#f8fbff'}));
    const ticks=Math.max(2,Math.min(14,Math.floor(span/70)));
    for(let i=0;i<=ticks;i++){const time=model.end*i/ticks;picture.append(svg('line',{x1:x(time),x2:x(time),y1:25,y2:height,stroke:'#d8e1ec'}),svg('text',{x:x(time),y:18,fill:'#365272','font-size':11,'text-anchor':i===ticks?'end':'start'},Number(time.toFixed(3))+' ns'));}
    rows.forEach((r,i)=>{
      const y=49+i*37,color=r.kind.includes('expected')?'#8660a8':r.kind==='Saved stimulus'?'#66758c':'#087f8c';
      picture.append(svg('text',{x:5,y:y+5,fill:color,'font-size':12},r.name));
      if(r.sampled)for(const e of r.events){picture.append(svg('circle',{cx:x(e.time),cy:y,r:3,fill:color}),svg('text',{x:x(e.time)+4,y:y-5,fill:color,'font-size':11},e.value));}
      else if(r.width===1){let path='',lastY=y;
        for(const [j,e]of r.events.entries()){const ey=e.value==='1'?y-9:e.value==='0'?y+9:y;path+=(j?' H '+x(e.time)+' V '+ey:'M '+x(e.time)+' '+ey);lastY=ey;if(/[xz]/i.test(e.value))picture.append(svg('text',{x:x(e.time)+3,y:y-4,fill:'#b36b00','font-size':11},e.value));}
        if(r.events.length)path+=' H '+x(r.end??model.end);picture.append(svg('path',{d:path,fill:'none',stroke:color,'stroke-width':1.6}));
      }else for(let j=0;j<r.events.length;j++){const e=r.events[j],next=r.events[j+1]?.time??r.end??model.end,w=x(next)-x(e.time);picture.append(svg('rect',{x:x(e.time),y:y-10,width:Math.max(w,1),height:20,fill:'none',stroke:color}));if(w>15)picture.append(svg('text',{x:x(e.time)+4,y:y+4,fill:color,'font-size':11},e.value));}
    });
    for(const m of model.mismatches)picture.append(svg('line',{x1:x(m.time),x2:x(m.time),y1:25,y2:height,stroke:'#c43333','stroke-dasharray':'4 2'}));
    picture.append(svg('line',{x1:x(d.cursor),x2:x(d.cursor),y1:23,y2:height,stroke:'#e7a522','stroke-width':2}));host.replaceChildren(picture);
    values.replaceChildren(el('p',{text:`Cursor: ${d.cursor.toFixed(3)} ns · Zoom ${d.zoom}×`}),el('table',{},el('thead',{},el('tr',{},['Signal','Evidence','Value at cursor'].map(t=>el('th',{text:t})))),el('tbody',{},rows.map(r=>{
      const sample=r.sampled?r.events.find(e=>Math.abs(e.time-d.cursor)<1e-6):d.cursor<=(r.end??model.end)?r.events.findLast(e=>e.time<=d.cursor):undefined;
      return el('tr',{},el('td',{text:r.name}),el('td',{text:r.kind}),el('td',{text:sample?.value??(r.sampled?'Not sampled':'Not recorded')}));
    }))));
  }
}
