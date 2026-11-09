import test from 'node:test';import assert from 'node:assert/strict';import {inspectMedia} from '../lib/media.mjs';
test('upload inspection rejects disguised active content and oversize files',()=>{
 assert.throws(()=>inspectMedia(new TextEncoder().encode('<script>alert(1)</script>'),'image/png',25));
 assert.throws(()=>inspectMedia(new Uint8Array(16),'image/svg+xml',16));
 const png=new Uint8Array([137,80,78,71,13,10,26,10,0,0,0,0]);assert.equal(inspectMedia(png,'image/png',12).kind,'image');assert.throws(()=>inspectMedia(png,'image/png',9*1024*1024));
 const mp4=new Uint8Array([0,0,0,20,102,116,121,112,105,115,111,109]);assert.equal(inspectMedia(mp4,'video/mp4',12).kind,'video');
});
