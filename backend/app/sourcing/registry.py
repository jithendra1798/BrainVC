"""Connector registry: adding a source = one connector file + one entry here.
Nothing else in the system changes (core modularity rule)."""

from app.sourcing.connectors.github import GitHubConnector
from app.sourcing.connectors.inbound_deck import InboundDeckConnector

CONNECTORS = {
    "inbound_deck": InboundDeckConnector(),
    "github": GitHubConnector(),
    # "arxiv": ArxivConnector(),        # stretch
    # "synthetic": SyntheticProfileConnector(),  # seeds
}


def get_connector(name: str):
    return CONNECTORS[name]
