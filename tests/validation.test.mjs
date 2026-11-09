import assert from 'node:assert/strict';
import test from 'node:test';
import { credentials, profileInput, postInput, commentInput, identifier } from '../lib/validation.mjs';
test('reject empty and oversized user content', () => {
  assert.equal(postInput.safeParse('   ').success, false);
  assert.equal(postInput.safeParse('a'.repeat(2001)).success, false);
  assert.equal(commentInput.safeParse('a'.repeat(501)).success, false);
  assert.equal(postInput.parse('  hello  '), 'hello');
});
test('validate account identifiers and credentials', () => {
  assert.equal(profileInput.safeParse({username:'bad/name',display_name:'A',bio:''}).success,false);
  assert.equal(profileInput.safeParse({username:'alice_1',display_name:'Alice',bio:''}).success,true);
  assert.equal(credentials.safeParse({email:'bad',password:'short'}).success,false);
  assert.equal(identifier.safeParse("x' OR true").success,false);
});
