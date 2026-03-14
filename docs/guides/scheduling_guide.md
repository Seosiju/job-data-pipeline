# 스케줄링 설정 가이드

> 매일 오전 9시 자동 크롤링 설정 방법

---

## macOS (launchd)

### 1. plist 파일 생성

```bash
nano ~/Library/LaunchAgents/com.jobkorea.crawler.plist
```

### 2. 내용 작성

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jobkorea.crawler</string>

    <key>ProgramArguments</key>
    <array>
        <string>/path/to/jobkorea/scripts/run_crawler.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/path/to/jobkorea/log/launchd.log</string>

    <key>StandardErrorPath</key>
    <string>/path/to/jobkorea/log/launchd_error.log</string>

    <key>WorkingDirectory</key>
    <string>/path/to/jobkorea</string>
</dict>
</plist>
```

> `/path/to/jobkorea`를 실제 경로로 변경하세요.

### 3. 등록 및 시작

```bash
# 등록
launchctl load ~/Library/LaunchAgents/com.jobkorea.crawler.plist

# 즉시 테스트 실행
launchctl start com.jobkorea.crawler

# 상태 확인
launchctl list | grep jobkorea

# 해제 (필요 시)
launchctl unload ~/Library/LaunchAgents/com.jobkorea.crawler.plist
```

---

## Linux (cron)

### 1. crontab 편집

```bash
crontab -e
```

### 2. 스케줄 추가

```bash
# 매일 오전 9시 실행
0 9 * * * /path/to/jobkorea/scripts/run_crawler.sh >> /path/to/jobkorea/log/cron.log 2>&1
```

### 3. 확인

```bash
crontab -l
```

---

## Linux (systemd)

### 1. 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/jobkorea-crawler.service
```

```ini
[Unit]
Description=JobKorea Crawler Service
After=network.target postgresql.service

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/jobkorea
ExecStart=/path/to/jobkorea/scripts/run_crawler.sh
StandardOutput=append:/path/to/jobkorea/log/systemd.log
StandardError=append:/path/to/jobkorea/log/systemd_error.log

[Install]
WantedBy=multi-user.target
```

### 2. 타이머 파일 생성

```bash
sudo nano /etc/systemd/system/jobkorea-crawler.timer
```

```ini
[Unit]
Description=Run JobKorea Crawler daily at 9 AM

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. 활성화

```bash
# 서비스 리로드
sudo systemctl daemon-reload

# 타이머 활성화
sudo systemctl enable jobkorea-crawler.timer
sudo systemctl start jobkorea-crawler.timer

# 상태 확인
sudo systemctl status jobkorea-crawler.timer
sudo systemctl list-timers --all | grep jobkorea

# 수동 실행 테스트
sudo systemctl start jobkorea-crawler.service
```

---

## Windows (Task Scheduler)

### 1. 작업 스케줄러 열기

- Win + R → `taskschd.msc` 입력

### 2. 기본 작업 만들기

1. **이름**: JobKorea Crawler
2. **트리거**: 매일 오전 9:00
3. **동작**: 프로그램 시작
   - 프로그램: `python`
   - 인수: `main.py`
   - 시작 위치: `C:\path\to\jobkorea`

### PowerShell 스크립트 방식

```powershell
# run_crawler.ps1
Set-Location "C:\path\to\jobkorea"
python main.py 2>&1 | Tee-Object -FilePath "log\crawler_$(Get-Date -Format 'yyyyMMdd').log"
```

---

## 실행 확인

### 로그 확인

```bash
# 최근 로그 확인
tail -f log/crawler.log

# 에러 로그 확인
tail -f log/error.log

# 특정 날짜 로그 검색
grep "2026-03-10" log/crawler.log
```

### 크롤링 실행 기록 확인 (DB)

```sql
SELECT * FROM crawl_runs ORDER BY started_at DESC LIMIT 10;
```

---

## 문제 해결

### 1. 스크립트가 실행되지 않음

```bash
# 실행 권한 확인
ls -la scripts/run_crawler.sh

# 권한 부여
chmod +x scripts/run_crawler.sh
```

### 2. Python을 찾지 못함

```bash
# Python 경로 확인
which python

# scripts/run_crawler.sh에서 절대 경로 사용
/usr/bin/python3 main.py
```

### 3. 환경변수가 로드되지 않음

```bash
# .env 파일 확인
cat .env

# 스크립트에서 직접 로드 확인
source .env && python main.py
```

### 4. DB 연결 실패

```bash
# PostgreSQL 상태 확인
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Linux
```

---

*최종 업데이트: 2026-03-10*
