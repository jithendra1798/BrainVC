FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY seeds ./seeds
ENV PATH="/app/.venv/bin:$PATH"
# On first boot with an empty disk, restore the pre-seeded demo database
# (public + synthetic data only) so judges land on a full funnel, not a blank app.
CMD ["sh", "-c", "mkdir -p data && { [ -f data/brainvc.db ] || cp seeds/demo_snapshot.db data/brainvc.db 2>/dev/null || true; } && uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
