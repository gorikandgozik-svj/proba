export const topics = ['technology','art','science','culture','life'];
// Explainable ranking within each fetched page: freshness plus an explicit interest boost.
export function rankFeed(posts, interests, now = Date.now()) {
  const score = post => Math.max(0, 48 - (now - Date.parse(post.created_at)) / 3600000) + (interests.includes(post.topic) ? 12 : 0);
  return [...posts].sort((a,b) => score(b)-score(a) || b.created_at.localeCompare(a.created_at));
}
