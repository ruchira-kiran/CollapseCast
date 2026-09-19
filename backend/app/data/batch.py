"""Column-oriented container for a batch of companies' raw signals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from app.config import POSTINGS_SIGNAL, SCALAR_SIGNALS


@dataclass
class SignalBatch:
    """Scalar signals as one float array per signal, plus one weekly-postings array per company.

    Postings are kept as a list because API callers may send series of different lengths.
    """

    scalars: dict[str, np.ndarray]
    postings: list[np.ndarray]

    def __len__(self) -> int:
        return len(self.postings)

    @classmethod
    def from_records(cls, records: Sequence[Mapping[str, Any]]) -> "SignalBatch":
        return cls(
            scalars={k: np.array([float(r[k]) for r in records], dtype=float) for k in SCALAR_SIGNALS},
            postings=[np.asarray(r[POSTINGS_SIGNAL], dtype=float) for r in records],
        )

    def matrix(self, names: Sequence[str]) -> np.ndarray:
        """Stack the named scalar signals into an (n_companies, len(names)) matrix."""
        return np.column_stack([self.scalars[k] for k in names])
