// This script runs inside the temporary Hexo project built by build-site.py.
const bodies = require('../published-bodies.json');
const ranks = require('../published-order.json');

hexo.extend.filter.register('after_post_render', function (post) {
  if (post.snapshot_route) post.content = bodies[post.snapshot_route];
  return post;
}, 1000);

// Hexo uses insertion order for posts with the same timestamp. A clean import
// can read these in a different order. Preserve their published order when
// assigning previous/next pointers, including after a backdated insertion.
const generatePosts = hexo.extend.generator.get('post');
hexo.extend.generator.register('post', async function (locals) {
  const routes = await generatePosts.call(this, locals);
  const posts = routes.filter(route => route.data && route.data.__post).map(route => route.data);
  posts.sort((a, b) => a.date.valueOf() - b.date.valueOf()
    || (ranks[a.source] ?? Number.MAX_SAFE_INTEGER) - (ranks[b.source] ?? Number.MAX_SAFE_INTEGER)
    || a.source.localeCompare(b.source, 'en'));
  posts.forEach((post, index) => {
    post.next = posts[index - 1];
    post.prev = posts[index + 1];
  });
  return routes;
});
