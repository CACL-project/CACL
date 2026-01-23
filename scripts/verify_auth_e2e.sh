#!/bin/bash
#
# End-to-end authentication verification script for CACL demo app.
# Validates all auth endpoints, token lifecycle, and security behaviors.
#
# Usage: ./scripts/verify_auth_e2e.sh
#
# Prerequisites:
#   - Docker and docker compose installed
#   - Ports 8001 (web) and 5432 (db) available
#
set -e

BASE_URL="http://localhost:8001"
COOKIE_JAR=$(mktemp)
ADMIN_COOKIE_JAR=$(mktemp)
RESP_FILE=$(mktemp)

cleanup() {
    rm -f "$COOKIE_JAR" "$ADMIN_COOKIE_JAR" "$RESP_FILE"
}
trap cleanup EXIT

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
log_pass()  { echo -e "${GREEN}[PASS]${NC} $1"; ((PASSED++)); ((TOTAL++)); }
log_fail()  { echo -e "${RED}[FAIL]${NC} $1"; ((FAILED++)); ((TOTAL++)); }
log_section() { echo -e "\n${YELLOW}=== $1 ===${NC}\n"; }

# Test helper: expects HTTP status code
assert_status() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" = "$expected" ]; then
        log_pass "$name -> HTTP $actual"
    else
        log_fail "$name -> HTTP $actual (expected $expected)"
    fi
}

# ============================================================
# ENVIRONMENT SETUP
# ============================================================
log_section "ENVIRONMENT SETUP"

log_info "Stopping existing containers..."
docker compose down -v 2>/dev/null || true

log_info "Building and starting containers..."
docker compose up -d --build 2>&1 | tail -5

log_info "Waiting for services to be ready..."
sleep 5

log_info "Running database migrations..."
docker compose exec -T web alembic upgrade head 2>&1 | tail -3

# ============================================================
# CREATE TEST USERS
# ============================================================
log_section "CREATE TEST USERS"

log_info "Creating admin user (admin@test.com)..."
docker compose exec -T -e EMAIL=admin@test.com -e PASSWORD=admin123 web \
    python scripts/create_admin.py 2>&1 || true

log_info "Creating regular user (user@test.com)..."
docker compose exec -T -e EMAIL=user@test.com -e PASSWORD=user1234 web \
    python scripts/create_user.py 2>&1 || true

log_info "Verifying users in database..."
USER_COUNT=$(docker compose exec -T db psql -U postgres -d cacl_demo -t -c \
    "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
if [ "$USER_COUNT" -ge 2 ]; then
    log_pass "Users created: $USER_COUNT users in database"
else
    log_fail "User creation failed: only $USER_COUNT users found"
fi

# ============================================================
# SUCCESS FLOWS
# ============================================================
log_section "SUCCESS FLOWS"

# Test: Regular user login
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -c "$COOKIE_JAR" \
    -d '{"email":"user@test.com","password":"user1234"}')
assert_status "Regular user login" "200" "$HTTP_CODE"

# Test: GET /me with valid token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X GET "$BASE_URL/me" -b "$COOKIE_JAR")
assert_status "GET /me with valid token" "200" "$HTTP_CODE"

# Test: Admin login
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/admin/login" \
    -H "Content-Type: application/json" \
    -c "$ADMIN_COOKIE_JAR" \
    -d '{"email":"admin@test.com","password":"admin123"}')
assert_status "Admin login" "200" "$HTTP_CODE"

# Test: GET /admin/users with admin token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X GET "$BASE_URL/admin/users" \
    -b "$ADMIN_COOKIE_JAR")
assert_status "GET /admin/users with admin token" "200" "$HTTP_CODE"

# ============================================================
# FAILURE FLOWS (SECURITY)
# ============================================================
log_section "FAILURE FLOWS (SECURITY)"

# Test: Login with wrong password
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"user@test.com","password":"wrongpass"}')
assert_status "Login with wrong password" "401" "$HTTP_CODE"

# Test: Admin login with non-admin user
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"user@test.com","password":"user1234"}')
assert_status "Admin login with non-admin user" "403" "$HTTP_CODE"

# Test: GET /me without token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X GET "$BASE_URL/me")
assert_status "GET /me without token" "401" "$HTTP_CODE"

# Test: GET /me with invalid token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X GET "$BASE_URL/me" \
    -H "Cookie: access_token=invalid.token.here")
assert_status "GET /me with invalid token" "401" "$HTTP_CODE"

# Test: GET /admin/users with regular user token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X GET "$BASE_URL/admin/users" \
    -b "$COOKIE_JAR")
assert_status "GET /admin/users with regular user" "403" "$HTTP_CODE"

# Test: Refresh without token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/refresh")
assert_status "Refresh without token" "401" "$HTTP_CODE"

# Test: Logout without token
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/logout")
assert_status "Logout without token" "401" "$HTTP_CODE"

# ============================================================
# TOKEN ROTATION & REUSE
# ============================================================
log_section "TOKEN ROTATION & REUSE"

# Fresh login for rotation tests
ROTATION_JAR=$(mktemp)
curl -s -o "$RESP_FILE" -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -c "$ROTATION_JAR" \
    -d '{"email":"user@test.com","password":"user1234"}'

# Save original refresh token
ORIG_REFRESH=$(grep refresh_token "$ROTATION_JAR" 2>/dev/null | awk '{print $NF}')

# Test: Refresh success
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/refresh" \
    -b "$ROTATION_JAR" -c "$ROTATION_JAR")
assert_status "Refresh token rotation" "200" "$HTTP_CODE"

# Test: Refresh reuse with OLD token (must fail)
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/refresh" \
    -H "Cookie: refresh_token=$ORIG_REFRESH")
assert_status "Refresh reuse with old token" "401" "$HTTP_CODE"

rm -f "$ROTATION_JAR"

# ============================================================
# LOGOUT & POST-LOGOUT
# ============================================================
log_section "LOGOUT & POST-LOGOUT"

# Fresh login for logout tests
LOGOUT_JAR=$(mktemp)
curl -s -o "$RESP_FILE" -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -c "$LOGOUT_JAR" \
    -d '{"email":"user@test.com","password":"user1234"}'

# Save tokens before logout
ACCESS_TOKEN=$(grep access_token "$LOGOUT_JAR" 2>/dev/null | awk '{print $NF}')
REFRESH_TOKEN=$(grep refresh_token "$LOGOUT_JAR" 2>/dev/null | awk '{print $NF}')

# Test: Logout success
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/logout" \
    -b "$LOGOUT_JAR")
assert_status "Logout" "200" "$HTTP_CODE"

# Test: GET /me after logout (access token blacklisted)
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X GET "$BASE_URL/me" \
    -H "Cookie: access_token=$ACCESS_TOKEN")
assert_status "GET /me after logout" "401" "$HTTP_CODE"

# Test: Refresh after logout (refresh token blacklisted)
HTTP_CODE=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -X POST "$BASE_URL/auth/refresh" \
    -H "Cookie: refresh_token=$REFRESH_TOKEN")
assert_status "Refresh after logout" "401" "$HTTP_CODE"

rm -f "$LOGOUT_JAR"

# ============================================================
# SUMMARY
# ============================================================
log_section "SUMMARY"

echo -e "Total tests: $TOTAL"
echo -e "Passed:      ${GREEN}$PASSED${NC}"
echo -e "Failed:      ${RED}$FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED${NC}"
    exit 1
fi
