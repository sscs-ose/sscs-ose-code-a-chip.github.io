import { element as el } from './dom.js';

/** Explicit read-only catalog. Every request is scoped to the active system. */
export class ProjectFiles {
  constructor(callbacks){this.callbacks=callbacks;this.token=0;}
  async open(){
    this.close();const token=++this.token,scope=this.callbacks.identity();
    const dialog=el('dialog',{class:'project-files-dialog','aria-label':'Project files and change history','data-testid':'project-files-dialog'});
    this.dialog=dialog;dialog.append(el('h2',{text:'Project files and change history'}),el('p',{text:'Reading saved file index…',role:'status'}),el('button',{type:'button',text:'Close files',onclick:()=>this.close()}));document.body.append(dialog);dialog.showModal();
    dialog.addEventListener('cancel',()=>this.close());
    try{
      const data=await this.callbacks.request('inspection/files');
      if(token!==this.token||scope!==this.callbacks.identity())return;
      this.data=data;this.scope=scope;this.filter='';this.category='';this.page=0;this.view='files';this.selectedId=null;this.render();
    }catch(e){if(token===this.token)dialog.append(el('p',{role:'alert',text:e.message}));}
  }
  close(){this.token++;this.previewToken=(this.previewToken||0)+1;this.dialog?.close();this.dialog?.remove();this.dialog=null;}
  render(){
    const dialog=this.dialog;if(!dialog?.isConnected)return;
    this.previewToken=(this.previewToken||0)+1;
    const table=el('div',{'data-testid':'project-files-table'}),preview=el('section',{'data-testid':'project-file-preview'});this.table=table;this.preview=preview;
    dialog.replaceChildren(el('div',{class:'provider-actions'},el('h2',{text:'Project files and change history'}),el('button',{type:'button',text:'Close files','data-testid':'project-files-close',onclick:()=>this.close()})),
      el('p',{text:this.data.limits}),el('p',{text:`Saved system ${this.data.identity.system_id} · revision ${this.data.revision_id}. Unsaved editor drafts are not files in this index.`}),
      el('p',{class:'scope-note',text:'Select a file row, or focus it and press Enter, to open a read-only preview. Refresh the file index after generation to include new saved outputs.'}),
      el('div',{class:'provider-actions'},el('button',{type:'button',text:'Files','data-testid':'project-files-tab',onclick:()=>{this.view='files';this.page=0;this.render();}}),el('button',{type:'button',text:'Change history','data-testid':'project-history-tab',onclick:()=>{this.view='history';this.page=0;this.render();}}),el('button',{type:'button',text:'Refresh file index',onclick:()=>this.open()})),
      el('label',{},'Find file or action',el('input',{type:'search',value:this.filter,'data-testid':'project-files-search',oninput:e=>{this.filter=e.target.value;this.page=0;this.rows();}})),
      el('label',{},'File group (Files only)',el('select',{'data-testid':'project-files-category',value:this.category,disabled:this.view!=='files',onchange:e=>{this.category=e.target.value;this.page=0;this.rows();}},el('option',{value:'',text:'All file groups'}),[...new Set(this.data.entries.map(e=>e.category))].map(c=>el('option',{value:c,text:c,selected:c===this.category})))),table,preview);
    this.rows();
  }
  rows(){
    const source=this.view==='files'?this.data.entries:this.data.events, query=this.filter.toLowerCase();
    const rows=source.filter(r=>(!this.category||this.view==='history'||r.category===this.category)&&JSON.stringify(r).toLowerCase().includes(query));
    const size=40,count=Math.max(1,Math.ceil(rows.length/size));this.page=Math.min(this.page,count-1);
    const selected=rows.slice(this.page*size,(this.page+1)*size), columns=this.view==='files'?['Name','Group / storage','Saved location','Action / time','Inspect']:['Time','Action / record','Actor','Detail / location'];
    this.table.replaceChildren(el('p',{'data-testid':'project-files-count',text:`${rows.length} ${this.view==='files'?'entries':'recorded actions'} · page ${this.page+1} of ${count}`}),
      el('div',{class:'provider-actions'},el('button',{type:'button',text:'Previous page',disabled:this.page===0,onclick:()=>{this.page--;this.rows();}}),el('button',{type:'button',text:'Next page',disabled:this.page>=count-1,onclick:()=>{this.page++;this.rows();}})),
      el('table',{},el('thead',{},el('tr',{},columns.map(text=>el('th',{text})))),el('tbody',{},selected.map(r=>this.view==='files'?
        el('tr',{class:'project-file-row',tabindex:0,'aria-selected':String(r.id===this.selectedId),'data-file-id':r.id,
          onclick:event=>{if(!event.target.closest('button'))this.inspect(r);},
          onkeydown:event=>{if(event.target===event.currentTarget&&['Enter',' '].includes(event.key)){event.preventDefault();this.inspect(r);}}},
          el('td',{text:r.name}),el('td',{text:r.category+' / '+r.storage}),el('td',{},el('code',{text:r.location}),
            r.stage_id?el('p',{class:'scope-note',text:`Stage ${r.stage_id}${r.node_id?' · node '+r.node_id:''}${r.source_revision?' · source '+r.source_revision:''}`}):null),
          el('td',{text:(r.action||'')+' · '+(r.time?new Date(r.time).toLocaleString():'Historical time not recorded')}),el('td',{},el('button',{type:'button',text:'Inspect '+r.name,onclick:()=>this.inspect(r)}))):
        el('tr',{},el('td',{text:r.time?new Date(r.time).toLocaleString():'Not recorded'}),el('td',{text:r.action+' · '+(r.record_id||'')}),el('td',{text:typeof r.actor==='string'?r.actor:JSON.stringify(r.actor)}),el('td',{text:r.detail+'\n'+r.location}))))));
  }
  async inspect(entry,page=0,sha256=null){
    const token=this.previewToken=(this.previewToken||0)+1,scope=this.scope;
    this.selectedId=entry.id;this.rows();
    this.preview.replaceChildren(el('h3',{text:entry.name}),el('p',{text:'Reading verified file…',role:'status'}));
    try{
      const query=sha256?`?page=${page}&sha256=${encodeURIComponent(sha256)}`:'';
      const data=await this.callbacks.request(`inspection/files/${entry.id}${query}`);
      if(token!==this.previewToken||scope!==this.callbacks.identity()||!this.dialog?.isConnected)return;
      const selectedPreview=this.preview,selectedDialog=this.dialog;
      const revealLoadedImage=()=>{
        if(token===this.previewToken&&scope===this.callbacks.identity()&&selectedDialog===this.dialog&&selectedPreview===this.preview&&selectedDialog.isConnected)
          selectedPreview.scrollIntoView({block:'start'});
      };
      const pagination=data.pagination,changePage=page=>this.inspect(entry,page,data.sha256);
      const pageControls=pagination?el('div',{'data-testid':'project-file-pagination'},
        el('p',{'data-testid':'project-file-page-range',text:`Page ${pagination.page+1} of ${pagination.page_count} · bytes ${pagination.start_byte+1}–${pagination.end_byte} of ${pagination.total_bytes}. Only this page is displayed; UTF-8 byte boundaries are preserved.`}),
        el('div',{class:'provider-actions'},
          el('button',{type:'button',text:'First page','data-testid':'project-file-page-first',disabled:pagination.page===0,onclick:()=>changePage(0)}),
          el('button',{type:'button',text:'Previous text page','data-testid':'project-file-page-previous',disabled:pagination.page===0,onclick:()=>changePage(pagination.page-1)}),
          el('button',{type:'button',text:'Next text page','data-testid':'project-file-page-next',disabled:pagination.page>=pagination.page_count-1,onclick:()=>changePage(pagination.page+1)}),
          el('button',{type:'button',text:'Last page','data-testid':'project-file-page-last',disabled:pagination.page>=pagination.page_count-1,onclick:()=>changePage(pagination.page_count-1)}))):null;
      this.preview.replaceChildren(...[el('h3',{text:entry.name}),el('p',{text:`${data.entry.location} · ${data.bytes} bytes · SHA-256 ${data.sha256||'not computed (preview size limit)'}`}),
        data.entry.stage_id?el('p',{text:`Stage ${data.entry.stage_id}${data.entry.run_id?' · record '+data.entry.run_id:''}${data.entry.node_id?' · node '+data.entry.node_id:''}${data.entry.source_revision?' · source revision '+data.entry.source_revision:''}`}):null,
        el('p',{class:'scope-note',text:'Read-only preview. This view has no edit or save action.'}),
        pageControls,
        data.kind==='image'&&data.mime_type==='image/png'?el('img',{src:'data:image/png;base64,'+data.data_base64,alt:entry.name,class:'project-file-preview-image','data-testid':'project-file-image',onload:revealLoadedImage}):
          data.kind==='binary'?el('p',{role:'status','data-testid':'project-file-binary',text:data.message}):el('pre',{'data-testid':'project-file-text',text:data.text}),
        data.entry.download_url?el('a',{href:data.entry.download_url,text:'Download saved file','data-testid':'project-file-download'}):null].filter(Boolean));
      this.preview.scrollIntoView({block:'start'});
    }catch(e){if(token===this.previewToken&&this.dialog?.isConnected)this.preview.replaceChildren(el('p',{role:'alert',text:e.message}));}
  }
}
