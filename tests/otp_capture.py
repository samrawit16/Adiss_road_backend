"""Capture OTP codes sent via the dev console transport so tests can verify flows."""
import logging
import re
from contextlib import contextmanager


@contextmanager
def otp_capture():
    records = []

    class Handler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("otp")
    h = Handler()
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    try:
        yield records
    finally:
        logger.removeHandler(h)


def codes_for(records, email, purpose=None):
    codes = []
    for r in records:
        msg = r.getMessage()
        if email in msg:
            m = re.search(r"code is: (\d{6})", msg)
            if m:
                codes.append(m.group(1))
    return codes
