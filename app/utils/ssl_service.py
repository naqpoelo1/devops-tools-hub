import ssl
import socket
import datetime
import requests
import ipaddress
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def is_valid_target(hostname: str) -> bool:
    """
    Check if target is valid.
    Previously blocked private IPs for SSRF protection.
    Now ALLOWS private/local IPs for internal network scanning.
    """
    return True

def check_security_headers(hostname: str) -> dict:
    """
    Fetches HTTP headers and evaluates them strictly based on modern security standards.
    Returns penalty score (negative) and details.
    """
    target_url = f"https://{hostname}"
    headers_info = {
        "score_penalty": 0,
        "details": [],
        "raw": {},
        "missing_critical": [] 
    }

    try:
        # Browser-like User-Agent to avoid WAF/Firewall blocking
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Disable InsecureRequestWarning because we strictly set verify=False
        # (SSL Validation is done separately in get_ssl_details via socket)
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        # verify=False: To allow fetching headers even if SSL is considered invalid by container (e.g. Self-Signed)
        resp = requests.get(target_url, headers=req_headers, timeout=10, allow_redirects=True, verify=False)
        
        headers = {k.lower(): v for k, v in resp.headers.items()} 
        headers_info["raw"] = dict(resp.headers)

        # --- STRICT RULES DEFINITION (ADDITIVE - MAX 40 POINTS) ---
        checks = [
            {
                "key": "strict-transport-security",
                "label": "HSTS",
                "desc": "Prevents Man-in-the-Middle & enforces HTTPS.",
                "points": 10
            },
            {
                "key": "content-security-policy",
                "label": "CSP",
                "desc": "Primary mitigation for XSS & Data Injection attacks.",
                "points": 10
            },
            {
                "key": "x-frame-options",
                "label": "X-Frame-Options",
                "desc": "Prevents Clickjacking attacks.",
                "points": 5
            },
            {
                "key": "x-content-type-options",
                "label": "X-Content-Type",
                "desc": "Prevents MIME-Sniffing (nosniff).",
                "points": 5
            },
            {
                "key": "referrer-policy",
                "label": "Referrer-Policy",
                "desc": "Controls referrer data privacy.",
                "points": 5
            },
            {
                "key": "permissions-policy",
                "label": "Permissions-Policy",
                "desc": "Controls browser features (camera, mic, etc).",
                "points": 5
            }
        ]

        # Info Leak Checks (Warning Only)
        leak_checks = [
            {"key": "server", "label": "Server Info Leak"},
            {"key": "x-powered-by", "label": "X-Powered-By Leak"},
            {"key": "x-aspnet-version", "label": "ASP.NET Version Leak"}
        ]

        total_points = 0
        details = []

        # 1. Check Headers (Bonus Points)
        for check in checks:
            val = headers.get(check["key"])
            item = {
                "name": check["label"],
                "header": check["key"],
                "value": val,
                "desc": check["desc"],
                "status": "missing"
            }

            if val:
                item["status"] = "good"
                total_points += check["points"]
            else:
                item["status"] = "missing"
            
            details.append(item)

        # 2. Check Info Leaks (No Score Impact, just warning)
        for check in leak_checks:
            val = headers.get(check["key"])
            if val:
                details.append({
                    "name": check["label"],
                    "header": check["key"],
                    "value": val,
                    "desc": "Potentially helps hackers identify server version.",
                    "status": "warning"
                })

        headers_info["details"] = details
        headers_info["score_bonus"] = total_points

    except Exception as e:
        logger.warning(f"Failed to fetch headers for {hostname}: {e}")
        headers_info["error"] = str(e)

    return headers_info


