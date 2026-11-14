'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const base=path.join(__dirname,'..');
const html=fs.readFileSync(path.join(base,'app/src/main/assets/index.html'),'utf8');
const manifest=fs.readFileSync(path.join(base,'app/src/main/AndroidManifest.xml'),'utf8');
const java=fs.readFileSync(path.join(base,'app/src/main/java/ai/waypack/app/MainActivity.java'),'utf8');
const cpp=fs.readFileSync(path.join(base,'app/src/main/cpp/waypack_jni.cpp'),'utf8');
function bridge(){
 const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)];
 let calls=[],native={
  isModelReady(){return true},
  runQwen(id,payload){calls.push({id,payload})}
 };
 let w={WaypackNative:native,fetch:async()=>{throw Error('No external internet allowed')}};
 let ctx={window:w,location:{href:'https://appassets.androidplatform.net/index.html'},
          URL,Response,DOMException,Promise,console};
 vm.runInNewContext(scripts[0][1],ctx,{timeout:1000});
 return {window:w,calls,scripts};
}
test('all inline app JavaScript compiles',()=>{
 const {scripts}=bridge();assert.ok(scripts.length>=2);
 scripts.forEach((s,i)=>assert.doesNotThrow(()=>new vm.Script(s[1],{filename:'app-script-'+i+'.js'})));
});
test('offline APK requests zero Android network permissions',()=>{
 assert.ok(!manifest.includes('android.permission.INTERNET'));
 assert.ok(manifest.includes('android:usesCleartextTraffic="false"'));
});
test('JNI is connected to a real GGUF decoder, not canned responses',()=>{
 for(const marker of ['inferLocal','llama_model_load_from_file','llama_decode','llama_sampler_sample'])assert.ok(cpp.includes(marker));
 assert.ok(java.includes('System.loadLibrary("waypack-qwen")'));
 assert.ok(java.includes('qwen3.5-0.8b-q4ks.gguf'));
});
test('native status reports local Qwen availability without server request',async()=>{
 const {window}=bridge();const r=await window.fetch('/api/status');
 assert.equal(r.status,200);const payload=await r.json();
 assert.equal(payload.qwen,true);assert.match(payload.model,/0\.8B/);
});
test('trip reaches JNI, Qwen result returns as actual JSON through bridge',async()=>{
 const {window,calls}=bridge();
 const trip={profile:{country:'Египет',city:'Шарм-эш-Шейх',days:7},activities:['snorkel'],currentItems:[{name:'Футболка'}]};
 const pending=window.fetch('/api/ai',{method:'POST',body:JSON.stringify(trip)});
 assert.equal(calls.length,1);
 assert.deepEqual(JSON.parse(calls[0].payload).profile,trip.profile);
 window.waypackNativeResolve(calls[0].id,JSON.stringify({model:'Qwen3.5 0.8B Q4_K_S',items:[{name:'Чехол для телефона',qty:1,category:'activity'}]}),200);
 const response=await pending;assert.equal(response.status,200);
 const answer=await response.json();assert.equal(answer.items[0].name,'Чехол для телефона');
});
test('native Qwen errors surface to app instead of silently returning fake answers',async()=>{
 const {window,calls}=bridge();const pending=window.fetch('/api/ai',{body:'{}'});
 window.waypackNativeResolve(calls[0].id,JSON.stringify({error:'Нет памяти'}),502);
 const response=await pending;assert.equal(response.status,502);
 assert.equal((await response.json()).error,'Нет памяти');
});
test('aborted Qwen request is rejected and no stale response is rendered',async()=>{
 const {window,calls}=bridge();const ac=new AbortController();
 const pending=window.fetch('/api/ai',{body:'{}',signal:ac.signal});
 ac.abort();
 await assert.rejects(pending,e=>e.name==='AbortError');
 window.waypackNativeResolve(calls[0].id,'{"items":[{"name":"Поздний результат"}]}',200);
});
test('app UI and native bridge identify Qwen 0.8B and use offline-only route',()=>{
 assert.ok(html.includes('Qwen3.5 0.8B Q4_K_S'));
 assert.ok(html.includes('Content-Security-Policy'));
 assert.ok(html.includes("connect-src 'none'"));
 assert.ok(!html.includes("if(isNative)apiBase='https://"));
});
