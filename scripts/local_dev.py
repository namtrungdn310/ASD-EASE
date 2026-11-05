"""Chuẩn bị cấu hình cho npm run dev; stdout chỉ có metadata, không có secret."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess

from setup_local_mqtt import provision

ROOT = Path(__file__).resolve().parents[1]
HEADER = Path('ai/edge_firmware/include/network_config.h')


def read_env(path):
    if not path.exists():
        return {}
    return {key.strip(): value.strip().strip('\"\'')
            for line in path.read_text(encoding='utf-8-sig').splitlines()
            if line.strip() and not line.lstrip().startswith('#') and '=' in line
            for key, value in [line.split('=', 1)]}


def write_env(path, updates):
    lines = path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else []
    seen = set()
    for index, line in enumerate(lines):
        key = line.split('=', 1)[0].strip()
        if key in updates:
            lines[index] = f'{key}={updates[key]}'
            seen.add(key)
    lines += [f'{key}={value}' for key, value in updates.items() if key not in seen]
    wire = '\n'.join(lines) + '\n'
    if not path.exists() or path.read_text(encoding='utf-8-sig') != wire:
        path.write_text(wire, encoding='utf-8', newline='\n')


def definitions(source):
    result = {}
    pattern = r'^\s*#define\s+(\w+)\s+("(?:\\.|[^"\\])*"|[^\s/]+)'
    for name, token in re.findall(pattern, source, re.M):
        try:
            result[name] = json.loads(token)
        except ValueError:
            raise ValueError(f'Không đọc được #define {name}; dùng chuỗi trong nháy kép hoặc số nguyên.') from None
    return result


def set_definitions(source, updates):
    for name, value in updates.items():
        line = f'#define {name} {json.dumps(value, ensure_ascii=False)}'
        pattern = rf'^\s*#define\s+{re.escape(name)}\s+[^\r\n]*$'
        if re.search(pattern, source, re.M):
            source = re.sub(pattern, lambda _: line, source, flags=re.M)
        else:
            source += '\n' + line + '\n'
    return source


def usable_ip(value):
    try:
        address = ipaddress.ip_address(value)
        return address.version == 4 and address.is_private and not (
            address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast)
    except ValueError:
        return False


def lan_addresses():
    preferred = []
    if os.name == 'nt':
        query = ('@(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | '
                 'ForEach-Object { $_.IPv4Address.IPAddress }) | ConvertTo-Json -Compress')
        run = subprocess.run(['powershell', '-NoProfile', '-Command', query], capture_output=True, text=True)
        if run.returncode == 0 and run.stdout.strip():
            values = json.loads(run.stdout)
            preferred = values if isinstance(values, list) else [values]
    all_ips = {entry[4][0] for entry in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    return list(dict.fromkeys(value for value in [*preferred, *sorted(all_ips)] if usable_ip(value)))


def prepare(root=ROOT, *, addresses=None, provisioner=provision):
    root = Path(root).resolve()
    addresses = lan_addresses() if addresses is None else addresses
    if not addresses:
        raise ValueError('Chưa có IPv4 LAN. Kết nối laptop với Wi-Fi/router/hotspot trước.')
    header = root / HEADER
    exists = header.exists()
    source = (header if exists else header.with_name('network_config.example.h')).read_text(encoding='utf-8-sig')
    config = definitions(source)
    host = str(config.get('MQTT_BROKER_HOST', ''))
    if not host or host == '192.168.x.x':
        host = addresses[0]
    if host not in addresses or not usable_ip(host):
        raise ValueError('MQTT_BROKER_HOST trong network_config.h phải là IPv4 LAN hiện tại của laptop. '
                         'IP đang có: ' + ', '.join(addresses) + '. Sửa header và nạp lại ESP sau khi đổi mạng.')
    port = config.get('MQTT_BROKER_PORT', 1883)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('MQTT_BROKER_PORT phải là số nguyên1..65535.')
    if config.get('MQTT_USE_TLS', 0) != 0:
        raise ValueError('Launcher local dùng broker LAN plaintext. Không tự hạ TLS; đối chiếu cấu hình TLS riêng trước.')
    device_id = config.get('MQTT_DEVICE_ID', 'ESP32-001')
    if not isinstance(device_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', device_id):
        raise ValueError('MQTT_DEVICE_ID không hợp lệ.')

    environment = read_env(root / '.env')
    project = environment.get('COMPOSE_PROJECT_NAME', 'asd-ease-local')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', project):
        raise ValueError('COMPOSE_PROJECT_NAME không hợp lệ.')
    directory = (root / environment.get('MQTT_LOCAL_DIR', './infra/mosquitto/local/dev')).resolve()
    if not directory.is_relative_to(root / 'infra/mosquitto/local'):
        raise ValueError('MQTT_LOCAL_DIR cho launcher phải nằm trong infra/mosquitto/local/ đã được Git bỏ qua.')
    fresh = not directory.exists() or not any(directory.iterdir())
    if fresh:
        provisioner(directory, device_id=device_id)
    required = ['backend.env', 'firmware-device.json', 'device-registry.json', 'passwords', 'acl']
    if not all((directory / name).is_file() for name in required):
        raise ValueError('Thư mục local chưa đủ credential/registry/ACL. Giữ nguyên để đối chiếu, không ghi đè cấu hình dở.')
    identity = json.loads((directory / 'firmware-device.json').read_text())
    registry = json.loads((directory / 'device-registry.json').read_text())
    if identity.get('device_id') != device_id or identity.get('data_origin') != 'DEVICE':
        raise ValueError('Device ID trong header khác bộ credential local. Đối chiếu trước; không tự đổi identity.')
    if not any(row.get('device_id') == device_id and row.get('data_origin') == 'DEVICE'
               and row.get('transport') == 'mqtt' and row.get('mqtt_username') == identity.get('username') for row in registry):
        raise ValueError('Registry không khớp identity MQTT của thiết bị.')
    backend = read_env(directory / 'backend.env')
    if any(len(backend.get(key, '')) < 32 for key in ['OPERATOR_TOKEN', 'COOKIE_SECRET']):
        raise ValueError('Bộ local thiếu secret người vận hành/cookie hợp lệ.')
    if not identity.get('password') or not identity.get('username') or identity['username'] == backend.get('MQTT_USERNAME'):
        raise ValueError('Credential thiết bị phải riêng với backend.')

    updated = set_definitions(source, {
        'ASD_NETWORK_ENABLED': 1, 'MQTT_DEVICE_ID': device_id,
        'MQTT_BROKER_HOST': host, 'MQTT_BROKER_PORT': port,
        'MQTT_USERNAME': identity['username'], 'MQTT_PASSWORD': identity['password'],
        'MQTT_USE_TLS': 0, 'ASD_ALLOW_INSECURE_LAN': 1, 'BACKEND_HOST': host,
    })
    changed = not exists or updated != source
    if changed:
        header.write_text(updated, encoding='utf-8', newline='\n')
    origins = 'http://localhost:5173,http://127.0.0.1:5173'
    write_env(directory / 'backend.env', {'CORS_ORIGINS': origins})
    relative = './' + directory.relative_to(root).as_posix()
    compose = {'COMPOSE_PROJECT_NAME': project, 'MQTT_LOCAL_DIR': relative,
               'MQTT_BIND_IP': host, 'MQTT_HOST_PORT': str(port), 'APP_BIND_IP': '127.0.0.1'}
    write_env(root / '.env', compose)
    return {'compose': compose, 'credentialsDirectory': str(directory), 'deviceId': device_id,
            'brokerHost': host, 'brokerPort': port, 'firmwareChanged': changed,
            'wifiConfigured': all(config.get(key) not in (None, '', 'CHANGE_ME') for key in ['WIFI_SSID', 'WIFI_PASSWORD'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.parse_args()
    try:
        print(json.dumps(prepare(), ensure_ascii=False))
    except ValueError as error:
        import sys
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except (OSError, subprocess.CalledProcessError):
        # Không dump biến config, header hay đầu vào JSON có secret.
        import sys
        print('Không chuẩn bị được cấu hình local. Kiểm tra network_config.h/IP LAN và bộ credential local.', file=sys.stderr)
        raise SystemExit(1)
