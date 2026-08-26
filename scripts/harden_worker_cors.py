from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'worker.js'

OLD = '''function corsHeaders(origin) {
  const allowed = !origin || origin.includes("github.io") ||
    origin.includes("pages.dev") || origin.includes("localhost");
  return {
    "Access-Control-Allow-Origin": allowed ? (origin || "*") : "null",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}
'''

NEW = '''function corsHeaders(origin) {
  // Match real hostnames, never arbitrary substrings such as
  // attacker.example/?next=github.io. GitHub Pages / Cloudflare Pages remain
  // supported, while local development is restricted to loopback hosts.
  let allowed = !origin;
  if (origin) {
    try {
      const u = new URL(origin);
      const host = u.hostname.toLowerCase();
      const local = host === "localhost" || host === "127.0.0.1" || host === "::1";
      const githubPages = host === "github.io" || host.endsWith(".github.io");
      const cloudflarePages = host === "pages.dev" || host.endsWith(".pages.dev");
      const secureHosted = u.protocol === "https:" && (githubPages || cloudflarePages);
      const localDev = local && (u.protocol === "http:" || u.protocol === "https:");
      allowed = secureHosted || localDev;
    } catch (_) {
      allowed = false;
    }
  }
  return {
    "Access-Control-Allow-Origin": allowed ? (origin || "*") : "null",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}
'''

text = WORKER.read_text(encoding='utf-8')
if NEW in text:
    print('Worker CORS already hardened')
elif text.count(OLD) != 1:
    raise RuntimeError('Expected legacy corsHeaders implementation not found exactly once')
else:
    WORKER.write_text(text.replace(OLD, NEW, 1), encoding='utf-8')
    print('Worker CORS hardened')
