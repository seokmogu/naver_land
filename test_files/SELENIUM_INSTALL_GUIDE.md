# Selenium 설치 가이드

## Ubuntu/Debian 시스템에서 설치

### 1. 시스템 패키지 설치
```bash
# Python venv 패키지 설치
sudo apt-get update
sudo apt-get install python3.12-venv python3-pip

# Chrome 브라우저 설치 (없는 경우)
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
sudo apt-get update
sudo apt-get install google-chrome-stable
```

### 2. 가상환경 생성 및 패키지 설치
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 패키지 설치
pip install selenium webdriver-manager requests pandas
```

### 3. 실행
```bash
# 가상환경에서 실행
python naver_land_selenium_collector.py
```

## Windows에서 설치

### 1. Python 설치
- https://www.python.org/downloads/ 에서 최신 버전 다운로드
- 설치 시 "Add Python to PATH" 체크

### 2. Chrome 브라우저 설치
- https://www.google.com/chrome/ 에서 다운로드

### 3. 명령 프롬프트에서 패키지 설치
```cmd
pip install selenium webdriver-manager requests pandas
```

### 4. 실행
```cmd
python naver_land_selenium_collector.py
```

## Mac에서 설치

### 1. Homebrew로 Python 설치
```bash
brew install python
```

### 2. Chrome 브라우저 설치
- https://www.google.com/chrome/ 에서 다운로드

### 3. 패키지 설치
```bash
pip3 install selenium webdriver-manager requests pandas
```

### 4. 실행
```bash
python3 naver_land_selenium_collector.py
```

## 문제 해결

### Chrome 드라이버 오류
webdriver-manager가 자동으로 처리하지만, 수동 설치가 필요한 경우:
1. https://chromedriver.chromium.org/ 에서 Chrome 버전에 맞는 드라이버 다운로드
2. 압축 해제 후 PATH에 추가하거나 프로젝트 폴더에 복사

### 권한 오류 (Linux/Mac)
```bash
chmod +x chromedriver
```

### headless 모드 오류
일부 시스템에서는 headless 모드가 작동하지 않을 수 있습니다.
`naver_land_selenium_collector.py`에서 `headless=False`로 변경하세요.