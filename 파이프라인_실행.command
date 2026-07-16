#!/bin/bash
# 서울/수도권 아파트 호가 리포트 파이프라인 실행기 (macOS)
# Finder에서 이 파일을 더블클릭하면 파이프라인이 실행됩니다.
# (최초 1회: 우클릭 → 열기 로 Gatekeeper 허용, 또는 chmod +x 필요)

# 이 스크립트가 위치한 디렉터리로 이동 (프로젝트 루트)
cd "$(dirname "$0")" || exit 1

echo "=================================================="
echo " 아파트 호가 리포트 파이프라인 실행"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================="

# venv 확인
if [ ! -x "venv/bin/python" ]; then
  echo "[오류] venv를 찾을 수 없습니다. 먼저 아래를 실행하세요:"
  echo "  python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  echo ""
  echo "종료하려면 Enter 키를 누르세요."
  read -r
  exit 1
fi

# 파이프라인 실행
./venv/bin/python scripts/run_pipeline.py
STATUS=$?

echo ""
echo "=================================================="
if [ $STATUS -eq 0 ]; then
  echo " ✅ 완료 (텔레그램 리포트 전송됨)"
else
  echo " ❌ 실패 (종료 코드: $STATUS) — 위 로그를 확인하세요."
fi
echo "=================================================="
echo "이 창을 닫으려면 Enter 키를 누르세요."
read -r
