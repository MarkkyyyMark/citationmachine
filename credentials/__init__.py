"""Phase 4: draft author credentials via Claude web search (human-reviewed)."""

from .drafter import draft_credentials, CredentialError

__all__ = ["draft_credentials", "CredentialError"]
