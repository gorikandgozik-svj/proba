'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs');
const vm=require('vm');
const html=fs.readFileSync('android/app/src/main/assets/index.html','utf8');
const script=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(x=>x[1]).join('\n');

function launch(mode='success'){
 const saved=new Map(), handlers={}, pending=[];
 const app={innerHTML:'',addEventListener:(name,fn)=>handlers['app:'+name]=fn};
 const toast={textContent:'',classList:{add(){},remove(){}}};
 const context={
   location:{hostname:'appassets.androidplatform.net',protocol:'https:',origin:'https://appassets.androidplatform.net'},
   navigator:{},
   document:{getElementById:id=>id==='app'?app:id==='toast'?toast:null,
     querySelectorAll:()=>[],addEventListener:(name,fn)=>handlers['document:'+name]=fn},
   localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,String(v))},
   scrollTo(){},setTimeout,clearTimeout,Date,Math,JSON,Promise,Number,Set,Map,String,
   URL,AbortController,AbortSignal,console
 };
 context.window=context;
 context.WaypackNative={
   haptic(){},
   analyzeTrip(id,json){
     if(mode==='error')throw Error('Offline');
     const p=JSON.parse(json);
     assert.equal(p.profile.country,'Египет');
     pending.push(id);
     setTimeout(()=>context.waypackCloudDone(id,200,JSON.stringify({
       realModel:true,model:'Qwen3.8-27B',
       updates:[],
       additions:[{name:'Водонепроницаемый чехол для телефона',qty:1,category:'activity',reason:'Для снорклинга'}]
     })),10);
   }
 };
 vm.runInNewContext(script,context,{filename:'waypack-android-inline.js',timeout:1000});
 return {app,toast,saved,pending,context,click(dataset){
   handlers['document:click']({target:{closest:()=>({dataset,disabled:false})}});
 }};
}

test('automatic cloud inference is invoked after generating, no AI button',async()=>{
 const t=launch();
 assert.match(t.app.innerHTML,/Расскажи о путешествии/);
 t.click({action:'next-activities'});
 assert.match(t.app.innerHTML,/Выбери активности/);
 t.click({action:'generate'});
 assert.match(t.app.innerHTML,/ИИ анализирует маршрут/);
 assert.doesNotMatch(t.app.innerHTML,/data-action="ai"/);
 assert.doesNotMatch(t.app.innerHTML,/Адрес сервера Qwen/);
 assert.equal(t.pending.length,1);
 await new Promise(r=>setTimeout(r,50));
 assert.match(t.app.innerHTML,/Список улучшен нейросетью/);
 assert.match(t.app.innerHTML,/Водонепроницаемый чехол для телефона/);
 const state=JSON.parse(t.saved.get('waypack-state-v3'));
 assert.equal(state.result.mode,'ai');
 assert.ok(state.items.some(i=>i.name==='Водонепроницаемый чехол для телефона'));
});

test('on cloud failure offline packing remains functional',async()=>{
 const t=launch('error');
 t.click({action:'next-activities'});
 t.click({action:'generate'});
 await new Promise(r=>setTimeout(r,20));
 assert.match(t.app.innerHTML,/Список готов — без облака/);
 assert.match(t.app.innerHTML,/Маска и трубка для плавания/);
 assert.doesNotMatch(t.app.innerHTML,/Водонепроницаемый чехол для телефона/);
});

test('cached real-model response avoids repeated cloud calls',async()=>{
 const t=launch();
 t.click({action:'next-activities'});
 t.click({action:'generate'});
 await new Promise(r=>setTimeout(r,50));
 assert.equal(t.pending.length,1);
 t.click({action:'back-activities'});
 t.click({action:'generate'});
 await new Promise(r=>setTimeout(r,20));
 assert.equal(t.pending.length,1);
 assert.match(t.app.innerHTML,/Список улучшен нейросетью/);
});
