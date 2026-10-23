import pytest
import requests

from order_manager.services.zip_code import ZipCodeError, ZipCodeNotFoundError, lookup_zip_code


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.urls = []

    def get(self, url, timeout):
        self.urls.append(url)
        if self.error:
            raise self.error
        return self.response


def test_lookup_returns_address():
    session = FakeSession(
        FakeResponse({"logradouro": "Praça da Sé", "bairro": "Sé", "localidade": "São Paulo", "uf": "SP"})
    )
    address = lookup_zip_code("01001-000", session=session)
    assert session.urls == ["https://viacep.com.br/ws/01001000/json/"]
    assert (address.street, address.city, address.state) == ("Praça da Sé", "São Paulo", "SP")


def test_unknown_zip_code():
    with pytest.raises(ZipCodeNotFoundError):
        lookup_zip_code("99999999", session=FakeSession(FakeResponse({"erro": True})))


@pytest.mark.parametrize("value", ["123", "", "abcdefgh"])
def test_invalid_zip_code_does_not_call_api(value):
    session = FakeSession()
    with pytest.raises(ZipCodeError):
        lookup_zip_code(value, session=session)
    assert session.urls == []


def test_network_error_is_wrapped():
    session = FakeSession(error=requests.ConnectionError("offline"))
    with pytest.raises(ZipCodeError, match="offline"):
        lookup_zip_code("01001000", session=session)
