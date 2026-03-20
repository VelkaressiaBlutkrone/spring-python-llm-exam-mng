# MySQL 초기 설정 실행 (PowerShell)
# llm_user 생성 및 llm_db 권한 부여
# root 비밀번호: param -RootPassword, .env MYSQL_ROOT_PASSWORD, 또는 기본값 "password"
#
# 비밀번호 확인: docker exec -it app-db mysql -uroot -p  (대화형으로 입력)
# app-db는 docker-compose/infra에서 MYSQL_ROOT_PASSWORD로 설정됨
param([string]$RootPassword)

if (-not $RootPassword) {
    $envPath = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
    if (Test-Path $envPath) {
        Get-Content $envPath -Encoding UTF8 | ForEach-Object {
            $line = $_ -replace '#.*$', ''  # 주석 제거
            if ($line -match '^\s*MYSQL_ROOT_PASSWORD\s*=\s*(.+)$') {
                $RootPassword = $matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
}
$rootPassword = if ($RootPassword) { $RootPassword } elseif ($env:MYSQL_ROOT_PASSWORD) { $env:MYSQL_ROOT_PASSWORD } else { "rootpassword" }

Write-Host "app-db 컨테이너에 init-mysql.sql 실행 중... (root 비밀번호: .env 또는 -RootPassword 확인)" -ForegroundColor Cyan
$sqlPath = Join-Path $PSScriptRoot "init-mysql.sql"
docker cp $sqlPath app-db:/tmp/init-mysql.sql
# 비밀번호를 작은따옴표로 감싸 sh에서 특수문자(!,$ 등) 해석 방지
$pwEscaped = $rootPassword -replace "'", "'\`''"
docker exec app-db sh -c "mysql -uroot --password='$pwEscaped' < /tmp/init-mysql.sql"
