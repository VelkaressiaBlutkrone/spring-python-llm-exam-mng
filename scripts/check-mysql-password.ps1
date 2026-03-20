# app-db 컨테이너 root 비밀번호 확인
# docker-compose로 생성된 경우, infra 프로젝트의 MYSQL_ROOT_PASSWORD 확인
param([string[]]$Passwords = @("", "rootpassword", "password", "root"))

Write-Host "app-db root 비밀번호 확인 중..." -ForegroundColor Cyan
foreach ($pw in $Passwords) {
    $arg = if ($pw) { "-uroot", "-p$pw", "-e", "SELECT 1" } else { "-uroot", "--password=", "-e", "SELECT 1" }
    $null = docker exec app-db mysql @arg 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "성공! root 비밀번호: $(if ($pw) { "'$pw'" } else { '(빈 값)' })" -ForegroundColor Green
        Write-Host ".env에 추가: MYSQL_ROOT_PASSWORD=$(if ($pw) { $pw } else { '""' })"
        exit 0
    }
}
Write-Host "일치하는 비밀번호 없음. infra/docker-compose.yml의 MYSQL_ROOT_PASSWORD 확인" -ForegroundColor Yellow
