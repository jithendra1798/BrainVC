"""Outbound GitHub connector: public footprint → RawSignals with real provenance.

Unauthenticated (60 req/hr — fine at demo scale); set GITHUB_TOKEN to raise
limits. Two calls per founder: profile + recently-pushed repos. Forks are
excluded — we score what someone builds, not what they mirror.
"""

import os
from datetime import datetime

import httpx

from app.contracts.enums import SourceType
from app.contracts.signals import ConnectorQuery, RawSignal

API = "https://api.github.com"
MAX_REPOS = 8


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "brainvc-hackathon"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _iso(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


class GitHubConnector:
    source_type = SourceType.GITHUB

    def fetch(self, query: ConnectorQuery) -> list[RawSignal]:
        handle = query.params["handle"]
        with httpx.Client(headers=_headers(), timeout=20) as client:
            user = client.get(f"{API}/users/{handle}")
            user.raise_for_status()
            profile = user.json()
            repos_response = client.get(
                f"{API}/users/{handle}/repos",
                params={"sort": "pushed", "per_page": 30})
            repos_response.raise_for_status()
            repos = [r for r in repos_response.json() if not r.get("fork")][:MAX_REPOS]

        display_name = profile.get("name") or handle
        signals = [RawSignal(
            source_type=self.source_type,
            source_ref=profile.get("html_url", f"https://github.com/{handle}"),
            content=(
                f"GitHub profile: {display_name} (@{handle}). "
                f"Bio: {profile.get('bio') or 'none'}. "
                f"Public repos: {profile.get('public_repos', 0)}. "
                f"Followers: {profile.get('followers', 0)}. "
                f"Location: {profile.get('location') or 'unknown'}. "
                f"Company: {profile.get('company') or 'none'}. "
                f"Account created: {profile.get('created_at', '?')[:10]}."
            ),
            observed_at=_iso(profile.get("updated_at")),
            founder_hint=display_name,
        )]
        for repo in repos:
            topics = ", ".join(repo.get("topics") or [])
            signals.append(RawSignal(
                source_type=self.source_type,
                source_ref=repo["html_url"],
                content=(
                    f"Repository {repo['full_name']}: "
                    f"{repo.get('description') or 'no description'}. "
                    f"Language: {repo.get('language') or 'unknown'}. "
                    f"Stars: {repo.get('stargazers_count', 0)}, "
                    f"forks: {repo.get('forks_count', 0)}. "
                    f"Created {repo.get('created_at', '?')[:10]}, "
                    f"last pushed {repo.get('pushed_at', '?')[:10]}."
                    + (f" Topics: {topics}." if topics else "")
                ),
                observed_at=_iso(repo.get("pushed_at")),
                founder_hint=display_name,
            ))
        return signals
