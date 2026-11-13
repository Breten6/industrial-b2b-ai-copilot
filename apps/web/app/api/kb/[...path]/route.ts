import { apiUrl } from "../../../../lib/catalog";

const PDF_LIMIT = 8 * 1024 * 1024;
type Context = { params: Promise<{ path: string[] }> };

function error(detail: string, status: number) {
  return Response.json({ detail }, { status });
}

async function limitedBody(request: Request, limit: number) {
  const reader = request.body?.getReader();
  if (!reader) return new Blob();
  const chunks: ArrayBuffer[] = [];
  let bytes = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return new Blob(chunks);
    bytes += value.byteLength;
    if (bytes > limit) {
      await reader.cancel();
      return null;
    }
    chunks.push(Uint8Array.from(value).buffer);
  }
}

async function forward(request: Request, { params }: Context) {
  const path = (await params).path.join("/");
  const method = request.method;
  const upload = method === "POST" && path === "documents";
  const file = method === "GET" && /^documents\/\d{1,10}\/file$/.test(path);
  const review = method === "POST" && /^assertions\/\d{1,10}\/review$/.test(path);
  const archive = method === "PATCH" && /^documents\/\d{1,10}$/.test(path);
  if (!(upload || file || review || archive)) return error("Route not found.", 404);

  try {
    const url = apiUrl(`/v1/${path}`);
    const headers = new Headers();
    let body: Blob | undefined;
    if (!file) {
      const origin = request.headers.get("origin");
      if (origin !== `http://${request.headers.get("host")}`) {
        return error("This action requires a same-origin request.", 403);
      }
      const expectedType = upload ? "application/pdf" : "application/json";
      if (request.headers.get("content-type")?.split(";")[0] !== expectedType) {
        return error(`Expected ${expectedType}.`, 415);
      }
      const limited = await limitedBody(request, upload ? PDF_LIMIT : 4096);
      if (!limited) return error("Request exceeds the size limit.", 413);
      body = limited;
      headers.set("Content-Type", expectedType);
    }
    if (upload) url.search = new URL(request.url).search;
    const upstream = await fetch(url, { method, headers, body, signal: AbortSignal.timeout(85_000) });
    const responseHeaders = new Headers({ "Cache-Control": "no-store" });
    for (const name of ["Content-Type", "Content-Disposition", "Content-Security-Policy", "X-Content-Type-Options"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return error("The knowledge-base service is temporarily unavailable.", 503);
  }
}

export { forward as GET, forward as POST, forward as PATCH };
