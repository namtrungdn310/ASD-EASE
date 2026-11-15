"""Cấu hình chung cho hai laptop: không mất secret, không thay Wi-Fi, đổi LAN rõ ràng."""
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
from local_dev import HEADER, definitions, prepare, read_env, set_definitions
import local_dev
from types import SimpleNamespace


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'repo'
    directory = (root / HEADER).parent
    directory.mkdir(parents=True)
    (directory / 'network_config.example.h').write_text(
        (REPO / HEADER.with_name('network_config.example.h')).read_text(encoding='utf-8'), encoding='utf-8')
    return root


def provision(directory, *, device_id):
    directory.mkdir(parents=True)
    device = {'device_id': device_id, 'data_origin': 'DEVICE', 'username': 'esp32', 'password': 'device-unit-'+'d'*40}
    (directory / 'firmware-device.json').write_text(json.dumps(device))
    (directory / 'device-registry.json').write_text(json.dumps([
        {'device_id': device_id, 'data_origin': 'DEVICE', 'mqtt_username': 'esp32', 'transport': 'mqtt'},
    ]))
    (directory / 'backend.env').write_text('OPERATOR_TOKEN='+'o'*40+'\nCOOKIE_SECRET='+'c'*40+
                                         '\nMQTT_USERNAME=backend\nMQTT_PASSWORD='+'b'*40+'\n')
    (directory / 'acl').write_text('unit ACL')
    (directory / 'passwords').write_text('unit hashed-password fixture')


def test_first_machine_provisions_config_and_never_returns_secret(checkout):
    result = prepare(checkout, addresses=['192.168.10.5'], provisioner=provision)
    assert result['brokerHost'] == '192.168.10.5'
    assert result['firmwareChanged'] and not result['wifiConfigured']
    config = definitions((checkout / HEADER).read_text(encoding='utf-8'))
    assert config['MQTT_DEVICE_ID'] == 'ESP32-001'
    assert config['MQTT_BROKER_HOST'] == '192.168.10.5'
    assert config['MQTT_USERNAME'] == 'esp32'
    assert config['MQTT_PASSWORD'] == 'device-unit-'+'d'*40
    assert config['ASD_NETWORK_ENABLED'] == 1
    assert 'd'*40 not in json.dumps(result) and 'o'*40 not in json.dumps(result)
    assert read_env(checkout / '.env')['APP_BIND_IP'] == '127.0.0.1'
    backend = read_env(Path(result['credentialsDirectory']) / 'backend.env')
    assert backend['AUTO_SESSION_ENABLED'] == 'true'
    assert backend['AUTO_SESSION_DEVICE_ID'] == 'ESP32-001'


def test_second_run_reuses_credentials_and_preserves_wifi(checkout):
    first = prepare(checkout, addresses=['192.168.10.5'], provisioner=provision)
    header = checkout / HEADER
    header.write_text(set_definitions(header.read_text(encoding='utf-8'),
                                     {'WIFI_SSID': 'unit-wifi', 'WIFI_PASSWORD': 'wifi-unit-secret'}), encoding='utf-8')
    local = Path(first['credentialsDirectory'])
    before = (local / 'firmware-device.json').read_bytes()
    def refuse_rotation(*args, **kwargs):
        raise AssertionError('Không được tạo lại credential')
    result = prepare(checkout, addresses=['192.168.10.5'], provisioner=refuse_rotation)
    assert not result['firmwareChanged'] and result['wifiConfigured']
    assert (local / 'firmware-device.json').read_bytes() == before
    assert definitions(header.read_text(encoding='utf-8'))['WIFI_PASSWORD'] == 'wifi-unit-secret'


def test_lan_ip_change_updates_header_compose_and_keeps_secrets(checkout):
    first = prepare(checkout, addresses=['192.168.10.5'], provisioner=provision)
    header = checkout / HEADER
    local = Path(first['credentialsDirectory'])
    old_operator = read_env(local / 'backend.env')['OPERATOR_TOKEN']
    identity = (local / 'firmware-device.json').read_bytes()
    header.write_text(set_definitions(header.read_text(encoding='utf-8'),
                          {'WIFI_SSID': 'unit-wifi', 'WIFI_PASSWORD': 'unit-password'}), encoding='utf-8')
    result = prepare(checkout, addresses=['172.20.10.3', '172.21.96.1'],
                     primary_addresses=['172.20.10.3'])
    assert result['brokerHostChanged'] and result['firmwareChanged']
    config = definitions(header.read_text(encoding='utf-8'))
    assert config['MQTT_BROKER_HOST'] == config['BACKEND_HOST'] == '172.20.10.3'
    assert config['WIFI_SSID'] == 'unit-wifi' and config['WIFI_PASSWORD'] == 'unit-password'
    assert result['compose']['MQTT_BIND_IP'] == '172.20.10.3'
    assert read_env(checkout / '.env')['MQTT_BIND_IP'] == '172.20.10.3'
    assert (local / 'firmware-device.json').read_bytes() == identity
    header.write_text(set_definitions(header.read_text(encoding='utf-8'),
                                     {'MQTT_BROKER_HOST': '172.20.10.3', 'MQTT_BROKER_PORT': 1884}), encoding='utf-8')
    result = prepare(checkout, addresses=['172.20.10.3'])
    assert result['compose']['MQTT_BIND_IP'] == '172.20.10.3'
    assert result['compose']['MQTT_HOST_PORT'] == '1884'
    assert read_env(local / 'backend.env')['OPERATOR_TOKEN'] == old_operator


