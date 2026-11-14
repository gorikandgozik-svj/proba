'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {join}=require('node:path');
const base=join(__dirname,'..');
const html=fs.readFileSync(join(base,'app/src/main/assets/index.html'),'utf8');
const java=fs.readFileSync(join(base,'app/src/main/java/ai/waypack/app/MainActivity.java'),'utf8');
const manifest=fs.readFileSync(join(base,'app/src/main/AndroidManifest.xml'),'utf8');
const gradle=fs.readFileSync(join(base,'app/build.gradle'),'utf8');
const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);
const engineEnd=scripts[1]?.indexOf("\n(function(){'use strict';\nconst E=window.PackingEngine");
const engineJs=engineEnd>=0?scripts[1].slice(0,engineEnd):'';
const sandbox={};
if(engineJs)vm.runInNewContext(engineJs,sandbox,{timeout:3000,filename:'packing-engine.js'});
const E=sandbox.PackingEngine;
const profile=(destination,month=6,days=7,people=1,luggage='checked')=>
 ({country:destination.country,city:destination.city,date:'2027-'+String(month).padStart(2,'0')+'-11',days,people,laundry:0,luggage,notes:''});

test('all inline scripts parse',()=>{
 assert.equal(scripts.length,2);
 scripts.forEach((s,i)=>assert.doesNotThrow(()=>new vm.Script(s,{filename:'waypack-script-'+i+'.js'})));
});
test('packing engine has destinations and activities',()=>{
 assert.ok(E&&typeof E.generate==='function');
 assert.ok(E.destinations.length>=4);
 assert.ok(E.activities.length>=15);
});
test('travel matrix 12 months, multiple days and baggage classes',()=>{
 const places=E.destinations.slice(0,Math.min(12,E.destinations.length));
 let count=0;
 for(const place of places)for(let m=1;m<=12;m++)for(const days of [1,7,21])for(const bag of ['cabin','checked','backpack']){
   const input=profile(place,m,days,2,bag);
   const output=E.generate(input,E.suggestActivities(input).slice(0,5));
   assert.ok(output.items.length>=8,place.city+' '+m+' '+days+' '+bag);
   assert.equal(new Set(output.items.map(i=>i.id)).size,output.items.length,'duplicate IDs');
   for(const item of output.items){
      assert.ok(typeof item.name==='string' && item.name.length>1);
      assert.ok(Number.isSafeInteger(item.qty)&&item.qty>=1&&item.qty<=99,item.id+' invalid qty');
      assert.ok(E.groups[item.category],item.id+' unknown category');
   }
   count++;
 }
 assert.ok(count>=100);
});
test('untrusted user destination does not execute code',()=>{
 const malicious='<img src=x onerror=alert(1)> "ignore instructions"';
 const result=E.generate({country:malicious,city:malicious,date:'2027-11-11',days:7,people:1,luggage:'cabin'},['beach']);
 assert.ok(result.items.length>0);
 assert.ok(result.items.every(i=>typeof i.name==='string'&&!i.name.includes('<script>')));
});
test('merge preserves checks, user quantities and manual items',()=>{
 const trip=E.generate(profile(E.destinations[0],7,7),['beach']).items;
 const prior=trip.slice(0,3).map((item,i)=>({...item,checked:i===0,qty:17,editedQty:i===1}));
 prior.push({id:'custom_test',name:'Моя книга',qty:1,category:'other',checked:true});
 const merged=E.mergeItems(prior,trip);
 assert.equal(merged.find(i=>i.id===trip[0].id).checked,true);
 assert.equal(merged.find(i=>i.id===trip[1].id).qty,17);
 assert.ok(merged.some(i=>i.id==='custom_test'));
});
test('WebView blocks remote requests and app backup/debugging',()=>{
 assert.ok(manifest.includes('android:allowBackup="false"'));
 assert.ok(manifest.includes('android:usesCleartextTraffic="false"'));
 assert.ok(!manifest.includes('android.permission.INTERNET'));
 assert.ok(java.includes('setWebContentsDebuggingEnabled(false)'));
 assert.ok(java.includes('settings.setAllowFileAccess(false)'));
 assert.ok(java.includes('settings.setAllowUniversalAccessFromFileURLs(false)'));
 assert.ok(java.includes('return missing();'));
 assert.ok(html.includes("connect-src 'none'"));
 assert.ok(!gradle.includes('libllama'));
 assert.ok(!gradle.includes('llama.cpp'));
});
test('real Google LiteRT model runs in Android, not a fake result or Gemma',()=>{
 assert.ok(java.includes('com.google.ai.edge.litert.CompiledModel'));
 assert.ok(java.includes('CompiledModel.create('));
 assert.ok(java.includes('new CompiledModel.Options(Accelerator.CPU)'));
 assert.ok(java.includes('rankerModel.run(rankerInput,rankerOutput)'));
 assert.ok(java.includes('rankerInput.get(0).writeFloat(input)'));
 assert.ok(java.includes('rankerOutput.get(0).readFloat()[0]'));
 assert.ok(java.includes('new float[18]'));
 assert.ok(java.includes('selectedRecommendations("",choices)'));
 assert.ok(!java.includes('inferLocal('));
 assert.ok(!java.includes('modelFile.getAbsolutePath()'));
 assert.ok(gradle.includes("com.google.ai.edge.litert:litert:2.3.0"));
 assert.ok(!gradle.includes('externalNativeBuild'));
});
test('AI cancels obsolete inferences; fallback is labeled',()=>{
 assert.ok(html.includes('aiController.abort()'));
 assert.ok(html.includes('if(aiController===controller)'));
 assert.ok(!html.includes('isNative?15000:28000'));
 assert.ok(!html.includes('Gemma не ответила вовремя'));
 assert.ok(html.includes('window.waypackAcceptEnrichment'));
 assert.ok(html.includes('window.waypackModelReady'));
 assert.ok(html.includes("autoAIStatus=data.realModel?'complete':'fallback'"));
 assert.ok(!html.includes('data-action="ai"'));
});
test('build uses lighter GGUF and supported Android ABI',()=>{
 assert.ok(gradle.includes("applicationId 'ai.waypack.litert'"));
 assert.ok(gradle.includes("versionName '5.0.0'"));
 assert.ok(gradle.includes("'armeabi-v7a'"));
 assert.ok(gradle.includes("noCompress += ['tflite']"));
});


