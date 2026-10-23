"""Brazilian ZIP code (CEP) lookup using the public ViaCEP API."""

from __future__ import annotations

import requests

from order_manager.domain.formatting import digits_only
from order_manager.domain.models import Address

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"


class ZipCodeError(Exception):
    """Base error for ZIP code lookups."""


class ZipCodeNotFoundError(ZipCodeError):
    pass


def lookup_zip_code(
    zip_code: str,
    session: requests.Session | None = None,
    timeout: float = 5.0,
) -> Address:
    """Return the address for ``zip_code`` (number is left blank).

    Raises :class:`ZipCodeNotFoundError` for unknown CEPs and :class:`ZipCodeError` for
    invalid input or network problems.
    """
    cep = digits_only(zip_code)
    if len(cep) != 8:
        raise ZipCodeError("O CEP deve ter 8 dígitos.")
    http = session or requests
    try:
        response = http.get(VIACEP_URL.format(cep=cep), timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ZipCodeError(f"Falha ao consultar o CEP: {exc}") from exc
    if data.get("erro"):
        raise ZipCodeNotFoundError(f"CEP {cep} não encontrado.")
    return Address(
        zip_code=cep,
        street=data.get("logradouro", ""),
        district=data.get("bairro", ""),
        city=data.get("localidade", ""),
        state=data.get("uf", ""),
    )
