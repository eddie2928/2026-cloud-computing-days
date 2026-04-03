# Phase 1: Reconnaissance

Complete reconnaissance procedures for web bug bounty targets. Read `references/cli-tools.md` for detailed tool syntax and `references/chrome-testing.md` for Chrome-based recon patterns.

## Recon Pipeline

Execute these steps in order. Save all results to `recon-results.json` at the end.

```
1. Domain Analysis
2. Subdomain Enumeration
3. Live Host Detection
4. Port Scanning
5. Directory/File Discovery
6. Technology Fingerprinting
7. JS Analysis & API Endpoint Mining
8. Interactive Crawling (Chrome)
9. Parameter Discovery
10. Compile Results
```

## Step 1: Domain Analysis

Extract the root domain from each target URL in the scope config.

```bash
# For target url "https://app.example.com/dashboard"
# Root domain: example.com
# Extract with:
echo "https://app.example.com/dashboard" | awk -F/ '{print $3}' | rev | cut -d. -f1,2 | rev
```

## Step 2: Subdomain Enumeration

Run subfinder for each root domain:

```bash
subfinder -d <domain> -silent -o subdomains-raw.txt
```

Filter results against scope config `in_scope` patterns. Remove any subdomain matching `out_of_scope`.

```bash
# Example filter: keep only *.example.com, remove admin.example.com
grep -E "\.example\.com$" subdomains-raw.txt | grep -v "admin" > subdomains.txt
```

## Step 3: Live Host Detection

Probe all discovered subdomains:

```bash
httpx -l subdomains.txt -status-code -title -tech-detect -content-length -web-server -follow-redirects -o live-hosts.txt
```

Parse output to identify:
- Active hosts (200, 301, 302, 403)
- Technology stack per host
- Interesting titles (admin panels, API docs, staging)

## Step 4: Port Scanning

Scan each live host for web-related ports:

```bash
nmap -sV -p 80,443,8080,8443,3000,5000,8000,8888,9090 <host> -oN nmap-<host>.txt
```

Note any non-standard web ports for further testing.

## Step 5: Directory/File Discovery

Run ffuf against each live host:

```bash
ffuf -w ~/SecLists/Discovery/Web-Content/common.txt -u https://<host>/FUZZ -e .php,.asp,.aspx,.jsp,.html,.js,.json,.xml,.bak,.txt,.env,.git,.svn -mc 200,301,302,403 -fs <common-404-size> -rate 10 -o ffuf-<host>.json -of json
```

High-value finds to flag:
- `.env`, `.git/config`, `.svn/entries` — information disclosure
- `/api/`, `/swagger`, `/docs`, `/graphql` — API endpoints
- `/admin`, `/debug`, `/phpinfo` — admin/debug interfaces
- `.bak`, `.old`, `.orig` — backup files

## Step 6: Technology Fingerprinting

Use Chrome to identify frontend frameworks and technologies:

Read `references/chrome-testing.md` section "Technology Fingerprinting" for the JavaScript snippet.

Also check response headers via CLI:

```bash
curl -s -I https://<host> | grep -iE "server|x-powered-by|x-frame-options|content-security-policy|x-xss-protection|strict-transport-security|set-cookie"
```

Record: web server, backend language/framework, frontend framework, CDN, WAF indicators.

## Step 7: JS Analysis & API Endpoint Mining

Use Chrome to extract all JS file URLs (see `references/chrome-testing.md`), then analyze each for:

```bash
# Download and search JS files for sensitive patterns
curl -s https://<host>/static/app.js | grep -oE "(api|v[0-9]+)/[a-zA-Z0-9/_-]+" | sort -u

# Search for hardcoded secrets
curl -s https://<host>/static/app.js | grep -oiE "(api[_-]?key|secret|token|password|auth)['\"]?\s*[:=]\s*['\"][^'\"]+['\"]"

# Search for internal URLs
curl -s https://<host>/static/app.js | grep -oE "https?://[a-zA-Z0-9./_-]+" | sort -u
```

## Step 8: Interactive Crawling (Chrome)

Navigate through the application using Chrome MCP tools:

1. Start at the main page
2. Extract all links (see `references/chrome-testing.md` "Extract All Links")
3. Navigate to each unique path within scope
4. For each page:
   - Extract forms and input fields
   - Note file upload endpoints
   - Note AJAX/fetch requests via network tab
   - Record any error messages
5. Build a site map of all discovered paths, parameters, and forms

## Step 9: Parameter Discovery

For each interesting endpoint, discover hidden parameters:

```bash
arjun -u https://<host>/<path> -o arjun-<path>.json
```

Also check for common hidden parameters manually:
```bash
ffuf -w ~/SecLists/Discovery/Web-Content/burp-parameter-names.txt -u "https://<host>/<path>?FUZZ=test" -mc 200 -fs <baseline-size> -o params-<path>.json -of json
```

## Step 10: Compile Results

Structure all findings into `recon-results.json`:

```json
{
  "target": "example.com",
  "scan_date": "2026-04-02",
  "subdomains": ["api.example.com", "staging.example.com"],
  "live_hosts": [
    {
      "url": "https://api.example.com",
      "status": 200,
      "title": "API Documentation",
      "tech": ["nginx", "Node.js", "Express"],
      "ports": [80, 443]
    }
  ],
  "endpoints": [
    {
      "url": "https://api.example.com/v1/users",
      "method": "GET",
      "params": ["id", "page", "limit"],
      "auth_required": true,
      "source": "js_analysis"
    }
  ],
  "forms": [
    {
      "page": "https://example.com/contact",
      "action": "/api/contact",
      "method": "POST",
      "fields": ["name", "email", "message", "file"]
    }
  ],
  "technologies": {
    "frontend": "React 18",
    "backend": "Express/Node.js",
    "server": "nginx",
    "cdn": "Cloudflare"
  },
  "interesting_files": [
    "https://example.com/.env.bak",
    "https://example.com/swagger.json"
  ],
  "notes": "WAF detected (Cloudflare). API uses JWT auth stored in localStorage."
}
```

This file becomes the input for Phase 2 (Attack).