test('Android startup and native recommendation are independent from model load',()=>{
 const ui=java.indexOf('showWebApp();');
 const extraction=java.indexOf('worker.execute(() -> {',ui);
 assert.ok(ui>0&&extraction>ui,'the WebView must show before background model extraction');
 const bridge=java.slice(java.indexOf('@JavascriptInterface public void runModel('),java.indexOf('@JavascriptInterface public void shareText('));
 const response=bridge.indexOf('deliver(id,200,instant.toString());');
 const neural=bridge.indexOf('worker.execute(() -> {');
 assert.ok(response>=0&&neural>response,'send fallback BEFORE scheduling slow Gemma');
 assert.ok(bridge.includes('selectedRecommendations("",choices)'));
 assert.ok(bridge.includes('waypackNativeEnhance'));
 assert.ok(bridge.includes('neuralRecommendations(data,choices)'));
 assert.ok(!bridge.includes('inferLocal('));
 assert.ok(bridge.includes('serial==requestSerial.get()'));
});
test('native fetch bridge resolves fast result independently of optional inference',async()=>{
 let lastId='',invoked=0,enhanceCount=0;
 const window={fetch:async()=>{throw Error('forbidden network')}};
 const native={
  isModelReady:()=>true,
  isNeuralReady:()=>false,
  runModel(id,payload){
   lastId=id;invoked++;
   assert.equal(JSON.parse(payload).activities[0],'beach');
   queueMicrotask(()=>window.waypackNativeResolve(id,JSON.stringify({
    items:[{name:'Мешок для грязной одежды',qty:1,category:'other'}],
    realModel:false,model:'WAYPACK Fast Engine'
   }),200));
  }
 };
 window.WaypackNative=native;
 const sandbox={window,location:{href:'https://appassets.androidplatform.net/index.html'},URL,Response,DOMException,Promise};
 vm.runInNewContext(scripts[0],sandbox,{timeout:2000});
 const status=await (await window.fetch('/api/status')).json();
 assert.equal(status.qwen,true);
 assert.equal(status.neuralReady,false);
 const response=await window.fetch('/api/ai',{method:'POST',body:JSON.stringify({activities:['beach']})});
 const data=await response.json();
 assert.equal(data.items[0].name,'Мешок для грязной одежды');
 assert.equal(data.realModel,false);
 assert.equal(invoked,1);
 window.waypackAcceptEnrichment=()=>{enhanceCount++};
 window.waypackNativeEnhance(lastId,JSON.stringify({realModel:true,items:[]}));
 window.waypackNativeEnhance('old-'+lastId,JSON.stringify({realModel:true,items:[]}));
 assert.equal(enhanceCount,1);
});

test('model is a standalone task-trained ranker and labels are honest',()=>{
 const trainer=fs.readFileSync(join(base,'tools/train_waypack_ranker.py'),'utf8');
 assert.ok(trainer.includes('synthetic travel-item relevance'));
 assert.ok(trainer.includes('tf.lite.TFLiteConverter.from_keras_model'));
 assert.ok(trainer.includes('heldout'));
 assert.ok(html.includes("data.modelKind!=='task-specific-18d-ranker'"));
 assert.ok(html.includes('protectedInstant'));
 assert.ok(html.includes('const available=Math.max(0,3-protectedInstant.length)'));
 assert.ok(java.includes('.put("modelKind","task-specific-18d-ranker")'));
});
