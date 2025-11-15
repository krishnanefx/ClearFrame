"""
Python sitecustomize hook to silence noisy third-party warnings during CLI usage.
This file is automatically imported by the interpreter when present on sys.path.
"""

import warnings

# Match on the warning message so we do not need to import urllib3 (which would
# immediately emit the same warning that we are trying to hide).
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
)
