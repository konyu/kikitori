export default {
  async fetch(request, env, ctx) {
    // Static assets (index.html, assets/*) are served automatically via [assets]
    // This handler runs only for paths that don't match a static file.
    // Return 404 for unmatched paths.
    return new Response("Not Found", { status: 404 });
  },
};
