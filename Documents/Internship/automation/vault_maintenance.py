"""Run the token-free ByteSmart refresh and review workflow in one command."""

from __future__ import annotations

from vault_refresh import main as refresh_main
from vault_review import main as review_main
from vault_dashboard import main as dashboard_main


def main() -> int:
    refresh_result = refresh_main()
    if refresh_result != 0:
        return refresh_result
    review_result = review_main()
    if review_result != 0:
        return review_result
    return dashboard_main()


if __name__ == "__main__":
    raise SystemExit(main())
