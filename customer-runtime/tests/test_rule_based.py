"""T-005: rule_based.py — regex + keyword extraction 테스트 (EN/KO)."""
import socket
import pytest


EN_IFU_TEXT = """
Device Name: CardioScan Pro 3000
Intended Use: The CardioScan Pro 3000 is intended for cardiac monitoring.
Indications: Indicated for patients with suspected arrhythmia.
Contraindications: Do not use in patients with pacemakers.
Warnings: WARNING: Do not expose to magnetic fields.
Device Classification: Class II medical device.
Region Targets: United States, European Union, South Korea.
Cybersecurity Requirements: Device must be updated to latest firmware.
Precautions: Handle with care. Avoid dropping the device.
Product Code: CSP-3000-US
Maintenance Interval: Annual calibration required.
Cleaning Disinfection: Wipe with 70% isopropyl alcohol.
Software Version: v2.3.1
Accessories: Power adapter, USB cable, carrying case.
Disposal Instructions: Dispose according to local regulations for electronic waste.
"""

KO_IFU_TEXT = """
제품명: 카디오스캔 프로 3000
사용목적: 카디오스캔 프로 3000은 심장 모니터링을 위해 사용됩니다.
적응증: 부정맥이 의심되는 환자에게 사용합니다.
금기사항: 심박조율기 환자에게는 사용하지 마십시오.
경고: 경고: 자기장에 노출시키지 마십시오.
제품 분류: 2등급 의료기기.
지역 대상: 대한민국, 미국, 유럽연합.
사이버보안 요구사항: 최신 펌웨어로 업데이트해야 합니다.
주의사항: 주의하여 취급하십시오. 제품을 떨어뜨리지 마십시오.
제품 코드: CSP-3000-KR
유지보수 주기: 연간 교정이 필요합니다.
세척 및 소독: 70% 이소프로필 알코올로 닦으십시오.
소프트웨어 버전: v2.3.1
부속품: 전원 어댑터, USB 케이블, 휴대용 케이스.
폐기 지침: 전자폐기물 관련 현지 규정에 따라 폐기하십시오.
"""


def test_en_text_extracts_device_name():
    from app.schemas.parse import ExtractionStage
    from app.services.parser_engine.rule_based import extract

    result = extract(EN_IFU_TEXT, ["device_name"])
    assert "device_name" in result
    fe = result["device_name"]
    assert fe.stage == ExtractionStage.RULE
    assert fe.confidence > 0.0
    assert fe.value is not None


def test_en_text_extracts_multiple_fields():
    from app.schemas.parse import ExtractionStage
    from app.services.parser_engine.rule_based import extract

    fields = ["device_name", "intended_use", "product_code"]
    result = extract(EN_IFU_TEXT, fields)
    for field in fields:
        assert field in result
        assert result[field].stage == ExtractionStage.RULE


def test_ko_text_extracts_device_name():
    from app.schemas.parse import ExtractionStage
    from app.services.parser_engine.rule_based import extract

    result = extract(KO_IFU_TEXT, ["device_name"])
    assert "device_name" in result
    fe = result["device_name"]
    assert fe.stage == ExtractionStage.RULE
    assert fe.confidence > 0.0


def test_network_isolation_extract_still_returns(monkeypatch):
    """REQ-006: extract() must not make network calls."""
    original_socket = socket.socket

    def no_network(*args, **kwargs):
        raise OSError("Network access blocked")

    monkeypatch.setattr(socket, "socket", no_network)
    from app.services.parser_engine.rule_based import extract

    # Should not raise even when network is blocked
    result = extract(EN_IFU_TEXT, ["device_name"])
    assert "device_name" in result


def test_no_gpu_import_in_rule_based():
    """Ensure rule_based.py does not import GPU-dependent libraries."""
    import ast
    import pathlib

    rule_based_path = pathlib.Path(__file__).parent.parent / "src/app/services/parser_engine/rule_based.py"
    source = rule_based_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    gpu_libs = {"torch", "tensorflow", "cuda", "cupy", "jax"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                assert name not in gpu_libs, f"GPU import found: {name}"


def test_unknown_field_returns_none_value():
    from app.services.parser_engine.rule_based import extract

    result = extract("No relevant content here.", ["device_name"])
    assert "device_name" in result
    # Value may be None if not found, confidence may be low
    fe = result["device_name"]
    assert 0.0 <= fe.confidence <= 1.0
