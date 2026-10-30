# OMEN 노트북 환경 스냅샷 (2026-10-30)

새 조작 노트북(HP OMEN 16, `LAPTOP-3U29RMFK`)이 기존 ASUS 노트북의 조작(IL)·주문 서버·Astra 송신 작업을 이어받을 준비가 됐는지 기존 노트북 세션이 판단할 수 있게 모은 자료다. 이 폴더는 확인용 사본(`jangjunseo05/test`)에만 있고 팀 저장소(`mmporong/bimanual-robot`)에는 올리지 않는다.

- 코드 기준: 새 클론 `C:\Users\user\Desktop\프로젝트\최종프로젝트\bimanual-robot-git`(`core.autocrlf=false`), `main` @ `39b44e8`(#86) + 이 저장소의 다음 커밋(오늘 로컬 변경 4개 파일).
- 넣지 않은 것: 모델 가중치·데이터셋(해시만), HF 토큰·SSH 키·비밀번호, 노트북 내장 카메라 사진.
- 수집: 2026-10-30 16:52~17:16 KST. 시각은 모두 KST.

## 1. 판정 요약

| 항목 | 상태 | 근거 파일 |
|---|---|---|
| 파이썬·torch·CUDA | ✅ Python 3.12.16, torch 2.11.0+cu128, RTX 4060 Laptop 8GB, 드라이버 592.82 | `env/conda_version.txt`, `system.txt` |
| 고정 패키지 | ✅ `so101_env_requirements.txt` 149개 전부 일치 | `env/requirements_compare.txt`, `env/pip_freeze.txt` |
| lerobot 패치 | ✅ 7e241bd6 + 로컬 변경 10개 파일 = `tools/rollout/lerobot_7e241bd6_local_changes.patch`(index 줄 제외 동일) | `lerobot/` |
| 모델 | ✅ SmolVLA 80(v1 60 + part2 20). 물따르기 016000·컵배치 007000 `model.safetensors` SHA256이 HF `jun-seo/water_pour_chassis_smolvla_80_16000S`·`jun-seo/cup_place_chassis_smolvla_80_7000S`와 일치 | `models/` |
| 토크나이저 경로 | ✅ `policy_preprocessor.json`의 `tokenizer_name` 2곳만 이 노트북 절대 경로로 수정(.bak 대비) | `models/model_files.txt` |
| 팔 포트 | ✅ CH343 `COM3`=왼팔, `COM4`=오른팔(배터리 맞바꾸기로 확인). `start_scenario.bat` 반영 | 3절 |
| 손목캠 | ✅ 왼쪽 `2bd3af6b`(Innomaker, 그대로), 오른쪽 `1b3f2dc8`→`2353db1a`(USB 2.0 PC Cam). `resolve_camera_indices.py` → left=1 right=2 depth=4 | `cameras/` |
| Astra | ✅ SDK 2.1.3(`Downloads`), 드라이버 4.3.0.22, ORBBEC 장치 OK, OBS Virtual Camera OK, Pi `192.168.0.159:5600` 송신 연결=True | `system.txt`, `logs/astra_bridge_camera_tail.txt` |
| 네트워크 | ✅ `aicampus_286_6G` 6 GHz, `192.168.0.157`(DHCP, 고정 할당 불가), 방화벽 `order-server 8765` 허용 | `system.txt` |
| 전원 | ✅ 절전·최대 절전·화면 꺼짐·USB 선택적 절전 끔(AC/DC), 전원 모드 오버레이 최고 성능(AC/DC) | `system.txt` |
| 오른팔 배터리 | ⚠ 원래 오른팔 배터리 방전 → 충전 대기 | 3절 |
| 통합 추론 속도 | ❌ 16:52 물따르기 추론 2.94 s(정상 0.45~0.5 s) → 동작 끊김·시간 초과 | 4절 |
| 왼쪽 손목캠 | ⚠ 실행 중 반복 끊김(멈춘 화면 28 s·22 s, 15:56 실행 44 s) | 4절 |
| 예약 작업 | ⚠ `AMRArmService`·`AMRAstraCamera`·`AMROrderServer`가 옛 클론으로 실행 중. 중지는 자동 권한 검사 거부로 사용자 실행 대기 | 5절, `status_at_upload.txt` |

## 2. setup_check.py (기존 노트북 세션 작성본, 16:10 실행)

`setup_check_output_1610.txt`. 정상 31·실패 3·주의 1.
- 실패: 왼팔 `COM15`·오른팔 `COM16` 없음(실제 COM3/COM4), 오른쪽 손목캠 힌트 `1b3f2dc8` 없음. → 이후 bat·힌트 수정.
- 주의: origin/main보다 1개 뒤 → 이후 #86까지 pull.
- 방화벽 항목은 조회가 20 s 시간 초과했는데 `[OK]`로 표시됨(스크립트 문제, 규칙은 직접 확인함). 수정본은 아직 받지 않아 재실행 전이다.

## 3. 팔 점검 (`tools/rollout/arm_health.py`, 읽기만)

| 시점 | 왼팔 COM3 | 오른팔 COM4 |
|---|---|---|
| 16:2x 처음 | 6/6 응답, 11.1~11.2 V | 6/6 무응답 |
| 재확인 | 같음 | 6/6 무응답. 1M/500k/115200 bps × ID 1~20 ping 전부 무응답 |
| 배터리 맞바꾼 뒤 | **6/6 무응답**(원래 오른팔 배터리) | **6/6 응답, 11.2~11.3 V**(원래 왼팔 배터리) |

판정: 무응답이 배터리를 따라감 → 원래 오른팔 배터리 방전(또는 보호 회로 차단). 보드·케이블·모터 정상. 15:56 물따르기 중 `There is no status packet!`과 종료 시 `right_arm 그리퍼 응답 없음(comm=-6)`도 같은 원인으로 본다(`logs/launch-arms_1447_run.txt`).
16:44 실행은 양팔이 연결돼 stow까지 했으므로 그 전에 충전된 배터리로 바꾼 상태였다. 실행 뒤 대기 중 `no status packet` 3회가 있어 실행기를 끈 뒤 전압 재확인이 필요하다.

## 4. 16:52 통합 추론(주행 PC가 주문·align/confirm) — 느림·끊김 원인

`logs/launch-arms_1644_run.txt`.

- 결과: `pour` `ok=false, reason=duration`(run 101.14 s, 100 s 제한). stow는 정상(7.12 s).
- 실행기 추론은 제어 루프 안에서 바로 돈다(`SyncInferenceEngine started (inline mode — no background thread)`). 추론하는 동안 팔이 멈춘다.
- 실행기 측정 `pour_infer_s 2.94`, `place_infer_s 3.38`, 불러오기 176.8 s·169.8 s. 제어 주기 경고 934회, 최소 0.3 Hz·중앙 25.1 Hz(목표 30 Hz).
- 비교 시험(같은 시점·같은 배터리 13%·같은 모델, 일반 창 `python`, 보통 우선순위, 팔 없음): 추론 0.98(첫 회)/0.53/0.47/0.49/0.56 s, 불러오기 130.5 s.
- 판단(확정 아님): 실행기가 예약 작업(우선순위 7=낮음, 창 없는 `pythonw` 백그라운드)으로 떠서 배터리 상태에서 Windows 전력 제한을 받은 것이 1순위다. 불러오기 지연은 배터리 잔량(17%→13%, 충전기 없음) 영향이다(배터리 100%에서는 34~36 s). 충전기 연결 + `start_scenario.bat`을 창으로 띄워 0.5 s 근처가 나오면 확정한다.
- 왼쪽 손목캠(카메라 1)이 16:53·16:55에 끊겨 멈춘 화면으로 28.0 s·22.4 s 돌았다(오른쪽 카메라 2도 잠깐). MSMF `can't grab frame`. 15:56 실행에서도 44.3 s. USB 연결·포트 점검 대상이다. 16:52~16:53에 이 세션이 장치 목록을 읽기 전용으로 조회했지만 15:56·16:55 끊김은 조회와 무관하다.
- 통신(Wi-Fi·주행 PC) 문제는 아니다. 주문·정렬 신호는 정상 수신(`logs/order_server_tail.txt`).

## 5. 예약 작업·원격 접속

- 예약 작업 3개: 트리거 없음, `user` 최고 권한, 우선순위 7, `%TEMP%\amr_launch_omen.py`(`logs/amr_launch_omen.py` 사본)로 옛 클론 `C:\Users\user\bimanual-robot`(#86, autocrlf=true)을 실행. 왼팔 COM3·오른팔 COM4·오른쪽 힌트 `2353db1a`를 스크립트 안에서 덮어쓴다.
- `sshd` 자동 시작(12:04부터). 관리자용 `administrators_authorized_keys` 12:20 수정(키 1개 크기, 관리자 권한 없어 내용 미확인). 사용자용 `authorized_keys` 없음.
- SSH 접속 성공 58회(16시 이전 기준) + 16:44~16:51 추가, 모두 `192.168.0.217`(주행 PC)·ED25519 키 1개. 실패 0.
- 방화벽 22: `OpenSSH-Server-In-TCP`(Private만) + `AMR-SSH-In`(모든 프로필·모든 원격 주소). Wi-Fi 프로필이 Public이라 실제 통로는 `AMR-SSH-In`이다. 출발지를 `.217`로 좁힐지 사용자 결정 대기.
- 주행 세션 기록(PROGRESS.md `OMEN 16 주소로 주행 연동 전환`)에 "사용자 승인으로 OpenSSH와 공개키를 설정"이라고 되어 있다. Pi `--peer`·주행 PC `--order-url`은 이미 `.157`.

## 6. 파일

| 경로 | 내용 |
|---|---|
| `system.txt` | 하드웨어·OS·GPU·전원·네트워크·방화벽·장치·예약 작업·대기 포트(16:52) |
| `status_at_upload.txt` | 업로드 직전 상태(17:16) |
| `setup_check_output_1610.txt` | setup_check.py 출력 |
| `env/` | `pip_freeze.txt`, `conda_list.txt`, `conda_version.txt`, `requirements_compare.txt` |
| `lerobot/` | `lerobot_state.txt`(HEAD·변경 파일), `lerobot_local_diff.patch` |
| `models/` | `model_files.txt`(크기·SHA256·토크나이저 수정), 두 모델 `config.json`·`train_config.json` |
| `cameras/` | 손목캠 왼쪽(1)·오른쪽(2), OBS 가상 카메라 상단(4) 캡처 |
| `logs/` | 실행기 로그 발췌(14:47 실행·16:44 실행), Astra 브리지·주문 서버 로그 끝부분, 예약 작업 실행 스크립트 사본 |
