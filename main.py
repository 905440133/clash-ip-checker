import os
import sys
import base64
import urllib.parse
import json
import socket
import subprocess

def fetch_subscription(url):
    url = url.strip().strip("'").strip('"')
    
    # 模拟真实小火箭/Clash客户端请求头，防403
    user_agents = [
        "Shadowrocket/2182 (iOS 17.5; iPhone15,2)",
        "ClashforWindows/0.20.39",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ]
    
    for ua in user_agents:
        print(f"尝试使用 User-Agent 获取订阅: {ua}")
        try:
            cmd = [
                "curl", "-sSL", "--max-time", "15",
                "-H", f"User-Agent: {ua}",
                "-H", "Accept: */*",
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                if "://" in content or len(content) > 20:
                    print("✅ 成功通过 curl 获取到订阅数据！")
                    return content
        except Exception as e:
            print(f"curl 尝试失败: {e}")
            
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

    # 生成标准的明文节点按行分隔
    result_raw = "\n".join(new_lines)
    
    # 严格按照小火箭标准对 UTF-8 文本进行 Base64 编码
    result_b64 = base64.b64encode(result_raw.encode('utf-8')).decode('utf-8')

    # 同时导出明文和 Base64，确保全平台兼容
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(result_b64)
        
    with open("raw.txt", "w", encoding="utf-8") as f:
        f.write(result_raw)

    print("✅ 处理完毕并保存文件！")

if __name__ == "__main__":
    main()
