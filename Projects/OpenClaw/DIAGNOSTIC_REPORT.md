# OpenClaw Diagnostic Report
**Date:** 2026-02-15
**Server:** 195.177.94.189
**Status:** ✅ OPERATIONAL (with issues)

---

## 🎯 Executive Summary

OpenClaw is **running and stable** but experiencing **performance and reliability issues**:

### Critical Findings
1. **Network Connectivity Issues** - Intermittent fetch failures affecting API calls
2. **Context Management Problems** - Token overflow events (203K tokens requested)
3. **Python PATH Issues** - Python binary not found for some operations
4. **Embedded Run Timeouts** - Multiple 10-minute timeout occurrences
5. **Code Quality Issues** - Legacy scripts lack proper error handling and logging

### Health Status
- ✅ Service: Active (4+ days uptime)
- ✅ Telegram Bot: Responding
- ⚠️  Performance: Degraded (network issues, timeouts)
- ⚠️  Reliability: Moderate (context overflows, Python errors)

---

## 📊 Server Status (VPS)

### System Information
- **OS:** Ubuntu 22.04 LTS
- **Kernel:** 5.15.0-84-generic
- **Node.js:** v22.22.0
- **OpenClaw:** 2026.2.9
- **Uptime:** 4+ days (since Feb 10, 07:22 UTC)

### Resource Usage
| Resource | Usage | Available | Status |
|----------|-------|-----------|--------|
| Memory | 1.4 GB | 5.8 GB (24%) | ✅ Healthy |
| Disk | 18 GB | 39 GB (45%) | ✅ Healthy |
| OpenClaw | 1.0 GB | - | ✅ Normal |
| CPU | 1h 5min | - | ✅ Low |

### Process Status
```
PID 668073 - openclaw (launcher)
PID 668080 - openclaw-gateway (525 MB RAM)
PID 670096 - voice_processor.py (voice assistant)
```

---

## 🔴 Critical Issues

### 1. Network Connectivity Failures
**Severity:** HIGH
**Frequency:** Recurring (Feb 10-14)

**Symptoms:**
```
TypeError: fetch failed
sendChatAction failed: Error: connect ETIMEDOUT
```

**Impact:**
- Telegram message sending fails intermittently
- API calls timeout
- User experience degraded

**Root Cause:**
- Network instability between VPS and external APIs
- Possible firewall/routing issues

**Recommendations:**
1. Add retry logic with exponential backoff
2. Implement network health monitoring
3. Check VPS provider network status
4. Consider adding circuit breaker pattern
5. Monitor DNS resolution issues

---

### 2. Context Token Overflow
**Severity:** HIGH
**Occurrence:** Feb 10, 23:13 UTC

**Details:**
```
Token limit exceeded: 203,984 requested vs 202,752 max
Auto-compaction attempted but failed (rate limit)
Session restarted
```

**Current Mitigation:**
```json
"compaction": {
  "mode": "safeguard",
  "reserveTokensFloor": 4000
}
```

**Recommendations:**
1. ✅ DONE: reserveTokensFloor increased to 4000
2. Monitor token usage per conversation
3. Implement aggressive context pruning
4. Consider shorter TTL (currently 1h):
   ```json
   "contextPruning": {
     "mode": "cache-ttl",
     "ttl": "30m"  // Reduce from 1h
   }
   ```
5. Add conversation reset after N messages
6. Implement context summarization

---

### 3. Python PATH Issues
**Severity:** MEDIUM
**Occurrence:** Feb 11, 13:xx UTC

**Error:**
```
python: not found
ValueError: too many values to unpack (expected 2)
```

**Root Cause:**
- `python` binary not in PATH
- Scripts expect `python` but system has `python3`

**Fix:**
```bash
# On VPS:
sudo ln -s /usr/bin/python3 /usr/bin/python

# Or update scripts to use python3 explicitly
```

**Recommendations:**
1. Create python → python3 symlink
2. Update all scripts to use `#!/usr/bin/env python3`
3. Add PATH check in systemd service:
   ```ini
   Environment="PATH=/usr/bin:/usr/local/bin"
   ```

