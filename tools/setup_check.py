"""새 노트북 조작(IL) 환경 점검. 읽기만 한다(팔·토크·카메라 설정을 바꾸지 않는다).

docs/guides/20261030_새노트북_작업인계.md 2절을 마친 뒤 so101_env 파이썬으로 실행하고, 출력 전체를 공유한다.

    & $PY tools\\setup_check.py              # 저장소 루트에서
    & $PY tools\\setup_check.py --pi 192.168.0.159:5600

팔 포트를 열어 보므로 조작 실행기(start_scenario.bat)는 꺼 둔 상태에서 실행한다.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS: list[tuple[str, str, str]] = []  # (상태, 항목, 내용)


def report(status: str, item: str, detail: str = "") -> None:
    RESULTS.append((status, item, detail))
    mark = {"ok": "[OK]  ", "fail": "[FAIL]", "warn": "[WARN]"}[status]
    print(f"{mark} {item}" + (f" - {detail}" if detail else ""), flush=True)


def run(cmd: list[str], timeout: float = 20.0) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout)
        raw = out.stdout + out.stderr
        for enc in ("utf-8", "cp949"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"<실행 실패: {e}>"


def powershell(script: str) -> str:
    return run(["powershell", "-NoProfile", "-Command",
                "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script])


# ---------------------------------------------------------------- 1. 파이썬·GPU·패키지
def check_python() -> None:
    report("ok" if sys.version_info[:2] == (3, 12) else "warn", "파이썬",
           f"{platform.python_version()} ({sys.executable})")
    try:
        import torch

        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            report("ok", "torch·CUDA", f"torch {torch.__version__}, {p.name}, {p.total_memory / 2**30:.1f} GB")
        else:
            report("fail", "torch·CUDA", f"torch {torch.__version__}인데 CUDA를 못 씀(CPU 빌드거나 드라이버 문제)")
    except Exception as e:  # noqa: BLE001
        report("fail", "torch", str(e))


def check_lerobot() -> None:
    # lerobot(pyarrow)을 카메라 COM 열거보다 먼저 불러온다(반대 순서는 access violation, 2026-10-29)
    try:
        import lerobot
        import lerobot.motors  # noqa: F401
        import lerobot.rollout  # noqa: F401

        report("ok", "lerobot 불러오기", str(Path(lerobot.__file__).parent))
    except Exception as e:  # noqa: BLE001
        report("fail", "lerobot 불러오기", str(e))
        return
    try:
        from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

        has_mirror = "mirror" in getattr(OpenCVCameraConfig, "__dataclass_fields__", {})
        report("ok" if has_mirror else "fail", "lerobot 로컬 패치(카메라 mirror)",
               "" if has_mirror else "tools/rollout/lerobot_7e241bd6_local_changes.patch 미적용")
    except Exception as e:  # noqa: BLE001
        report("fail", "lerobot 로컬 패치(카메라 mirror)", str(e))
    try:
        import lerobot.rollout.strategies.base as base

        ok = "consecutive_obs_failures" in Path(base.__file__).read_text(encoding="utf-8")
        report("ok" if ok else "fail", "lerobot 로컬 패치(카메라 지연 허용)", "" if ok else "패치 미적용")
    except Exception as e:  # noqa: BLE001
        report("fail", "lerobot 로컬 패치(카메라 지연 허용)", str(e))
    try:
        import lerobot.robots.bi_so_follower  # noqa: F401
        from lerobot.robots.so_follower.config_so_follower import SOFollowerConfig

        ok = "gripper_protection" in SOFollowerConfig.__dataclass_fields__
        report("ok" if ok else "fail", "lerobot 양팔 로봇(bi_so_follower)·그리퍼 보호", "" if ok else "패치 미적용")
    except Exception as e:  # noqa: BLE001
        report("fail", "lerobot 양팔 로봇(bi_so_follower)", str(e))


def check_packages() -> None:
    for name in ("cv2", "primesense", "pyvirtualcam", "pygrabber", "comtypes", "scservo_sdk", "serial", "transformers"):
        try:
            mod = __import__(name)
            report("ok", f"패키지 {name}", getattr(mod, "__version__", ""))
        except Exception as e:  # noqa: BLE001
            report("fail", f"패키지 {name}", str(e))


# ---------------------------------------------------------------- 2. start_scenario.bat 설정과 모델
def bat_settings() -> dict[str, str]:
    text = (REPO / "tools" / "rollout" / "start_scenario.bat").read_text(encoding="utf-8", errors="replace")
    return dict(re.findall(r"^set (\w+)=(.*)$", text, flags=re.M))


def check_models(cfg: dict[str, str]) -> None:
    py = cfg.get("PY", "")
    report("ok" if Path(py).is_file() else "fail", "start_scenario.bat PY", py)
    if Path(py).is_file() and Path(py).resolve() != Path(sys.executable).resolve():
        report("warn", "실행 중인 파이썬과 bat의 PY가 다름", f"{sys.executable} vs {py}")
    for key in ("POUR", "PLACE"):
        d = Path(cfg.get(key, ""))
        if not (d / "model.safetensors").is_file() or not (d / "config.json").is_file():
            report("fail", f"모델 {key}", f"{d} 에 model.safetensors/config.json 없음")
            continue
        report("ok", f"모델 {key}", str(d))
        pre = d / "policy_preprocessor.json"
        try:
            names = re.findall(r'"tokenizer_name":\s*"([^"]+)"', pre.read_text(encoding="utf-8"))
            bad = [n for n in names if not Path(n).is_dir()]
            if names and not bad:
                report("ok", f"모델 {key} 토크나이저 경로", names[0])
            else:
                report("fail", f"모델 {key} 토크나이저 경로",
                       f"폴더가 없음: {bad or names} (가이드 5-3절: 이 노트북 절대 경로로 고친다)")
        except Exception as e:  # noqa: BLE001
            report("fail", f"모델 {key} 토크나이저 경로", str(e))


# ---------------------------------------------------------------- 3. 팔 포트·모터(읽기만)
def check_arms(cfg: dict[str, str]) -> None:
    try:
        from serial.tools import list_ports

        ports = {p.device: p.description for p in list_ports.comports()}
    except Exception as e:  # noqa: BLE001
        report("fail", "COM 포트 목록", str(e))
        return
    report("ok", "COM 포트 목록", ", ".join(f"{k}({v})" for k, v in ports.items()) or "없음")
    for side, key in (("왼팔", "LEFT_PORT"), ("오른팔", "RIGHT_PORT")):
        port = cfg.get(key, "")
        if port not in ports:
            report("fail", f"{side} 포트 {port}", "연결 안 됨. start_scenario.bat의 " + key + "를 실제 포트로 고친다")
            continue
        try:
            import scservo_sdk as scs

            ph, pk = scs.PortHandler(port), scs.PacketHandler(0)
            ph.openPort()
            ph.setBaudRate(1000000)
            alive, volts = [], []
            for i in range(1, 7):
                _, comm, _ = pk.ping(ph, i)
                if comm == 0:
                    alive.append(i)
                    v, c, _ = pk.read1ByteTxRx(ph, i, 62)
                    if c == 0:
                        volts.append(v / 10)
            ph.closePort()
            if len(alive) == 6:
                low = volts and min(volts) < 9.0
                report("warn" if low else "ok", f"{side} 모터({port})",
                       f"6/6 응답, 전압 {min(volts):.1f}~{max(volts):.1f} V" + (" - 배터리 교체 권장" if low else ""))
            else:
                report("fail", f"{side} 모터({port})", f"응답 {alive} (팔 배터리 OFF이거나 케이블 문제)")
        except Exception as e:  # noqa: BLE001
            report("fail", f"{side} 모터({port})", f"{e} (실행기가 켜져 있으면 끄고 다시)")


# ---------------------------------------------------------------- 4. 카메라·Astra
def check_cameras() -> None:
    sys.path.insert(0, str(REPO / "tools" / "camera"))
    try:
        from astra_sdk import find_sdk_bin

        b = find_sdk_bin()
        ok = (Path(b) / "astra.dll").is_file()
        report("ok" if ok else "fail", "Astra SDK", b if ok else f"{b} 에 astra.dll 없음 - ASTRA_SDK_BIN 지정")
    except Exception as e:  # noqa: BLE001
        report("fail", "Astra SDK", str(e))
    params = REPO / "config" / "camera" / "astra_params.json"
    report("ok" if params.is_file() else "fail", "Astra 보정값", str(params))
    pnp = powershell("Get-PnpDevice -PresentOnly | Where-Object { $_.FriendlyName -match 'ORBBEC Depth' } "
                     "| ForEach-Object { $_.Status }")
    report("ok" if "OK" in pnp else "fail", "Astra 장치(ORBBEC Depth Sensor)",
           "" if "OK" in pnp else "장치 관리자에 없음 - 드라이버 설치·USB 확인")
    try:
        from resolve_camera_indices import (DEPTH_NAME, LEFT_DEVPATH_HINT, RIGHT_DEVPATH_HINT,
                                            enumerate_devices)

        devices = enumerate_devices()
        for i, name, path in devices:
            print(f"        카메라 {i}: {name!r} {path}")
        names = [n for _, n, _ in devices]
        report("ok" if DEPTH_NAME in names else "fail", "OBS Virtual Camera",
               "" if DEPTH_NAME in names else "OBS Studio 설치 필요(가상 카메라 드라이버)")
        for side, hint in (("왼쪽 손목캠", LEFT_DEVPATH_HINT), ("오른쪽 손목캠", RIGHT_DEVPATH_HINT)):
            hit = [i for i, _, p in devices if hint in p]
            report("ok" if hit else "fail", f"{side} 경로 힌트 {hint}",
                   f"카메라 {hit[0]}" if hit else "일치하는 장치 없음 - 가이드 6-3절로 새 노트북 값을 넣는다")
    except Exception as e:  # noqa: BLE001
        report("fail", "카메라 목록", str(e))


# ---------------------------------------------------------------- 5. 네트워크·전원
def check_network(pi: str) -> None:
    wlan = powershell("netsh wlan show interfaces")
    ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", wlan, flags=re.M)
    band = re.search(r"^\s*(?:Band|대역)\s*:\s*(.+)$", wlan, flags=re.M)
    ssid_s = ssid.group(1).strip() if ssid else "?"
    report("ok" if ssid_s.startswith("aicampus_286") else "warn", "Wi-Fi",
           f"{ssid_s} {band.group(1).strip() if band else ''}".strip()
           + ("" if "6G" in ssid_s else " (권장: aicampus_286_6G)"))
    ip = powershell("(Get-NetIPAddress -InterfaceAlias Wi-Fi -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress").strip()
    report("ok" if ip.startswith("192.168.0.") else "warn", "노트북 IP",
           f"{ip} (192.168.0.175가 아니면 주행 담당에게 알리고 QR을 새로 만든다)")
    fw = powershell("Get-NetFirewallRule -Enabled True -Direction Inbound -Action Allow | Where-Object { "
                    "($_ | Get-NetFirewallPortFilter).LocalPort -contains '8765' } | ForEach-Object { $_.DisplayName }")
    report("ok" if fw.strip() else "fail", "방화벽 8765 허용",
           fw.strip() or "규칙 없음 - 관리자 PowerShell에서 New-NetFirewallRule ... -LocalPort 8765")
    host, port = pi.rsplit(":", 1)
    try:
        with socket.create_connection((host, int(port)), timeout=3):
            report("ok", f"Pi 영상 수신기 {pi}", "TCP 연결됨")
    except OSError as e:
        report("warn", f"Pi 영상 수신기 {pi}", f"{e} (Pi 수신기가 꺼져 있거나 다른 Wi-Fi)")
    plan = run(["powercfg", "/getactivescheme"])
    report("ok", "전원 구성", plan.strip().split(":", 1)[-1].strip() + " (배터리 운용 시 최고 성능 모드인지 확인)")


def check_repo() -> None:
    head = run(["git", "-C", str(REPO), "log", "--oneline", "-1"]).strip()
    branch = run(["git", "-C", str(REPO), "branch", "--show-current"]).strip()
    run(["git", "-C", str(REPO), "fetch", "-q", "origin"], timeout=30)
    behind = run(["git", "-C", str(REPO), "rev-list", "--count", "HEAD..origin/main"]).strip()
    ok = branch == "main" and behind == "0"
    report("ok" if ok else "warn", "저장소", f"{branch} @ {head}" + ("" if behind == "0" else f", origin/main보다 {behind}개 뒤"))
    autocrlf = run(["git", "-C", str(REPO), "config", "core.autocrlf"]).strip()
    patch = (REPO / "tools" / "rollout" / "lerobot_7e241bd6_local_changes.patch").read_bytes()
    report("ok" if b"\r\n" not in patch[:20000] else "fail", "패치 파일 줄바꿈(LF)",
           f"core.autocrlf={autocrlf or '미설정'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pi", default="192.168.0.159:5600")
    a = ap.parse_args()
    print(f"== 조작 환경 점검: {platform.node()} ({platform.platform()})")
    check_repo()
    check_python()
    check_lerobot()
    check_packages()
    cfg = bat_settings()
    check_models(cfg)
    check_arms(cfg)
    check_cameras()
    check_network(a.pi)
    fails = [r for r in RESULTS if r[0] == "fail"]
    warns = [r for r in RESULTS if r[0] == "warn"]
    print(f"\n== 결과: 실패 {len(fails)}, 주의 {len(warns)}, 정상 {len(RESULTS) - len(fails) - len(warns)}")
    for s, item, detail in fails + warns:
        print(f"  {'FAIL' if s == 'fail' else 'WARN'} {item}: {detail}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
