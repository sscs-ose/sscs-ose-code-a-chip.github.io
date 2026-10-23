'use strict';
(() => {
const data=JSON.parse(document.getElementById('experiment-data').textContent);
const $=id=>document.getElementById(id);
const meta={
 window:{title:'Does a missing edge mean failure?',layer:'BASIC · OBSERVATION',question:'Start with a short view of the old library record. Predict whether it supports a delay and whether it establishes the required response. Then compare a longer view.',outcome:'Success: distinguish an undefined delay from an unobserved functional deadline.'},
 model:{title:'Choose evidence that can challenge your explanation',layer:'ADVANCED · CONTROLLED COMPARISON',question:'Select a hypothesis, then predict the measurement and function of the SECOND case in the comparison.',outcome:'Success: explain what changed, what was held fixed, and what remains unsupported.'},
 rules:{title:'Which judgment changes when a limit changes?',layer:'ADVANCED · INDEPENDENT JUDGMENTS',question:'Change one measurement rule on the corrected nonlinear record. Predict all three judgments.',outcome:'Success: distinguish event extraction, a scalar limit and the separate T1 function contract.'},
 challenge:{title:'An unfamiliar observation — what would you request next?',layer:'INDEPENDENT CHALLENGE',question:'A 4 ms supply ramp has been observed only through 4.4 ms. Decide what can be established, and describe a check in ordinary words.',outcome:'Success: identify the evidence needed before declaring function success or failure.'}
};
let task='window',active=null,contextKey=null;
const drafts=[];
const attempts=[];
const controlIds=['windowEnd','hypothesis','resistor','start','threshold','upper'];
const predictionIds=['predictMeasure','predictFunction','predictScalar','reason','nextEvidence','proposedCheck'];
const choiceText={VALID:'valid measurement',INVALID:'undefined or invalid measurement',PASS:'requirement met',FAIL:'requirement failed',NOT_EVALUATED:'not evaluated',INSUFFICIENT_EVIDENCE:'not enough evidence',NOT_TRIGGERED:'no supply trigger observed'};
const dimensionText={measurement:'Delay measurement',scalar_spec:'Numerical delay limits',functional:'Response under T1'};
function key(){
 if(task==='window')return 'window:'+Number($('windowEnd').value);
 if(task==='model')return 'model:'+$('hypothesis').value+':'+$('resistor').value;
 if(task==='rules')return 'rules:'+[$('start').value,$('threshold').value,$('upper').value].map(Number).join(':');
 return 'challenge:4.4';
}
function saveDraft(){
 if(!contextKey)return;
 const reason=$('reason').value.trim(),explanation=$('explanation').value.trim();
 if(active&&active.feedback)return;
 const note={task,key:contextKey,reason,explanation,next_evidence:$('nextEvidence').value.trim(),proposed_check:$('proposedCheck').value.trim(),prediction:{measurement:$('predictMeasure').value,functional:$('predictFunction').value,scalar_spec:$('predictScalar').value}};
 if(!reason&&!explanation&&!note.next_evidence&&!note.proposed_check&&!Object.values(note.prediction).some(Boolean))return;
 if(active){if(!explanation)return;note.attempt_id=active.id;}
 const fingerprint=JSON.stringify(note);
 if(drafts.some(d=>d.fingerprint===fingerprint))return;
 drafts.push({...note,record_type:'UNFINISHED NOTES — not a completed experiment',fingerprint});
}
function appendText(parent,tag,text){const el=document.createElement(tag);el.textContent=text;parent.append(el);return el;}
function predictionText(a){return Object.entries(a.prediction).filter(([k,v])=>v).map(([k,v])=>dimensionText[k]+': '+choiceText[v]).join('; ')||'(not chosen yet)';}
function count(){
 $('attemptCount').textContent=attempts.length+' recorded experiment(s); '+attempts.filter(a=>a.feedback).length+' with explanation and feedback; '+drafts.length+' unfinished note(s). Nothing has been sent.';
 $('export').disabled=$('exportText').disabled=!(attempts.length||drafts.length);
 const history=$('history');history.replaceChildren();
 for(const a of attempts){
  const d=document.createElement('details');appendText(d,'summary','Attempt '+a.id+' · '+meta[a.task].title+(a.feedback?' · feedback completed':' · explanation still needed'));
  appendText(d,'p','Conditions: '+data.variants[a.key].conditions);appendText(d,'p','Your prediction: '+predictionText(a));appendText(d,'p','Your reason: '+a.reason);
  if(a.explanation)appendText(d,'p','Your observation: '+a.explanation);
  if(a.feedback)appendText(d,'p','Recorded feedback: '+a.feedback);
  if(a.additional_evidence)appendText(d,'p','Additional evidence: '+a.additional_evidence.explanation);
  history.append(d);
 }
 for(const a of drafts){const d=document.createElement('details');appendText(d,'summary','Unfinished notes · '+meta[a.task].title);appendText(d,'p','Conditions: '+data.variants[a.key].conditions);appendText(d,'p','Your prediction: '+predictionText(a));appendText(d,'p','Your reason: '+(a.reason||'(not written yet)'));if(a.explanation)appendText(d,'p','Your observation: '+a.explanation);if(a.next_evidence)appendText(d,'p','Next evidence requested: '+a.next_evidence);if(a.proposed_check)appendText(d,'p','Proposed check: '+a.proposed_check);history.append(d);}
}
function targetNote(){
 const v=data.variants[key()];contextKey=key();
 $('predictionTarget').textContent=(task==='model'?'Predict the SECOND (lower) plot: ':'Prediction applies to: ')+({old_nonlinear:'old library / original resistor',corrected_nonlinear:'corrected library / original resistor',old_linear:'old library / simplified resistor',corrected_linear:'corrected library / simplified resistor',dc_original:'original supply setting',dc_removed:'DC override removed',slow_supply:'slow-supply record, first 4.4 ms'})[v.result.case]+'. '+v.conditions;
}
function clearAttempt(message){
 active=null;
 for(const id of predictionIds){$(id).value='';$(id).disabled=false;}
 $('explanation').value='';$('explanation').disabled=false;$('run').disabled=false;$('feedbackButton').disabled=false;
 for(const id of ['evidence','reflection','feedback','extended','nextStep'])$(id).hidden=true;
 $('emptyEvidence').hidden=false;$('extend').hidden=true;$('notice').textContent=message;count();
}
function modelNote(){
 const h=$('hypothesis').value;$('resistor').disabled=h!=='hvl_dependency';
 const descriptions={hvl_dependency:'First: old HVL. Second: corrected HVL. Same selected resistor model, ramp and tolerance.',resistor_only:'First: corrected HVL with nonlinear resistor. Second: corrected HVL with simplified resistor. HVL held fixed.',dc_override:'First: original DC setting. Second: DC override removed. Original matched setup retained.',window_only:'First: 1.5 ms measurement start. Second: 0 ms start. Same old-HVL trace and unchanged T1.'};
 $('comparisonNote').textContent=descriptions[h];
}
function selectTask(next){
 saveDraft();task=next;for(const b of document.querySelectorAll('[data-task]'))b.setAttribute('aria-pressed',String(b.dataset.task===task));
 for(const t of Object.keys(meta))$(t+'Controls').hidden=t!==task;
 $('taskTitle').textContent=meta[task].title;$('layer').textContent=meta[task].layer;$('question').textContent=meta[task].question;$('outcome').textContent=meta[task].outcome;
 $('scalarPrediction').hidden=task!=='rules';$('challengeAnswers').hidden=task!=='challenge';
 $('reasonLabel').textContent=task==='model'?'Why? What observation would contradict your hypothesis?':'Why do you expect that?';
 modelNote();clearAttempt('Choose a prediction and give a reason. Previous attempts and unfinished notes are kept below.');targetNote();
}
function displayEvidence(variant){
 $('emptyEvidence').hidden=true;$('evidence').hidden=false;
 $('wave').src=data.images[variant.image];$('wave').alt=variant.alt;
 $('evidenceLabel').textContent='REAL RECORDED SPICE WAVEFORMS · Python-precomputed check · no new simulation';
 $('conditions').textContent=variant.conditions;
 $('source').textContent=variant.reports.map(r=>'Case: '+r.case+'\nWaveform SHA-256: '+r.source_wave_sha256+'\nSettings: '+JSON.stringify(r.settings)+'\nT1 source: '+r.functional.contract.source).join('\n\n');
}
function run(){
 if(!$('predictMeasure').value||!$('predictFunction').value||!$('reason').value.trim()||(task==='rules'&&!$('predictScalar').value)){
  $('notice').textContent='First choose each prediction and explain your reason. No answer is preselected.';return;
 }
 if(task==='challenge'&&(!$('nextEvidence').value.trim()||!$('proposedCheck').value.trim())){
  $('notice').textContent='For the challenge, also describe the evidence you would request and a check in ordinary words.';return;
 }
 const k=key(),v=data.variants[k];
 active={id:attempts.length+1,task,key:k,prediction:{measurement:$('predictMeasure').value,functional:$('predictFunction').value},reason:$('reason').value.trim(),created_at:new Date().toISOString(),settings:v.reports.map(r=>r.settings),sources:v.reports.map(r=>r.source_wave_sha256),actual:{measurement:v.result.measurement,scalar_spec:v.result.scalar_spec,functional:v.result.functional.status}};
 if(task==='rules')active.prediction.scalar_spec=$('predictScalar').value;
 if(task==='model')active.hypothesis=$('hypothesis').value;
 if(task==='challenge'){active.next_evidence=$('nextEvidence').value.trim();active.proposed_check=$('proposedCheck').value.trim();}
 attempts.push(active);
 for(const id of predictionIds)$(id).disabled=true;
 $('run').disabled=true;displayEvidence(v);$('reflection').hidden=false;
 $('notice').textContent='Prediction recorded. Inspect the waveform, then explain your observation. Changing a condition requires a new prediction.';count();$('explanation').focus();
}
function feedback(){
 if(!active){$('notice').textContent='Record a prediction and open the evidence first.';return;}
 if(!$('explanation').value.trim()){$('notice').textContent='Name a waveform observation before opening feedback. A changed mind is welcome.';$('explanation').focus();return;}
 const v=data.variants[active.key];active.explanation=$('explanation').value.trim();active.feedback=v.explanation;active.comparisons=[];
 $('comparison').replaceChildren();
 for(const [dimension,prediction] of Object.entries(active.prediction)){
  const actual=active.actual[dimension],matched=prediction===actual;
  active.comparisons.push({dimension,prediction,actual,matched});
  const p=document.createElement('p');if(!matched)p.className='revise';
  p.textContent=(matched?'Supported prediction — ':'Revise this prediction — ')+dimensionText[dimension]+': you predicted '+choiceText[prediction]+'; the evidence gives '+choiceText[actual]+' ('+actual+').';
  $('comparison').append(p);
 }
 $('explanationText').textContent=(v.result.startup_s===null?'The selected delay cannot be calculated. ':`Measured delay: ${(v.result.startup_s*1000).toFixed(3)} ms; selected scalar limits: 0.5–${v.result.settings.scalar_max_ms} ms. `)+v.explanation;
 $('hypothesisText').textContent=active.hypothesis?data.hypotheses[active.hypothesis]:'';
 $('feedback').hidden=false;$('extend').hidden=task!=='challenge';$('explanation').disabled=true;$('feedbackButton').disabled=true;
 $('nextStep').hidden=false;$('nextTask').hidden=task==='challenge';
 $('nextHint').textContent={window:'Next: compare your 2.5 ms and 4 ms attempts and explain what the longer view adds. After that, continue to the hypothesis task.',model:'Next: try an alternative explanation and name what the comparison cannot establish. Then continue to measurement rules.',rules:'Next: compare maximum delays of 1 ms and 2 ms while keeping other settings fixed. Then try the independent challenge.',challenge:'Next: use the longer-record button if you need more evidence. Download your notes, then complete the transfer question and feedback form from the trial pack.'}[task];
 $('notice').textContent='Feedback is based on the declared rules and evidence, not a grade of your written reasoning.';count();$('feedback').focus();
}
for(const b of document.querySelectorAll('[data-task]'))b.addEventListener('click',()=>selectTask(b.dataset.task));
for(const id of controlIds)$(id).addEventListener('change',()=>{saveDraft();modelNote();clearAttempt('Condition changed. Make a new prediction; earlier attempts and written notes are kept below.');targetNote();});
$('run').addEventListener('click',run);$('feedbackButton').addEventListener('click',feedback);
$('enlarge').addEventListener('click',()=>{$('largeWave').src=$('wave').src;$('largeWave').alt=$('wave').alt;$('plotDialog').showModal();});
$('closePlot').addEventListener('click',()=>$('plotDialog').close());
$('nextTask').addEventListener('click',()=>{const order=Object.keys(meta);selectTask(order[Math.min(order.indexOf(task)+1,3)]);$('taskTitle').setAttribute('tabindex','-1');$('taskTitle').focus();});
$('retry').addEventListener('click',()=>{saveDraft();clearAttempt('New attempt. Earlier predictions and notes are kept below.');targetNote();});
$('preview').addEventListener('click',()=>{displayEvidence(data.challenge_preview);$('notice').textContent='Only the first 4.4 ms is visible. Record your own judgment before requesting the calculated result.';});
$('extend').addEventListener('click',()=>{
 if(!active||active.task!=='challenge'||!active.feedback)return;
 const v=data.variants['challenge:6'];active.additional_evidence={key:'challenge:6',explanation:v.explanation};
 $('extendedWave').src=data.images[v.image];$('extendedText').textContent=v.explanation;$('extended').hidden=false;$('extend').hidden=true;count();
});
function download(text,name,type){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function record(){saveDraft();count();return {format:'trust-before-pass-browser-journal-v2',release:data.release,record_type:'Local self-entered notes; not verified human-study data',evidence_manifest_sha256:data.evidence_manifest_sha256,attempts,unfinished_notes:drafts.map(({fingerprint,...d})=>d)};}
$('export').addEventListener('click',()=>download(JSON.stringify(record(),null,2),'trust-before-pass-investigation.json','application/json'));
$('exportText').addEventListener('click',()=>{
 const r=record(),lines=['Trust Before Pass — my investigation',r.release,'Saved locally. Share only if you choose.',''];
 for(const a of r.attempts){lines.push('ATTEMPT '+a.id+' — '+meta[a.task].title,data.variants[a.key].conditions,'Prediction: '+Object.entries(a.prediction).map(([k,v])=>dimensionText[k]+': '+choiceText[v]).join('; '),'Reason: '+a.reason,'Observation: '+(a.explanation||'(not completed)'), 'Feedback: '+(a.feedback||'(not requested)'));if(a.next_evidence)lines.push('Next evidence requested: '+a.next_evidence,'Proposed check: '+a.proposed_check);if(a.additional_evidence)lines.push('Additional evidence: '+a.additional_evidence.explanation);lines.push('');}
 for(const a of r.unfinished_notes)lines.push('UNFINISHED NOTES — '+meta[a.task].title,data.variants[a.key].conditions,'Prediction: '+Object.entries(a.prediction).filter(([k,v])=>v).map(([k,v])=>dimensionText[k]+': '+choiceText[v]).join('; '),'Reason: '+a.reason,'Observation: '+a.explanation,'Next evidence: '+a.next_evidence,'Proposed check: '+a.proposed_check,'');
 download(lines.join('\n'),'trust-before-pass-notes.txt','text/plain;charset=utf-8');
});
for(const id of [...predictionIds,'explanation'])$(id).addEventListener('input',()=>{$('export').disabled=$('exportText').disabled=false;});
$('app').hidden=false;
const requested=new URLSearchParams(location.search).get('task');selectTask(Object.hasOwn(meta,requested)?requested:'window');
})();
