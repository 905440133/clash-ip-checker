import os
import sys
import base64
import urllib.parse
import json
import socket
from curl_cffi import requests # 引入强力突破 Cloudflare 的指纹伪装库

def fetch_subscription(url):
    url = url.strip().strip("'").strip('"')
    
    if "flag=" not in url:
        connector = "&" if "?" in url else "?"
        url = f"{url}{connector}flag=shadowrocket"
        
    print(f"实际请求的订阅链接: {url}")
    
    try:
        print("正在伪装成真实 Chrome 浏览器底层指纹发起请求...")
        headers = {
            "User-Agent": "Shadowrocket/2182 (iOS 17.5; iPhone15,2)",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9"
        }
        # impersonate="chrome110" 会完美伪装真实浏览器的 TLS 特征
        response = requests.get(url, headers=headers, impersonate="chrome110", timeout=15)
        
        content = response.text.strip()
        if "<title>403" not in content and "<html>" not in content.lower() and content:
            print("✅ 成功穿透 Cloudflare 防火墙，获取到真实的节点数据！")
            return content
        else:
            print("⚠️ 仍被拦截，返回内容前 200 字:")
            print(content[:200])
    except Exception as e:
        print(f"❌ 请求失败: {e}")
            
    return None

def decode_sub(content):
    content = content.strip()
    try:
        padded = content + '=' * (-len(content) % 4)
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
        if "://" in decoded:
            return [line.strip() for line in decoded.splitlines() if line.strip()]
    except Exception:
        pass
    return [line.strip() for line in content.splitlines() if line.strip()]

def get_ip_info(host):
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        return None, None

    url = f"http://ip-api.com/json/{ip}?fields=status,hosting"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == 'success':
                return ip, data.get('hosting')
    except Exception:
        pass
    return ip, None

def process_line(line):
    line = line.strip()
    if not line or "://" not in line:
        return line

    server_host = None
    node_name = "节点"

    if line.startswith("vmess://"):
        try:
            b64_part = line[8:]
            b64_part += '=' * (-len(b64_part) % 4)
            data = json.loads(base64.b64decode(b64_part).decode('utf-8', errors='ignore'))
            server_host = data.get("add")
            node_name = data.get("ps", "vmess")
        except Exception:
            return line
    else:
        if "#" in line:
            main_part, frag = line.split("#", 1)
            node_name = urllib.parse.unquote(frag)
        else:
            main_part = line
        try:
            parsed = urllib.parse.urlparse(main_part)
            server_host = parsed.hostname
        except Exception:
            server_host = None

    if not server_host:
        return line

    ip, is_hosting = get_ip_info(server_host)

    if is_hosting is False:
        tag = "[🏠住宅]"
    elif is_hosting is True:
        tag = "[🏢机房]"
    else:
        tag = "[❓未知]"

    new_node_name = f"{tag} {node_name}"

    if line.startswith("vmess://"):
        try:
            b64_part = line[8:] + '=' * (-len(b64_part) % 4)
            data = json.loads(base64.b64decode(b64_part).decode('utf-8', errors='ignore'))
            data["ps"] = new_node_name
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')
            return f"vmess://{new_b64}"
        except Exception:
            return line
    else:
        main_part = line.split("#", 1)[0]
        return f"{main_part}#{urllib.parse.quote(new_node_name)}"

def main():
    sub_url = os.environ.get("SUB_URL")
    if not sub_url:
        print("错误：未设置 SUB_URL！")
        sys.exit(1)

    raw_content = fetch_subscription(sub_url)
    
    if not raw_content:
        print("错误：无法获取订阅！")
        sys.exit(1)

    lines = decode_sub(raw_content)
    print(f"解析到 {len(lines)} 个节点，正在处理...")

    new_lines = []
    for line in lines:
        if line.strip():
            new_lines.append(process_line(line))

    result_raw = "\n".join(new_lines)
    result_b64 = base64.b64encode(result_raw.encode('utf-8')).decode('utf-8')

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(result_b64)
        
    with open("raw.txt", "w", encoding="utf-8") as f:
        f.write(result_raw)

    print("✅ 处理完毕并保存文件！")

if __name__ == "__main__":
    main()
