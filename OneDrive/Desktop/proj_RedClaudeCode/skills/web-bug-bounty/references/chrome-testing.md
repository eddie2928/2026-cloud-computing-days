# Chrome Testing Reference

Comprehensive reference for using claude-in-chrome MCP tools during web vulnerability testing.

---

## 1. Tool Loading Pattern

Before ANY chrome tool call, load the tool via ToolSearch:

```
ToolSearch: select:mcp__claude-in-chrome__<tool_name>
```

Examples:

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp
ToolSearch: select:mcp__claude-in-chrome__navigate
ToolSearch: select:mcp__claude-in-chrome__javascript_tool
ToolSearch: select:mcp__claude-in-chrome__read_network_requests
ToolSearch: select:mcp__claude-in-chrome__read_console_messages
ToolSearch: select:mcp__claude-in-chrome__form_input
ToolSearch: select:mcp__claude-in-chrome__gif_creator
```

Never skip this step. The tool will not be callable without first loading its schema.

---

## 2. Session Setup

### Get Browser State

Load then call to see all open tabs and current context:

```
Tool: mcp__claude-in-chrome__tabs_context_mcp
Params: (none)
```

Note the `tabId` from the response — it is required for all subsequent tool calls.

### Navigate to Target

```
Tool: mcp__claude-in-chrome__navigate
Params:
  url:   "https://target.example.com"
  tabId: <tabId from tabs_context_mcp>
```

### Verify Login State

Check cookies to confirm an authenticated session:

```
Tool: mcp__claude-in-chrome__javascript_tool
Params:
  code:  "console.log(JSON.stringify(document.cookie));"
  tabId: <tabId>
```

Then read the output:

```
Tool: mcp__claude-in-chrome__read_console_messages
Params:
  tabId: <tabId>
```

Also check localStorage and sessionStorage for tokens:

```
Tool: mcp__claude-in-chrome__javascript_tool
Params:
  code: |
    console.log(JSON.stringify({
      localStorage: {...localStorage},
      sessionStorage: {...sessionStorage},
      cookie: document.cookie
    }));
  tabId: <tabId>
```

---

## 3. Reconnaissance Patterns

Run each snippet via `mcp__claude-in-chrome__javascript_tool`, then read results with `mcp__claude-in-chrome__read_console_messages`.

### Extract All Links

```javascript
console.log(JSON.stringify(
  [...document.querySelectorAll('a[href]')].map(a => ({
    text: a.textContent.trim(),
    href: a.href
  }))
));
```

### Extract All Forms (Actions + Inputs)

```javascript
console.log(JSON.stringify(
  [...document.querySelectorAll('form')].map(form => ({
    action: form.action,
    method: form.method,
    inputs: [...form.querySelectorAll('input, select, textarea')].map(el => ({
      name: el.name,
      type: el.type,
      value: el.value,
      id: el.id
    }))
  }))
));
```

### Extract All JS File URLs

```javascript
console.log(JSON.stringify(
  [...document.querySelectorAll('script[src]')].map(s => s.src)
));
```

### Read JS Source and Find API Endpoints

Fetch a JS file, extract `/api/` paths, and log them for reading via read_console_messages:

```javascript
fetch('/static/app.js')
  .then(r => r.text())
  .then(src => {
    const matches = src.match(/["'`](\/api\/[^"'`\s]+)["'`]/g) || [];
    console.log(JSON.stringify({
      source_length: src.length,
      api_paths: [...new Set(matches.map(m => m.replace(/["'`]/g, '')))]
    }));
  })
  .catch(e => console.log('fetch error: ' + e));
```

Replace `/static/app.js` with URLs found in the previous step.

### Technology Fingerprinting

```javascript
console.log(JSON.stringify({
  generator:    document.querySelector('meta[name=generator]')?.content,
  react:        !!(window.__REACT_DEVTOOLS_GLOBAL_HOOK__),
  vue:          !!(window.__VUE__),
  angular:      !!(window.ng),
  jquery:       !!(window.jQuery),
  next:         !!(window.__NEXT_DATA__),
  server_info:  document.querySelector('meta[name=generator]')?.content,
  powered_by:   null  // check network headers separately
}));
```

### Network Request Monitoring

```
Tool: mcp__claude-in-chrome__read_network_requests
Params:
  tabId: <tabId>
```

Key response headers to inspect:
- `X-Powered-By` — reveals server technology (e.g., Express, PHP)
- `Server` — web server version
- `Content-Security-Policy` — check for weak/missing directives
- `Set-Cookie` — check for missing `Secure`, `HttpOnly`, `SameSite` flags
- `Access-Control-Allow-Origin` — look for wildcard or reflected origin

---

## 4. Vulnerability Testing Patterns

### XSS Testing

**Reflected XSS** — Navigate with payload in a URL parameter, then check console for execution evidence:

```
Tool: mcp__claude-in-chrome__navigate
Params:
  url:   "https://target.example.com/search?q=<script>console.log('XSS_REFLECTED')</script>"
  tabId: <tabId>
