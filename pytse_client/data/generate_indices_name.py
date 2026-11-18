"""Regenerate indices_name.json (financial index name -> insCode).

Run from the repository root:

    python -m pytse_client.data.generate_indices_name

Keys are the index titles of the website without their section number and
dashes (e.g. "27-فلزات اساسي" becomes "فلزات اساسي" with section_number
27), the Arabic ي and ك of the website are kept.
"""

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Union

from pytse_client import tse_settings
from pytse_client.tsetmc_api import index

# see tse_settings.INDICES_LIST_URL
INDICES_LIST_URL = tse_settings.INDICES_LIST_URL

# flow 1 first: when an index of fara bourse has the same name as one of
# the stock exchange, the stock exchange one is kept.
INDICES_FLOWS = (1, 2)

INDICES_FILE = Path(__file__).parent / "indices_name.json"


def fetch_indices(flow: int) -> List[index.IndexLastValue]:
    """Rows of every financial index of a flow (market)."""
    return index.fetch_indices(flow)


def parse_index_title(title: str) -> Tuple[str, Union[int, str]]:
    """Split an index title like "27-فلزات اساسي" or
    "بيمه و بازنشسته66" into its name and section number ("" if none)."""
    section_number = re.search(r"(^\d+|\d+$)", title)
    section_number = (
        int(section_number.group(1)) if section_number is not None else ""
    )
    name = re.sub(r"^\d+|\d+$|-", "", title).strip()
    return name, section_number


def build_indices(
    rows_by_flow: Iterable[List[index.IndexLastValue]],
) -> Dict[str, Dict]:
    """indices_name.json content from the rows of each flow.

    Inside a flow, a later index with the same name replaces the earlier
    one (like the old scraper did); an index of a later flow never replaces
    one of an earlier flow.
    """
    indices: Dict[str, Dict] = {}
    for rows in rows_by_flow:
        flow_indices: Dict[str, Dict] = {}
        for row in rows:
            name, section_number = parse_index_title(row.name)
            flow_indices[name] = {
                "index": row.ins_code,
                "section_number": section_number,
            }
        for name, value in flow_indices.items():
            indices.setdefault(name, value)
    return indices


def get_financial_indices(
    flows: Iterable[int] = INDICES_FLOWS,
) -> Dict[str, Dict]:
    """Financial index name -> {"index", "section_number"} from the API."""
    return build_indices(fetch_indices(flow) for flow in flows)


def write_indices(indices: Dict[str, Dict], path: Path = INDICES_FILE):
    with open(path, "w", encoding="utf8") as file:
        json.dump(indices, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    write_indices(get_financial_indices())
