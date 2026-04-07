"""
Custom Channel Example
======================

Shows how to extend Sensa with your own data channels by subclassing
BaseChannel.  This lets you inject any real-time data source into
your agent's context — PagerDuty incidents, GitHub PRs, database
metrics, internal APIs, etc.

Two examples:
  1. PagerDutyChannel — surfaces active incidents so your agent knows
     about ongoing outages
  2. GitHubPRChannel — shows open pull requests awaiting review

pip install sensa aiohttp
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sensa import SensaClient
from sensa.channels import BaseChannel, register_channel


# ---------------------------------------------------------------------------
# Example 1: PagerDuty Incidents Channel
# ---------------------------------------------------------------------------

class PagerDutyChannel(BaseChannel):
    """
    A custom Sensa channel that fetches active PagerDuty incidents.

    This gives your AI agent awareness of ongoing outages and their
    severity, so it can factor system health into its responses.
    """

    # Unique name used to reference this channel in SensaClient config
    name = "pagerduty"

    # Human-readable description (shown in channel listings)
    description = "Active PagerDuty incidents and on-call status"

    # Default configuration — users can override via channel_config
    default_config = {
        "api_key": None,         # PagerDuty API key (required)
        "service_ids": [],       # Filter to specific services (empty = all)
        "min_severity": "info",  # Minimum severity: info, warning, error, critical
    }

    async def fetch(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch active incidents from PagerDuty.

        This method is called by SensaClient when the channel is requested.
        It must return a dict with the channel's structured data.

        In a real implementation, you'd call the PagerDuty API here.
        This example returns mock data for demonstration.
        """
        # --- In production, replace this with actual API calls: ---
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     headers = {"Authorization": f"Token token={config['api_key']}"}
        #     async with session.get(
        #         "https://api.pagerduty.com/incidents",
        #         headers=headers,
        #         params={"statuses[]": ["triggered", "acknowledged"]},
        #     ) as resp:
        #         data = await resp.json()
        #         return self._parse_incidents(data)

        # Mock data for demonstration
        return {
            "active_incidents": [
                {
                    "id": "P1234567",
                    "title": "High error rate on payment service",
                    "severity": "critical",
                    "status": "acknowledged",
                    "service": "payment-api",
                    "created_at": "2026-04-07T16:30:00Z",
                    "assigned_to": "oncall-team",
                },
                {
                    "id": "P1234568",
                    "title": "Elevated latency on search endpoint",
                    "severity": "warning",
                    "status": "triggered",
                    "service": "search-api",
                    "created_at": "2026-04-07T16:45:00Z",
                    "assigned_to": None,
                },
            ],
            "summary": {
                "critical": 1,
                "warning": 1,
                "info": 0,
                "total": 2,
            },
        }

    def format_context(self, data: Dict[str, Any]) -> str:
        """
        Format the channel's data as a human-readable string for
        inclusion in the agent's system prompt.

        This is what the agent actually sees in <current_environment>.
        Keep it concise but informative.
        """
        incidents = data.get("active_incidents", [])
        if not incidents:
            return "PagerDuty: No active incidents. All systems operational."

        summary = data.get("summary", {})
        lines = [
            f"PagerDuty: {summary.get('total', len(incidents))} active incident(s) "
            f"({summary.get('critical', 0)} critical, {summary.get('warning', 0)} warning)"
        ]
        for inc in incidents:
            severity = inc['severity'].upper()
            lines.append(
                f"  [{severity}] {inc['title']} "
                f"(service: {inc['service']}, status: {inc['status']})"
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Example 2: GitHub Pull Requests Channel
# ---------------------------------------------------------------------------

class GitHubPRChannel(BaseChannel):
    """
    Custom channel that surfaces open GitHub PRs awaiting review.

    Useful for developer-assistant agents that need to know about
    pending code reviews, CI status, and merge readiness.
    """

    name = "github_prs"
    description = "Open GitHub pull requests and their review status"

    default_config = {
        "token": None,           # GitHub personal access token
        "repos": [],             # List of "owner/repo" strings
        "show_draft": False,     # Include draft PRs
        "max_prs": 10,           # Max PRs to show per repo
    }

    async def fetch(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch open PRs from GitHub. (Mock data for demo.)"""

        # In production:
        # async with aiohttp.ClientSession() as session:
        #     headers = {"Authorization": f"Bearer {config['token']}"}
        #     for repo in config["repos"]:
        #         url = f"https://api.github.com/repos/{repo}/pulls"
        #         async with session.get(url, headers=headers) as resp:
        #             ...

        return {
            "repos": {
                "sensa-ai/sensa-py": [
                    {
                        "number": 42,
                        "title": "Add WebSocket support for streaming context",
                        "author": "alice",
                        "reviewers": ["bob", "carol"],
                        "status": "changes_requested",
                        "ci": "passing",
                        "created_at": "2026-04-05T10:00:00Z",
                        "updated_at": "2026-04-07T14:30:00Z",
                    },
                    {
                        "number": 43,
                        "title": "Fix staleness threshold edge case",
                        "author": "bob",
                        "reviewers": [],
                        "status": "review_needed",
                        "ci": "passing",
                        "created_at": "2026-04-07T09:15:00Z",
                        "updated_at": "2026-04-07T09:15:00Z",
                    },
                ],
            },
            "total_open": 2,
            "needs_review": 1,
        }

    def format_context(self, data: Dict[str, Any]) -> str:
        """Format PR data for the agent's context."""
        total = data.get("total_open", 0)
        needs_review = data.get("needs_review", 0)

        if total == 0:
            return "GitHub PRs: No open pull requests."

        lines = [f"GitHub PRs: {total} open ({needs_review} need review)"]

        for repo, prs in data.get("repos", {}).items():
            lines.append(f"  {repo}:")
            for pr in prs:
                review_status = pr["status"].replace("_", " ")
                lines.append(
                    f"    #{pr['number']} \"{pr['title']}\" "
                    f"by @{pr['author']} — {review_status} (CI: {pr['ci']})"
                )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Channel Registration
# ---------------------------------------------------------------------------

# Register your custom channels so SensaClient can discover them.
# After registration, they can be used just like built-in channels.

register_channel(PagerDutyChannel)
register_channel(GitHubPRChannel)


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

async def main():
    """
    Use custom channels alongside built-in ones.

    After registration, custom channels are first-class citizens —
    they appear in the same context string, support staleness detection,
    and can be individually configured.
    """
    client = SensaClient(
        api_key="your-sensa-api-key",
        # Mix built-in and custom channels
        channels=["time", "weather", "pagerduty", "github_prs"],
        channel_config={
            "pagerduty": {
                "api_key": "your-pagerduty-api-key",
                "min_severity": "warning",
            },
            "github_prs": {
                "token": "ghp_your_github_token",
                "repos": ["sensa-ai/sensa-py"],
                "max_prs": 5,
            },
        },
    )

    # Get the combined context — includes all channels
    context = await client.aget_context()
    print("=== Full Context with Custom Channels ===")
    print(context)
    # Output includes standard channels (time, weather) PLUS:
    #   PagerDuty: 2 active incident(s) (1 critical, 1 warning)
    #     [CRITICAL] High error rate on payment service (service: payment-api, status: acknowledged)
    #     [WARNING] Elevated latency on search endpoint (service: search-api, status: triggered)
    #   GitHub PRs: 2 open (1 need review)
    #     sensa-ai/sensa-py:
    #       #42 "Add WebSocket support for streaming context" by @alice — changes requested (CI: passing)
    #       #43 "Fix staleness threshold edge case" by @bob — review needed (CI: passing)

    # You can also fetch a single custom channel's structured data
    pd_data = await client.aget_channel("pagerduty")
    print(f"\nActive incidents: {pd_data['summary']['total']}")
    print(f"Critical: {pd_data['summary']['critical']}")


# ---------------------------------------------------------------------------
# Standalone demo (no API keys needed)
# ---------------------------------------------------------------------------

def standalone_demo():
    """
    Demonstrate the custom channels without requiring any API keys.
    Instantiates the channels directly and shows their output.
    """
    print("=== Custom Channel Demo ===\n")

    # You can use channels directly without going through SensaClient
    pd_channel = PagerDutyChannel()
    gh_channel = GitHubPRChannel()

    # Fetch data (uses mock data in these examples)
    pd_data = asyncio.run(pd_channel.fetch(pd_channel.default_config))
    gh_data = asyncio.run(gh_channel.fetch(gh_channel.default_config))

    # Format as context strings
    print(pd_channel.format_context(pd_data))
    print()
    print(gh_channel.format_context(gh_data))

    print("\n--- Channel Info ---")
    print(f"PagerDuty channel name: {pd_channel.name}")
    print(f"GitHub PR channel name: {gh_channel.name}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # This works without API keys — uses mock data
    standalone_demo()

    # Uncomment to run with SensaClient (requires API keys):
    # asyncio.run(main())
