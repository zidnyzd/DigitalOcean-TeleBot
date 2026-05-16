"""Helpers for interpreting DigitalOcean billing/balance responses.

DigitalOcean does not expose promotional credits (GitHub Student, referral,
Hacktoberfest, etc.) via the public API. We can only tell that a credit is
*likely* active by combining the balance endpoint with the droplet count:
when the account has running droplets but both the prior balance and the
month-to-date usage are zero, billing is being absorbed by a hidden credit.
"""

from typing import Optional

import digitalocean


def parse_amount(value) -> float:
    """Balance fields come back as strings. Convert to float defensively."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def count_droplets(token: str) -> Optional[int]:
    """Return the number of droplets on the account, or None on failure."""
    try:
        return len(digitalocean.Manager(token=token).get_all_droplets())
    except Exception:
        return None


def is_credit_active(account_balance, month_to_date_usage, droplet_count: int) -> bool:
    """Heuristic: account is running droplets but billing shows zero."""
    if droplet_count is None or droplet_count <= 0:
        return False
    return (
        parse_amount(account_balance) == 0.0
        and parse_amount(month_to_date_usage) == 0.0
    )


def credit_label(account_balance, month_to_date_usage, droplet_count: Optional[int]) -> str:
    """Short Bahasa Indonesia label describing the billing posture."""
    if droplet_count is None:
        return 'ℹ️ Tidak bisa hitung droplet'
    if droplet_count == 0:
        return '⏸️ Belum ada droplet'
    if is_credit_active(account_balance, month_to_date_usage, droplet_count):
        return f'🎓 Kredit aktif ({droplet_count} droplet)'
    if parse_amount(month_to_date_usage) > 0:
        return f'💳 Pay-as-you-go ({droplet_count} droplet)'
    return f'✅ {droplet_count} droplet'
