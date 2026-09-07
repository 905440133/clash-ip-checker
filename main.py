import os
import sys
import base64
import urllib.request
import urllib.parse
import json
import socket

def decode_sub(content):
    content = content.strip()
    try:
        padded = content + '=' * (-len(content) % 4)
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
        if "://" in decoded:
            return decoded.splitlines()
    except Exception:
        pass
    return content.splitlines()

def get_ip_info(host):
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        return None, None

    url = f"http://ip-api.com/json/{ip}?fields=status,countryCode,isp,org,as,hosting"
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
        print("错误：未检测到环境变量 SUB_URL，请在 Settings -> Secrets 中设置！")
        sys.exit(1)

    print("正在获取订阅节点...")
    req = urllib.request.Request(sub_url, headers={'User-Agent': 'Shadowrocket/2.2.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_content = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"下载订阅失败: {e}")
        sys.exit(1)

    lines = decode_sub(raw_content)
    print(f"解析到 {len(lines)} 个节点，正在批量检测 IP 类型...")

    new_lines = []
    for i, line in enumerate(lines, 1):
        if line.strip():
            print(f"正在处理第 [{i}/{len(lines)}] 个节点...")
            new_line = process_line(line)
            new_lines.append(new_line)

    result_raw = "\n".join(new_lines)
    result_b64 = base64.b64encode(result_raw.encode('utf-8')).decode('utf-8')

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(result_b64)

    print("全部检测完成，已导出 sub.txt！")

if __name__ == "__main__":
    main()