```

Then read console:

```
Tool: mcp__claude-in-chrome__read_console_messages
Params:
  tabId: <tabId>
```

If `XSS_REFLECTED` appears, reflected XSS is confirmed.

**Stored XSS** — Submit payload via form, then revisit the page:

```
Tool: mcp__claude-in-chrome__form_input
Params:
  selector: "#comment-input"
  value:    "<img src=x onerror=\"console.log('XSS_STORED')\">"
  tabId:    <tabId>
```

Navigate away and back, then read console messages to confirm execution.

**DOM XSS** — Check for dangerous sinks:

```javascript
// Check for innerHTML, eval, document.write sinks in event handlers
const sinks = [];
document.querySelectorAll('[onclick],[onerror],[onload]').forEach(el => {
  sinks.push({ tag: el.tagName, attr: el.getAttribute('onclick') || el.getAttribute('onerror') });
});
console.log(JSON.stringify(sinks));
```

Also search inline scripts for dangerous patterns:

```javascript
const scripts = [...document.querySelectorAll('script:not([src])')].map(s => s.textContent);
const dangerous = scripts.filter(s =>
  /innerHTML|eval\(|document\.write|setTimeout\(.*location/.test(s)
);
console.log(JSON.stringify({ dangerous_script_count: dangerous.length, samples: dangerous.slice(0,2) }));
```

---

### CSRF Testing

**Check for CSRF tokens in forms:**

```javascript
console.log(JSON.stringify(
  [...document.querySelectorAll('form')].map(form => ({
    action: form.action,
    method: form.method,
    csrf_fields: [...form.querySelectorAll('input[type=hidden]')].map(i => ({
      name: i.name,
      value: i.value.substring(0, 16) + '...'
    }))
  }))
));
```

**Check SameSite cookie attribute via network requests:**

```
Tool: mcp__claude-in-chrome__read_network_requests
Params:
  tabId: <tabId>
```

Look for `Set-Cookie` headers missing `SameSite=Strict` or `SameSite=Lax`.

---

### CORS Testing

Submit a cross-origin fetch with credentials and check returned headers:

```javascript
fetch('https://target.example.com/api/user', {
  method: 'GET',
  credentials: 'include',
  headers: { 'Origin': 'https://evil.example.com' }
})
.then(r => {
  const headers = {};
  r.headers.forEach((v, k) => headers[k] = v);
  console.log(JSON.stringify({
    status: r.status,
    cors_headers: {
      acao: headers['access-control-allow-origin'],
      acac: headers['access-control-allow-credentials'],
      acam: headers['access-control-allow-methods']
    }
  }));
});
```

Vulnerability indicators:
- `Access-Control-Allow-Origin: https://evil.example.com` with `Access-Control-Allow-Credentials: true` — critical CORS misconfiguration
- `Access-Control-Allow-Origin: *` — cannot be used with credentials, but may expose data

---

### IDOR Testing

Navigate to a resource with one ID, then swap the ID to another user's resource:

```
Tool: mcp__claude-in-chrome__navigate
Params:
  url:   "https://target.example.com/api/orders/1001"
  tabId: <tabId>
```

Then try:

```
Tool: mcp__claude-in-chrome__navigate
Params:
  url:   "https://target.example.com/api/orders/1002"
  tabId: <tabId>
```

Read page content to compare whether a different user's data is returned:

```
Tool: mcp__claude-in-chrome__get_page_text
Params:
  tabId: <tabId>
```

---

### JWT Analysis

Extract JWT from storage and decode header + payload:

```javascript
const sources = {
  cookie:          document.cookie,
  localStorage:    JSON.stringify({...localStorage}),
  sessionStorage:  JSON.stringify({...sessionStorage})
};

// Find JWT-like strings (three base64url segments separated by dots)
const jwtRegex = /eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*/g;
const found = JSON.stringify(sources).match(jwtRegex) || [];

const decoded = found.map(jwt => {
  const [h, p] = jwt.split('.');
  try {
    return {
      raw: jwt.substring(0, 30) + '...',
      header:  JSON.parse(atob(h.replace(/-/g,'+').replace(/_/g,'/'))),
      payload: JSON.parse(atob(p.replace(/-/g,'+').replace(/_/g,'/')))
    };
  } catch(e) { return { raw: jwt, error: e.message }; }
});

console.log(JSON.stringify(decoded));
```

Key weaknesses to look for:
- `"alg": "none"` — unsigned token accepted
- `"alg": "HS256"` with a weak or guessable secret
- Short expiry not enforced, or `exp` claim missing
- Sensitive data (PII, roles) in the payload

---

### Open Redirect Testing

Navigate with a redirect payload, then check where the page ends up:

```
Tool: mcp__claude-in-chrome__navigate
Params:
  url:   "https://target.example.com/login?next=https://evil.example.com"
  tabId: <tabId>
```

After navigation, check the resulting URL:

```javascript
console.log(JSON.stringify({
  href:     window.location.href,
  hostname: window.location.hostname
}));
```

If `hostname` is `evil.example.com`, an open redirect is confirmed.

---

### Business Logic Testing

**Price Manipulation** — Edit a DOM value before form submission:

```javascript
// Set item price to 0.01 before checkout
document.querySelector('input[name=price]').value = '0.01';
document.querySelector('input[name=total]').value = '0.01';
console.log('Price values overwritten');
```

**Step Skipping** — Navigate directly to a later step in a multi-step flow:

```
Tool: mcp__claude-in-chrome__navigate
Params:
  url:   "https://target.example.com/checkout/step3/confirm"
  tabId: <tabId>
```

Check whether the server enforces step order or allows jumping ahead.

---

## 5. GIF Evidence Recording

Use GIF recording to capture proof-of-concept evidence for reports.

### Start Recording

```
Tool: mcp__claude-in-chrome__gif_creator
Params:
  action: "start"
  tabId:  <tabId>
```

### Capture Technique

- Before a key action, take an extra frame by running a no-op script to pad the timeline.
- After the key action (e.g., XSS alert, IDOR data leak), allow 1-2 seconds for the page to settle before stopping.
- For smooth playback, insert a brief pause between steps using:

```javascript
// No-op used as a frame pause marker
console.log('frame_pause');
```

### Stop Recording

```
Tool: mcp__claude-in-chrome__gif_creator
Params:
  action: "stop"
  tabId:  <tabId>
```

The tool returns a path or URL to the recorded GIF. Include this in the bug report as evidence.

---

## 6. Network Analysis

### Read Network Requests

```
Tool: mcp__claude-in-chrome__read_network_requests
Params:
  tabId: <tabId>
```

What to look for:

| Signal | Implication |
|---|---|
| Hidden `/api/` endpoints not in the UI | Undocumented attack surface |
| Auth tokens in query parameters | Token leakage via Referer/logs |
| Internal IP addresses (10.x, 172.x, 192.168.x) | SSRF surface, internal exposure |
| Debug endpoints (`/debug`, `/_health`, `/metrics`) | Information disclosure |
| Sensitive data in response bodies | PII exposure, data leak |
| `X-Powered-By: Express 4.17` | Version-specific CVEs |
| Missing or weak CSP | XSS escalation possible |
| `Set-Cookie` without `Secure;HttpOnly;SameSite` | Session hijack / CSRF risk |

### Read Console Messages

```
Tool: mcp__claude-in-chrome__read_console_messages
Params:
  tabId: <tabId>
```

What to look for:

| Signal | Implication |
|---|---|
| Stack traces with file paths | Source map / path disclosure |
| API keys or tokens logged | Credential exposure |
| SQL error strings | SQL injection surface |
| Debug URLs or internal hostnames | SSRF / internal network recon |
| `console.log` output from injected payloads | XSS / code injection confirmed |

---

## 7. Scope Enforcement

Before every navigation, verify the target hostname is in scope.

### Check Current Hostname

```javascript
console.log(JSON.stringify({
  hostname: window.location.hostname,
  href:     window.location.href
}));
```

### Scope Check Pattern

Compare the hostname against the scope configuration before navigating:

```javascript
const inScopePatterns    = ['target.example.com', 'api.target.example.com'];
const outOfScopePatterns = ['admin.internal.example.com', 'corporate.example.com'];

const host = window.location.hostname;
const inScope    = inScopePatterns.some(p => host === p || host.endsWith('.' + p));
const outOfScope = outOfScopePatterns.some(p => host === p || host.endsWith('.' + p));

console.log(JSON.stringify({
  host,
  in_scope:     inScope,
  out_of_scope: outOfScope,
  safe_to_test: inScope && !outOfScope
}));
```

If `safe_to_test` is `false`, stop and do not proceed with the navigation.

### Scope Check Before Every Navigate Call

```
Tool: mcp__claude-in-chrome__javascript_tool  (scope check)
  -> confirm safe_to_test: true

Tool: mcp__claude-in-chrome__navigate
  url: <only if scope confirmed>
```

Never navigate to a URL before confirming hostname scope. Out-of-scope testing may violate the program's terms and invalidate the report.