def get_ssl_details(url_or_domain: str):
    """
    Connect to a domain, retrieve SSL certificate, calculate grade based on ADDITIVE POINTS.
    """
    # 1. Clean Input
    hostname = url_or_domain.strip()
    if "://" in hostname:
        parsed = urlparse(hostname)
        hostname = parsed.netloc or parsed.path
    if "/" in hostname:
        hostname = hostname.split("/")[0]
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    # Validate Hostname to prevent SSRF
    if not is_valid_target(hostname):
         return {
            "hostname": hostname,
            "grade": "F",
            "score": 0,
            "valid": False,
            "error": "Invalid target or Restricted IP (Private/Local)",
            "details": {},
            "headers": {}
        }

    port = 443
    context = ssl.create_default_context()
    
    result = {
        "hostname": hostname,
        "grade": "F",
        "score": 0,
        "valid": False,
        "error": None,
        "details": {},
        "headers": {}
    }

    try:
        # 2. SSL / Socket Check
        with socket.create_connection((hostname, port), timeout=5.0) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()
                
                not_after_str = cert['notAfter']
                ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'
                expiry_date = datetime.datetime.strptime(not_after_str, ssl_date_fmt)
                remaining = expiry_date - datetime.datetime.utcnow()
                days_left = remaining.days

                subject = dict(x[0] for x in cert['subject'])
                issuer = dict(x[0] for x in cert['issuer'])
                
                sans = []
                if 'subjectAltName' in cert:
                    sans = [x[1] for x in cert['subjectAltName'] if x[0] == 'DNS']

                details = {
                    "common_name": subject.get('commonName'),
                    "issuer": issuer.get('organizationName') or issuer.get('commonName'),
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "days_left": days_left,
                    "protocol": version,
                    "cipher_name": cipher[0],
                    "cipher_bits": cipher[2],
                    "serial_number": cert.get('serialNumber'),
                    "sans": sans[:10]
                }

                result["details"] = details
                result["valid"] = True

                # --- 3. SCORING SYSTEM (ADDITIVE START = 0) ---
                score = 0
                reasons = []
                critical_failure = False

                # A. BASE SSL SCORE (Max 30)
                if days_left >= 0:
                    score += 30
                    reasons.append("Valid Certificate (+30)")
                else:
                    reasons.append("Certificate EXPIRED (Critical)")
                    critical_failure = True

                # B. PROTOCOL SCORE (Max 20)
                if version == "TLSv1.3":
                    score += 20
                    reasons.append("Modern Protocol TLS 1.3 (+20)")
                elif version == "TLSv1.2":
                    score += 15
                    reasons.append("Standard Protocol TLS 1.2 (+15)")
                else:
                    reasons.append("Obsolete/Weak Protocol (0)")
                    critical_failure = True

                # C. KEY STRENGTH (Max 10)
                if cipher[2] >= 128:
                    score += 10
                    reasons.append("Strong Encryption >= 128 bit (+10)")
                else:
                    reasons.append("Weak Encryption (0)")
                    critical_failure = True

                # D. HEADER BONUS (Max 40)
                header_results = check_security_headers(hostname)
                result["headers"] = header_results
                
                bonus = header_results.get("score_bonus", 0)
                if bonus > 0:
                    score += bonus
                    reasons.append(f"Security Headers Bonus (+{bonus})")
                
                # --- 4. FINAL GRADING RULES ---
                
                # Cap Score at 100
                score = min(100, score)

                if critical_failure:
                    final_grade = "F"
                    score = 0
                else:
                    # Score Mapping
                    # Total Max = 30 + 20 + 10 + 40 = 100
                    
                    if score == 100: final_grade = "A+"
                    elif score >= 85: final_grade = "A"
                    elif score >= 70: final_grade = "B"
                    elif score >= 55: final_grade = "C"
                    elif score >= 40: final_grade = "D"
                    else: final_grade = "F"

                result["score"] = score
                result["grade"] = final_grade
                result["reasons"] = reasons

    except ssl.SSLCertVerificationError as e:
        # Catch specific SSL verification errors
        result["valid"] = False
        err_msg = str(e)
        if "certificate has expired" in err_msg:
             result["error"] = "Certificate has EXPIRED"
        elif "self signed" in err_msg:
             result["error"] = "Self-signed certificate (Untrusted)"
        else:
             result["error"] = f"SSL Verification Failed: {err_msg}"
        logger.warning(f"SSL Verify Error for {hostname}: {e}")

    except Exception as e:
        # General error handling
        result["error"] = str(e)
        logger.error(f"SSL Check Error: {e}")

    return result
