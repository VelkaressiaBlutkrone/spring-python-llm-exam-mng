# vLLM + Qwen2.5-7B WSL2 설치 및 운영 가이드

> 작성일: 2025-03-18  
> 환경: Windows 11 + WSL2 Ubuntu + NVIDIA GPU (8GB VRAM)

---

## 목차

1. [환경 요구사항](#1-환경-요구사항)
2. [WSL2 기본 설정](#2-wsl2-기본-설정)
3. [pyenv + Python 설치](#3-pyenv--python-설치)
4. [가상환경 생성 및 vLLM 설치](#4-가상환경-생성-및-vllm-설치)
5. [vLLM 서버 실행](#5-vllm-서버-실행)
6. [외부 PC 접속 설정](#6-외부-pc-접속-설정)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 환경 요구사항

| 항목 | 최소 사양 | 권장 사양 |
|------|----------|----------|
| GPU VRAM | 8GB (AWQ 양자화) | 16GB+ |
| Python | 3.9 ~ 3.12 | 3.11.x |
| CUDA | 12.1+ | 12.4+ |
| RAM | 16GB | 32GB+ |
| OS | Windows 10 + WSL2 | Windows 11 + WSL2 |

---

## 2. WSL2 기본 설정

### 시스템 업데이트 및 빌드 의존성 설치

> ⚠️ **pyenv로 Python 빌드 전에 반드시 먼저 실행**

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  build-essential curl wget git \
  libbz2-dev libffi-dev liblzma-dev \
  libncursesw5-dev libreadline-dev \
  libsqlite3-dev libssl-dev \
  libxml2-dev libxmlsec1-dev \
  tk-dev xz-utils zlib1g-dev
```

> `liblzma-dev` 누락 시 이후 `ModuleNotFoundError: No module named '_lzma'` 에러 발생

---

## 3. pyenv + Python 설치

### pyenv 설치

```bash
curl https://pyenv.run | bash
```

### 환경변수 등록

```bash
echo '' >> ~/.bashrc
echo '# pyenv 설정' >> ~/.bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

source ~/.bashrc
```

### Python 3.11.9 설치

```bash
pyenv install 3.11.9
pyenv global 3.11.9

# 확인
python --version   # Python 3.11.9
pip --version      # pip 24.x.x
```

---

## 4. 가상환경 생성 및 vLLM 설치

### 가상환경 생성

```bash
pip install --upgrade pip

mkdir -p ~/vllm-server && cd ~/vllm-server
python -m venv .venv
source .venv/bin/activate
```

### GPU(CUDA) 확인

```bash
nvidia-smi
```

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 545.xx    Driver Version: 545.xx    CUDA Version: 12.x          |
+-----------------------------------------------------------------------------+
| GPU  Name        | ... | Memory-Usage                                       |
|   0  RTX xxxx    | ... |   500MiB / 8192MiB                                |
+-----------------------------------------------------------------------------+
```

> ❗ `nvidia-smi` 없으면 Windows에 [NVIDIA 드라이버](https://www.nvidia.com/Download/index.aspx) 먼저 설치

### vLLM 설치

```bash
pip install vllm

# 확인
python -c "import vllm; print(vllm.__version__)"
```

---

## 5. vLLM 서버 실행

### GPU VRAM 별 권장 실행 명령어

| VRAM | 모델 | 설정 | 안정성 |
|------|------|------|--------|
| 24GB+ | Qwen2.5-7B-Instruct | bfloat16, max-len 8192 | ✅ 안정 |
| 16GB | Qwen2.5-7B-Instruct | bfloat16, max-len 4096 | ✅ 안정 |
| 10~12GB | Qwen2.5-7B-Instruct | bfloat16, util 0.80 | ⚠️ 주의 |
| 8GB | **Qwen2.5-7B-Instruct-AWQ** | awq, dtype auto | ✅ 권장 |

---

### 기본 실행 (16GB+)

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen2.5-7b \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9 \
  --dtype bfloat16 \
  --trust-remote-code
```

---

### 8GB GPU 권장 실행 (AWQ 양자화)

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct-AWQ \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen2.5-7b \
  --quantization awq \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --dtype auto \
  --trust-remote-code
```

### 주요 파라미터 설명

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `--tensor-parallel-size` | 멀티 GPU 병렬 수 | 1 |
| `--gpu-memory-utilization` | GPU 메모리 사용률 (0~1) | 0.9 |
| `--max-model-len` | 최대 컨텍스트 길이 | 모델 기본값 |
| `--dtype` | 데이터 타입 (bfloat16/float16/auto) | auto |
| `--quantization` | 양자화 방식 (awq/gptq) | 없음 |
| `--trust-remote-code` | 커스텀 모델 코드 허용 | false |

### 정상 구동 로그

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### API 테스트

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b",
    "messages": [
      {"role": "user", "content": "안녕! 간단히 자기소개 해줘"}
    ],
    "max_tokens": 256
  }'
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"
)

response = client.chat.completions.create(
    model="qwen2.5-7b",
    messages=[
        {"role": "system", "content": "당신은 친절한 AI 어시스턴트입니다."},
        {"role": "user", "content": "파이썬으로 피보나치 수열 구현해줘"}
    ],
    temperature=0.7,
    max_tokens=1024
)
print(response.choices[0].message.content)
```

---

## 6. 외부 PC 접속 설정

### 전체 구조

```
다른 PC (클라이언트)
    │  192.168.1.100:8000
    ▼
Windows 호스트 (포트 포워딩)
    │  172.28.x.x:8000
    ▼
WSL2 Ubuntu (vLLM 서버)
    │
    └── Qwen2.5-7B
```

### Step 1. IP 확인

```bash
# WSL2에서 Windows 호스트 IP 확인
cat /etc/resolv.conf | grep nameserver
```

```powershell
# Windows PowerShell에서 확인
ipconfig
# IPv4 Address: 192.168.x.x  ← 외부에서 이 IP 사용
```

### Step 2. 포트 포워딩 설정 (PowerShell 관리자)

```powershell
# WSL2 IP 확인
wsl hostname -I
# 예: 172.28.144.100

# 포트 포워딩 등록
netsh interface portproxy add v4tov4 `
  listenport=8000 `
  listenaddress=0.0.0.0 `
  connectport=8000 `
  connectaddress=172.28.144.100

# 등록 확인
netsh interface portproxy show all
```

### Step 3. 방화벽 포트 허용 (PowerShell 관리자)

```powershell
New-NetFirewallRule `
  -DisplayName "vLLM Server 8000" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow
```

### Step 4. 다른 PC에서 접속 테스트

```bash
# 포트 열림 확인
nc -zv 192.168.1.100 8000

# 모델 목록 확인
curl http://192.168.1.100:8000/v1/models
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.1.100:8000/v1",  # 서버 IP로 변경
    api_key="dummy"
)
```

### 포트 포워딩 정리 (서버 종료 시)

```powershell
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
Remove-NetFirewallRule -DisplayName "vLLM Server 8000"
```

> ⚠️ **WSL2 재시작 시 IP가 변경됩니다.** 재시작 후 `wsl hostname -I` 로 IP 확인 후 포트 포워딩 재등록 필요

---

## 7. 트러블슈팅

### ❌ ModuleNotFoundError: No module named '_lzma'

**원인**: `liblzma-dev` 없이 Python 빌드됨

```bash
# 1. 라이브러리 설치
sudo apt install -y liblzma-dev

# 2. Python 재설치
deactivate
pyenv uninstall 3.11.9
pyenv install 3.11.9

# 3. 가상환경 재생성
rm -rf ~/vllm-server/.venv
cd ~/vllm-server
python -m venv .venv
source .venv/bin/activate
pip install vllm
```

---

### ❌ ValueError: Free memory on device cuda:0 is less than desired GPU memory utilization

**원인**: VRAM 부족 (8GB GPU에서 0.9 설정 시 7.2GB 요구)

**해결 방법 1 - utilization 낮추기**

```bash
--gpu-memory-utilization 0.80 \
--max-model-len 4096
```

**해결 방법 2 - AWQ 양자화 모델 사용 (권장)**

```bash
--model Qwen/Qwen2.5-7B-Instruct-AWQ \
--quantization awq \
--dtype auto
```

**해결 방법 3 - 다른 GPU 프로세스 종료**

```bash
# GPU 점유 프로세스 확인
nvidia-smi

# 프로세스 종료
sudo kill -9 <PID>

# 또는 WSL 전체 재시작 (Windows PowerShell)
wsl --shutdown && wsl
```

---

### 에러 요약표

| 에러 | 원인 | 해결 |
|------|------|------|
| `No module named '_lzma'` | liblzma-dev 미설치 후 Python 빌드 | apt install liblzma-dev 후 Python 재설치 |
| `CUDA OOM / Free memory less than utilization` | VRAM 부족 | AWQ 모델 사용 또는 utilization 낮추기 |
| `CUDA not found` | NVIDIA 드라이버 미설치 | Windows에 NVIDIA 드라이버 설치 |
| `trust-remote-code 오류` | Qwen 커스텀 코드 미허용 | `--trust-remote-code` 옵션 추가 |
| `Connection refused` (외부 접속) | 포트 포워딩 미설정 | netsh portproxy 설정 + 방화벽 허용 |

---

## 참고 링크

- [vLLM 공식 문서](https://docs.vllm.ai)
- [Qwen2.5 HuggingFace](https://huggingface.co/Qwen)
- [NVIDIA CUDA WSL2 가이드](https://docs.nvidia.com/cuda/wsl-user-guide/)
- [pyenv GitHub](https://github.com/pyenv/pyenv)