---

### 4. Embedded Run Timeouts
**Severity:** MEDIUM
**Occurrences:** Feb 11 (04:56), Feb 13 (09:39)

**Details:**
```
Embedded run timed out after 600,000ms (10 minutes)
```

**Impact:**
- Long-running tasks fail
- User requests timeout
- No response returned

**Recommendations:**
1. Reduce timeout to 5 minutes for user-facing tasks:
   ```json
   "agents": {
     "defaults": {
       "timeout": 300000  // 5 minutes
     }
   }
   ```
2. Implement progress callbacks for long tasks
3. Split long operations into smaller chunks
4. Add task cancellation support
5. Monitor which operations timeout most frequently

---

## ⚠️  Configuration Issues

### Current Model Configuration
```json
"model": {
  "primary": "zai/glm-4.7-flash"
}
```

**Issue:** GLM-4.7-flash может быть причиной "слабой" работы

**Analysis:**
- GLM-4.7-flash - это быстрая, но менее мощная модель
- Подходит для простых задач, но не для сложного reasoning
- May explain "weak" performance user is experiencing

**Recommendations:**
1. **For Better Quality:** Switch to full GLM-4.7 (not flash):
   ```json
   "primary": "zai/glm-4.7"
   ```

2. **For Best Quality:** Use Anthropic Claude (if budget allows):
   ```json
   "primary": "anthropic/claude-3-5-sonnet-20241022"
   ```
   Don't forget to set `ANTHROPIC_API_KEY` in `/root/.openclaw/.env`

3. **Hybrid Approach:**
   ```json
   "primary": "zai/glm-4.7",           // Default
   "fallback": "zai/glm-4.7-flash",    // For simple tasks
   "reasoning": "anthropic/claude-3-5-sonnet"  // Complex tasks
   ```

### Gateway Authentication
```json
"gateway": {
  "mode": "local",
  "auth": {
    "mode": "token",
    "token": "c7d90013e2b8187cd124b4bcef6a9394"
  }
}
```

**Security Note:** Token is static and potentially exposed in logs.

**Recommendation:** Rotate token periodically or use stronger auth.

---

## 💻 Code Quality Issues

### Summary from Code Review
**Overall Score:** 6.6/10

### Critical Code Issues

#### 1. No Logging Infrastructure
**Impact:** HIGH

**Problem:**
- All scripts use `print()` instead of `logging` module
- No persistent logs
- No log levels (debug, info, error)
- Difficult to troubleshoot in production

**Fix Example:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openclaw_manager.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Connected to VPS")  # Instead of print()
```

#### 2. Bare Exception Handling
**Impact:** MEDIUM

**Problem:**
```python
# CURRENT (BAD)
except Exception as e:
    print("SSH failed:", e)
```

**Fix:**
```python
# BETTER
except (paramiko.AuthenticationException, paramiko.SSHException) as e:
    logger.error(f"SSH connection failed: {e}")
    raise
