// Handle MP4 ranges so native video controls can seek.
export default {
  async fetch(request, env) {
    if (!['GET', 'HEAD'].includes(request.method)) return env.ASSETS.fetch(request);

    const source = new Request(request, { method: 'GET' });
    source.headers.delete('Range');
    source.headers.delete('If-Range');
    const response = await env.ASSETS.fetch(source);
    if (response.status !== 200)
      return request.method === 'HEAD' ? new Response(null, response) : response;

    const body = await response.arrayBuffer();
    const size = body.byteLength;
    const headers = new Headers(response.headers);
    headers.set('Accept-Ranges', 'bytes');
    headers.set('Content-Length', String(size));
    if (request.method === 'HEAD') return new Response(null, { headers });

    const range = request.headers.get('Range');
    const ifRange = request.headers.get('If-Range');
    const match = /^bytes=(\d*)-(\d*)$/.exec(range ?? '');
    // Ignore unsupported/malformed ranges and stale If-Range validators.
    if (
      !match ||
      (!match[1] && !match[2]) ||
      (ifRange && (ifRange.startsWith('W/') || ifRange !== headers.get('ETag')))
    )
      return new Response(body, { headers });

    const start = match[1] ? Number(match[1]) : Math.max(size - Number(match[2]), 0);
    const end = match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
    if (start > end || start >= size) {
      headers.set('Content-Range', `bytes */${size}`);
      headers.set('Content-Length', '0');
      return new Response(null, { status: 416, headers });
    }

    headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
    headers.set('Content-Length', String(end - start + 1));
    return new Response(body.slice(start, end + 1), { status: 206, headers });
  },
};