def test_same_wifi_new_dhcp_ip_ignores_virtual_adapters(checkout):
    prepare(checkout, addresses=['192.168.68.75'], provisioner=provision)
    result = prepare(checkout, addresses=['172.21.96.1', '192.168.129.1', '192.168.68.62'],
                     primary_addresses=['192.168.68.62'])
    assert result['brokerHost'] == '192.168.68.62'
    assert result['brokerHostChanged']


def test_ambiguous_networks_do_not_change_local_files(checkout):
    first = prepare(checkout, addresses=['192.168.68.75'], provisioner=provision)
    header = checkout / HEADER
    original = header.read_bytes()
    env = (checkout / '.env').read_bytes()
    for candidates in [[], ['192.168.68.62', '192.168.10.2']]:
        with pytest.raises(ValueError, match='duy nhất'):
            prepare(checkout, addresses=['192.168.68.62', '192.168.10.2', '172.21.96.1'],
                    primary_addresses=candidates)
        assert header.read_bytes() == original
        assert (checkout / '.env').read_bytes() == env
    assert (Path(first['credentialsDirectory']) / 'firmware-device.json').exists()


def test_explicit_active_hotspot_ip_is_preserved_even_with_another_default_route(checkout):
    prepare(checkout, addresses=['192.168.137.1'], provisioner=provision)
    result = prepare(checkout, addresses=['192.168.137.1', '192.168.68.62'],
                     primary_addresses=['192.168.68.62'])
    assert result['brokerHost'] == '192.168.137.1'
    assert not result['brokerHostChanged']


def test_hotspot_without_gateway_or_hostname_record_is_detected(monkeypatch):
    monkeypatch.setattr(local_dev.os, 'name', 'nt')
    monkeypatch.setattr(local_dev.socket, 'gethostname', lambda: 'test-laptop')
    monkeypatch.setattr(local_dev.socket, 'getaddrinfo', lambda *args: [
        (None, None, None, None, ('192.168.129.1', 0))])
    def run(args, **kwargs):
        command = args[-1]
        if 'Get-NetIPConfiguration' in command:
            return SimpleNamespace(returncode=0, stdout='["172.15.144.128"]')
        assert 'Get-NetIPAddress' in command
        return SimpleNamespace(returncode=0, stdout='["192.168.137.1","172.21.96.1","127.0.0.1","169.254.1.1"]')
    monkeypatch.setattr(local_dev.subprocess, 'run', run)
    assert local_dev.lan_addresses() == ['192.168.137.1', '172.21.96.1', '192.168.129.1']


def test_partial_configuration_and_identity_changes_are_not_overwritten(checkout):
    first = prepare(checkout, addresses=['192.168.10.5'], provisioner=provision)
    header = checkout / HEADER
    header.write_text(set_definitions(header.read_text(encoding='utf-8'), {'MQTT_DEVICE_ID': 'ESP-OTHER'}), encoding='utf-8')
    original = header.read_bytes()
    with pytest.raises(ValueError, match='Device ID'):
        prepare(checkout, addresses=['192.168.10.5'])
    assert header.read_bytes() == original
    (Path(first['credentialsDirectory']) / 'acl').unlink()
    with pytest.raises(ValueError, match='chưa đủ'):
        prepare(checkout, addresses=['192.168.10.5'])


def test_no_network_or_external_secret_directory_is_rejected(checkout):
    with pytest.raises(ValueError, match='Chưa có IPv4'):
        prepare(checkout, addresses=[])
    (checkout / '.env').write_text('MQTT_LOCAL_DIR=../external\n')
    with pytest.raises(ValueError, match='MQTT_LOCAL_DIR'):
        prepare(checkout, addresses=['192.168.10.5'], provisioner=provision)
