"""Generate tests/data/compat.json from mdn/browser-compat-data.

The tests need one thin slice of BCD: which elements exist, which of them the
standard retired, which are still provisional, and the global attribute and
input type names. Vendoring BCD whole would be 1.3 MB of per-browser version
tables that churn with every Chrome release, burying the one line that
matters. This distills it to a file that diffs a line at a time.

The source is the published npm package rather than a git checkout, so a
snapshot records the release it came from and nobody needs a clone to
refresh one. Run it after a browser ships something::

    just compat

Then read the diff. A new element, or a status that flipped, is a change to
make deliberately: it means adding a class in ``src/django_div/__init__.py``,
regenerating the stub, and saying so in the docs. ``tests/test_tags.py`` and
``tests/test_attributes.py`` check the library against whatever this wrote,
so an unreviewed refresh fails the suite rather than passing quietly.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Any
from urllib.request import urlopen

#: The bundled build of BCD. One file, versioned, CC0-1.0.
PACKAGE = "@mdn/browser-compat-data"
REGISTRY = "https://registry.npmjs.org"
REPOSITORY = "https://github.com/mdn/browser-compat-data"

#: BCD names the open-ended ``data-*`` family alongside the real global
#: attributes. It is not a name anything can be checked against.
NOT_AN_ATTRIBUTE = "data_attributes"

TARGET = Path(__file__).parent.parent / "tests" / "data" / "compat.json"


def fetch_release(version: str = "latest") -> dict[str, Any]:
    """The npm metadata for one release: version, license, tarball URL."""
    with urlopen(f"{REGISTRY}/{PACKAGE}/{version}") as response:
        return json.load(response)


def fetch_data(url: str) -> dict[str, Any]:
    """The bundled data.json out of a release tarball, without unpacking it.

    Held in memory rather than written to a temporary directory: the archive
    is under a megabyte, and only one member of it is ever read.
    """
    with urlopen(url) as response:
        archive = io.BytesIO(response.read())
    with tarfile.open(fileobj=archive, mode="r:gz") as tar:
        member = tar.extractfile("package/data.json")
        if member is None:  # pragma: no cover - malformed release
            raise RuntimeError(f"{PACKAGE} has no package/data.json")
        return json.load(member)


def standing(entry: dict[str, Any]) -> dict[str, Any]:
    """One element's standing, flattened out of its compat block.

    ``deprecated`` and ``experimental`` are absent rather than false for most
    elements, so they are coerced: a snapshot where every element carries
    both keys turns a status change into a one-line diff.
    """
    compat = entry.get("__compat", {})
    status = compat.get("status", {})
    return {
        "deprecated": bool(status.get("deprecated")),
        "experimental": bool(status.get("experimental")),
        # Null for an element too new to have an MDN page, which is why the
        # library leaves the link out of those docstrings rather than
        # pointing at a 404.
        "mdn_url": compat.get("mdn_url"),
    }


def build_snapshot(release: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """The slice of BCD the tests read, ready to serialize."""
    html = data["html"]
    return {
        "source": {
            "package": PACKAGE,
            "version": release["version"],
            "license": release.get("license", "CC0-1.0"),
            "url": REPOSITORY,
        },
        "elements": {
            name: standing(entry) for name, entry in sorted(html["elements"].items())
        },
        "global_attributes": sorted(
            name for name in html["global_attributes"] if name != NOT_AN_ATTRIBUTE
        ),
        "input_types": sorted(
            name.removeprefix("type_")
            for name in html["elements"]["input"]
            if name.startswith("type_")
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default="latest",
        help=f"the {PACKAGE} release to read, or a dist-tag (default: latest)",
    )
    options = parser.parse_args()

    release = fetch_release(options.version)
    snapshot = build_snapshot(release, fetch_data(release["dist"]["tarball"]))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(snapshot, indent=2) + "\n")

    elements = snapshot["elements"]
    print(
        f"wrote {TARGET} from {PACKAGE}@{release['version']}: "
        f"{len(elements)} elements, "
        f"{sum(e['deprecated'] for e in elements.values())} deprecated, "
        f"{sum(e['experimental'] for e in elements.values())} experimental, "
        f"{len(snapshot['global_attributes'])} global attributes, "
        f"{len(snapshot['input_types'])} input types",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
