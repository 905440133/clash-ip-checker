import os
import sys
import base64
import urllib.parse
import json
import socket
import subprocess

def fetch_subscription(url):
    # 自动清理链接前后的空格、换行符及引号
    url = url.strip().strip("'").strip('"')
    
    # 模拟不同的客户端 User-Agent 依次尝试
    user_agents = [
        "Shadowrocket/2182 (iOS 17.5; iPhone15,2)",
        "ClashforWindows/0.20.39",
        "Clash.Meta",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    for ua in user_agents:
        print(f"正在尝试以 [{ua.split('/')[0]}] 身份获取订阅...")
        try:
            cmd = [
                "curl", "-sSL", "--max-time", "15",
                "-H", f"User-Agent: {ua}",
                "-H", "Accept: */*",
                "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
                "-H", "Connection: keep-alive",
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                # 简单校验返回内容是否包含节点或Base64字符
                if "://" in content or len(content) > 30:
                    print("✅ 成功下载订阅内容！")
                    return content
        except Exception as e:
            print(f"尝试失败: {e}")

    return None

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
    raw_content = fetch_subscription(sub_url)
    if not raw_content:
        print("错误：无法获取订阅，请检查 SUB_URL 链接是否正确，或确认机场订阅开关已开启。")
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
