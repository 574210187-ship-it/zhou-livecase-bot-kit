from __future__ import annotations

from typing import Protocol


class TargetSystemReader(Protocol):
    """Private read-only adapter. No create/update/delete methods by contract."""

    def storage_download_sha_matches(self, record_id: str) -> bool: ...
    def case_rows_match_business_keys(self, record_id: str) -> bool: ...
    def q50_rows_match_case_keys_globally(self, record_id: str) -> bool: ...
    def source_row_has_verified_terminal_receipt(self, record_id: str) -> bool: ...


class TargetSystemView:
    """Named read-only mapping used by the independent auditor process."""

    def __init__(self, reader: TargetSystemReader):
        self._reader = reader

    def storage_verified(self, record_id: str) -> bool:
        return self._reader.storage_download_sha_matches(record_id)

    def case_verified(self, record_id: str) -> bool:
        return self._reader.case_rows_match_business_keys(record_id)

    def q50_verified_globally(self, record_id: str) -> bool:
        return self._reader.q50_rows_match_case_keys_globally(record_id)

    def source_verified(self, record_id: str) -> bool:
        return self._reader.source_row_has_verified_terminal_receipt(record_id)
