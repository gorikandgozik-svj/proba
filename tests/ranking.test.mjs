import test from 'node:test';
import assert from 'node:assert/strict';
import {rankFeed} from '../lib/ranking.mjs';
test('explicit interest boost is predictable and does not mutate the source',()=>{
 const now=Date.parse('2026-11-09T12:00:00Z');const posts=[{id:'new',topic:'life',created_at:'2026-11-09T11:00:00Z'},{id:'interest',topic:'science',created_at:'2026-11-09T05:00:00Z'}];
 assert.deepEqual(rankFeed(posts,['science'],now).map(p=>p.id),['interest','new']);
 assert.deepEqual(rankFeed(posts,[],now).map(p=>p.id),['new','interest']);
 assert.equal(posts[0].id,'new');
});
