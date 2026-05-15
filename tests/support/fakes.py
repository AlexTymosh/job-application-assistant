from __future__ import annotations


class FakeKeyring:
    def get_password(self, service_name: str, username: str) -> str | None:
        return None

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise AssertionError("tests must not write to keyring")

    def delete_password(self, service_name: str, username: str) -> None:
        raise AssertionError("tests must not delete from keyring")
