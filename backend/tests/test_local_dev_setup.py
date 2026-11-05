"""Cấu hình chung cho hai laptop: không mất secret, không thay Wi-Fi, đổi LAN rõ ràng."""
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
from local_dev import HEADER, definitions, prepare, read_env, set_definitions


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


def test_wifi_change_uses_header_ip_and_keeps_operator_secrets(checkout):
    first = prepare(checkout, addresses=['192.168.10.5'], provisioner=provision)
    header = checkout / HEADER
    local = Path(first['credentialsDirectory'])
    old_operator = read_env(local / 'backend.env')['OPERATOR_TOKEN']
    with pytest.raises(ValueError, match='MQTT_BROKER_HOST'):
        prepare(checkout, addresses=['172.20.10.3'])
    header.write_text(set_definitions(header.read_text(encoding='utf-8'),
                                     {'MQTT_BROKER_HOST': '172.20.10.3', 'MQTT_BROKER_PORT': 1884}), encoding='utf-8')
    result = prepare(checkout, addresses=['172.20.10.3'])
    assert result['compose']['MQTT_BIND_IP'] == '172.20.10.3'
    assert result['compose']['MQTT_HOST_PORT'] == '1884'
    assert read_env(local / 'backend.env')['OPERATOR_TOKEN'] == old_operator


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
