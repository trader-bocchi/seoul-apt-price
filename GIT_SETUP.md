# Git 연동 설정 가이드

이 문서는 현재 프로젝트를 Git 저장소에 업로드하는 **실제 단계별 가이드**입니다.

## 현재 상태 확인

프로젝트 디렉토리에서 다음 명령어로 현재 상태를 확인하세요:

```powershell
# 프로젝트 디렉토리로 이동 (이미 있다면 생략)
cd C:\Users\niceg\job\proj\seoul-apt-price

# Git 저장소 초기화 여부 확인
git status
```

## 단계별 설정 가이드

### 1단계: Git 저장소 초기화 (아직 안 했다면)

프로젝트 루트 디렉토리에서 실행:

```powershell
cd C:\Users\niceg\job\proj\seoul-apt-price
git init
```

### 2단계: .gitignore 확인

`.gitignore` 파일이 이미 존재하며 다음 항목들이 포함되어 있습니다:
- ✅ `venv/` (가상환경)
- ✅ `__pycache__/` (Python 캐시)
- ✅ `.env` (환경 변수 - **중요!**)
- ✅ `data/raw/` (수집된 원시 데이터)
- ✅ `data/telegram_logs/` (텔레그램 로그)

**⚠️ 중요**: `.env` 파일은 절대 Git에 커밋하지 마세요! 개인 정보(텔레그램 토큰 등)가 포함되어 있습니다.

### 3단계: GitHub/GitLab 저장소 생성

#### GitHub 사용 시:
1. https://github.com 에 로그인
2. 우측 상단 "+" 버튼 클릭 → "New repository" 선택
3. Repository name 입력 (예: `seoul-apt-price`)
4. Public 또는 Private 선택
5. **"Initialize this repository with a README" 체크하지 않기** (이미 파일이 있으므로)
6. "Create repository" 클릭
7. 생성된 저장소의 URL 복사 (예: `https://github.com/yourusername/seoul-apt-price.git`)

#### GitLab 사용 시:
1. https://gitlab.com 에 로그인
2. "New project" → "Create blank project" 선택
3. Project name 입력
4. Visibility 선택
5. "Initialize repository with a README" 체크하지 않기
6. "Create project" 클릭
7. 저장소 URL 복사

### 4단계: 원격 저장소 연결

```powershell
# 원격 저장소 추가 (위에서 복사한 URL 사용)
git remote add origin https://github.com/yourusername/seoul-apt-price.git

# 또는 GitLab인 경우:
# git remote add origin https://gitlab.com/yourusername/seoul-apt-price.git

# 연결 확인
git remote -v
```

### 5단계: 파일 추가 및 첫 커밋

```powershell
# 현재 상태 확인
git status

# 모든 파일 추가 (.gitignore에 있는 파일은 자동으로 제외됨)
git add .

# 추가될 파일 확인 (선택사항)
git status

# 첫 커밋
git commit -m "Initial commit"

# 커밋 확인
git log
```

### 6단계: 원격 저장소에 푸시

```powershell
# 기본 브랜치 이름 확인 (보통 master 또는 main)
git branch

# 원격 저장소에 푸시
# master 브랜치인 경우:
git push -u origin master

# main 브랜치인 경우:
git push -u origin main

# 브랜치 이름이 다르면 다음으로 확인 후 푸시:
git branch --show-current
```

**참고**: `-u` 옵션은 "upstream"을 설정하여 이후 `git push`만으로도 푸시할 수 있게 합니다.

### 7단계: 푸시 확인

웹 브라우저에서 GitHub/GitLab 저장소 페이지를 열어 파일들이 업로드되었는지 확인하세요.

## 이후 작업 흐름

### 변경사항 커밋 및 푸시

```powershell
# 변경된 파일 확인
git status

# 특정 파일만 추가
git add <파일명>

# 또는 모든 변경사항 추가
git add .

# 커밋
git commit -m "커밋 메시지 (변경 내용 요약)"

# 원격 저장소에 푸시
git push
```

### 예시 커밋 메시지

```powershell
git commit -m "feat: 지역별 수집 기능 추가"
git commit -m "fix: 텔레그램 리포트 오류 수정"
git commit -m "docs: README 업데이트"
git commit -m "refactor: 코드 구조 개선"
```

## 문제 해결

### 이미 원격 저장소가 설정되어 있는 경우

```powershell
# 기존 원격 저장소 확인
git remote -v

# 기존 원격 저장소 제거 (필요한 경우)
git remote remove origin

# 새 원격 저장소 추가
git remote add origin <새_저장소_URL>
```

### 브랜치 이름이 다른 경우

```powershell
# 현재 브랜치 확인
git branch

# 브랜치 이름 변경 (master → main)
git branch -M main

# 또는 main → master
git branch -M master
```

### .env 파일이 실수로 추가된 경우

```powershell
# .env 파일을 Git에서 제거 (로컬 파일은 유지)
git rm --cached .env

# .gitignore 확인 후 커밋
git add .gitignore
git commit -m "Remove .env from tracking"
git push
```

### 푸시 권한 오류가 발생하는 경우

1. GitHub/GitLab에 로그인되어 있는지 확인
2. Personal Access Token 사용 (GitHub의 경우 Settings → Developer settings → Personal access tokens)
3. 또는 SSH 키 설정 (고급)

## 주의사항

⚠️ **절대 커밋하면 안 되는 파일들:**
- `.env` (환경 변수, 개인 정보)
- `venv/` (가상환경 - 용량이 크고 불필요)
- `data/raw/` (수집된 데이터 - 용량이 클 수 있음)
- `__pycache__/` (Python 캐시)

✅ **커밋해야 하는 파일들:**
- 소스 코드 (`src/`, `scripts/`)
- 설정 파일 (`requirements.txt`, `.gitignore`)
- 문서 (`README.md`, `PRD.md`, `ApiRef.md`)
- 참조 데이터 (`data/ref/` - 작은 크기의 참조 파일)

## 완료 확인

모든 단계를 완료했다면:

1. ✅ GitHub/GitLab에서 프로젝트 파일들이 보이는지 확인
2. ✅ `.env` 파일이 업로드되지 않았는지 확인
3. ✅ `venv/` 폴더가 업로드되지 않았는지 확인
4. ✅ `README.md`가 제대로 표시되는지 확인

이제 프로젝트가 Git에 성공적으로 업로드되었습니다! 🎉
