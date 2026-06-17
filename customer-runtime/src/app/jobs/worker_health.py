"""Worker health signal via Redis heartbeat key (AC-008).

The arq worker sets this key with a TTL on each iteration.
The /health endpoint checks for its presence to determine worker liveness.
"""

from __future__ import annotations

# Redis key used as heartbeat signal (TTL-based liveness probe)
# @MX:NOTE: [AUTO] Key format is intentionally simple — matched by GET in health endpoint.
HEARTBEAT_KEY = "arq:worker:heartbeat"

# TTL in seconds: worker refreshes every ~30s; 90s allows 3 missed beats before alert
HEARTBEAT_TTL_SECONDS = 90
