# API Rate Limits Guide

## Rate Limit Overview
AdSparkX enforces rate limits to ensure fair usage and platform stability.

## Limits by Plan

| Plan       | Requests/Day | Requests/Minute | Burst Limit |
|------------|-------------|----------------|-------------|
| Free       | 1,000       | 10             | 20          |
| Pro        | 50,000      | 100            | 200         |
| Enterprise | Custom      | Custom         | Custom      |

## Headers
Rate limit information is included in API response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1623456789
Retry-After: 45
```

## Handling Rate Limits

### 429 Too Many Requests
When you exceed the rate limit, the API returns:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 45 seconds.",
  "retry_after": 45
}
```

### Best Practices
1. **Implement backoff**: Use exponential backoff when receiving 429 responses.
2. **Cache responses**: Cache frequently accessed data to reduce API calls.
3. **Batch requests**: Use batch endpoints where available.
4. **Monitor headers**: Track remaining tokens via response headers.
5. **Queue requests**: Implement a local request queue with rate limiting.

### Example: Exponential Backoff (Python)
```python
import time
import requests

def api_call_with_retry(url, headers, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 2 ** attempt))
            time.sleep(wait)
            continue
        return response
    return response
```

## Requesting a Limit Increase
- Pro users: Contact support (standard 2-3 day review).
- Enterprise users: Limits are configured in your SLA.
- Temporary increases may be granted for special campaigns.
