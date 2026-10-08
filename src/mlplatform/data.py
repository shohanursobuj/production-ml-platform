"""Rotten Tomatoes movie reviews (binary sentiment), downloaded once and cached as parquet."""

import urllib.request
from pathlib import Path

import pandas as pd

from mlplatform.config import DATA_DIR

URL = (
    "https://huggingface.co/api/datasets/cornell-movie-review-data/"
    "rotten_tomatoes/parquet/default/{split}/0.parquet"
)


def load_split(split: str, cache_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Return a DataFrame with `text` and `label` (1 = positive) columns."""
    path = cache_dir / f"{split}.parquet"
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        url = URL.format(split=split)
        request = urllib.request.Request(url, headers={"User-Agent": "mlplatform"})
        with urllib.request.urlopen(request, timeout=60) as response:
            path.write_bytes(response.read())
    return pd.read_parquet(path)[["text", "label"]]