```

#### 3. Missing Type Hints
**Impact:** LOW (code quality)

**Problem:** Only `vps_connect.py` has type hints

**Fix:** Add to all functions:
```python
def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Execute command on VPS"""
    ...
```

#### 4. Code Duplication
**Impact:** MEDIUM (maintainability)

**Problem:** `run()` function duplicated in 4 files

**Fix:** Extract to common module:
```python
# common/ssh_utils.py
def run_ssh_command(
    ssh: paramiko.SSHClient,
    cmd: str,
    timeout: int = 30
) -> Tuple[int, str, str]:
    """Execute SSH command and return (code, stdout, stderr)"""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return exit_code, out, err
```

---

## 🔍 Installation Discovery

### Important Finding: Installation Location Changed
**Previous assumption:** `/opt/openclaw`
**Actual location:** `/usr/lib/node_modules/openclaw` (npm global)

**Files Updated:** ✅ COMPLETED
- ✅ README.md - Updated to show correct paths
- ✅ INSTALL.md - Fixed .env and service file paths
- ✅ TROUBLESHOOTING.md - Updated all path references
- ✅ CLAUDE.md - Updated VPS environment section
- ✅ vps_connect.py - Fixed installation check
- ✅ scripts/config/set_env.py - Now uses /root/.openclaw/.env
- ✅ scripts/config/set_glm.py - Now uses /root/.openclaw/.env
- ✅ scripts/setup/install_step2.py - Updated installation commands

**Actual Locations:**
```
Binary:      /usr/bin/openclaw
Module:      /usr/lib/node_modules/openclaw
Config:      /root/.openclaw/openclaw.json
Env:         /root/.openclaw/.env
Service:     /etc/systemd/system/openclaw.service
```

**Action Completed:** ✅
1. ✅ Updated all documentation
2. ✅ Updated scripts to use correct paths
3. ✅ Removed references to `/opt/openclaw`

---

## 📋 Action Plan

### Immediate (Fix Today)

1. **Fix Model Configuration** (Performance Issue)
   ```bash
   # SSH into server
   ssh root@195.177.94.189

   # Edit config
   nano /root/.openclaw/openclaw.json

   # Change:
   "primary": "zai/glm-4.7"  # Remove "-flash"

   # Restart
   systemctl restart openclaw
   ```

2. **Fix Python PATH**
   ```bash
   sudo ln -s /usr/bin/python3 /usr/bin/python
   ```

3. ✅ **Update Documentation** (Fix wrong paths) - COMPLETED
   - ✅ Updated README.md: `/opt/openclaw` → `/root/.openclaw`
   - ✅ Updated INSTALL.md: correct paths
   - ✅ Updated script comments and paths
   - ✅ Updated vps_connect.py installation check
   - ✅ Updated TROUBLESHOOTING.md
   - ✅ Updated CLAUDE.md

### This Week

4. **Add Retry Logic for Network**
   - Implement exponential backoff in API calls
   - Add circuit breaker for failing endpoints

5. **Reduce Context Pruning TTL**
   ```json
   "contextPruning": {
     "ttl": "30m"  // Was: "1h"
   }
   ```

6. **Add Logging to Scripts**
   - Implement logging module in vps_connect.py
   - Add log rotation

7. **Reduce Embedded Run Timeout**
   ```json
   "agents": {
     "defaults": {
       "timeout": 300000  // 5 min instead of 10
     }
   }
   ```

### This Month

8. **Refactor Code**
   - Extract common SSH utilities
   - Add type hints to all functions
   - Fix bare exception handling
   - Add proper docstrings

9. **Add Monitoring**
   - Implement health check endpoint
   - Add metrics collection
   - Set up alerting for failures

10. **Improve Documentation**
    - Add troubleshooting examples
    - Document all env variables
    - Add performance tuning guide

---

## 🎯 Expected Improvements

After implementing the action plan:

### Performance
- ✅ Faster responses (better model)
- ✅ Fewer timeouts (reduced timeout settings)
- ✅ Better context management (shorter TTL)

### Reliability
- ✅ Network resilience (retry logic)
- ✅ Fewer crashes (better error handling)
- ✅ Easier debugging (proper logging)

### User Experience
- ✅ More intelligent responses (better model)
- ✅ Fewer "I don't know" responses
- ✅ More consistent behavior

---

## 📞 Support

If issues persist after fixes:

1. Check logs:
   ```bash
   python vps_connect.py logs 200
   ```

2. Monitor in real-time:
   ```bash
   python scripts/monitoring/watch.py
   ```

3. Full diagnostic:
   ```bash
   python vps_connect.py status
   python vps_connect.py shell "systemctl status openclaw"
   ```

4. Restart if needed:
   ```bash
   python vps_connect.py restart
   ```

---

## 📝 Conclusion

OpenClaw is **functional but underperforming** due to:
1. Wrong model (GLM-4.7-flash instead of full GLM-4.7 or Claude)
2. Network issues causing intermittent failures
3. Context management problems from token overflow
4. Code quality issues in management scripts

**Priority Fix:** Change model from `zai/glm-4.7-flash` to `zai/glm-4.7` or `anthropic/claude-3-5-sonnet` for immediate quality improvement.

All other issues are addressable through the action plan above.
