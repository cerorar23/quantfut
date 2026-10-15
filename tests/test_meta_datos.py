"""Normalización de user_data según «Customer information parameters» de Meta."""
import hashlib

import pytest

from qf.comercial import meta_datos as m


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def test_email_se_recorta_y_pasa_a_minusculas_antes_del_hash():
    ud = m.user_data({"account_id": 7, "email": "  Ana.Perez@Ejemplo.COM ", "display_name": None},
                     None, None)
    assert ud["em"] == [h("ana.perez@ejemplo.com")]


def test_external_id_es_estable_y_no_se_cifra_dos_veces():
    assert m.external_id(7) == h("qf:7")
    ud = m.user_data({"account_id": 7, "email": "a@b.co", "display_name": None}, None, None)
    assert ud["external_id"] == [h("qf:7")]


def test_nombre_se_parte_por_el_primer_espacio_sin_puntuacion():
    assert m.split_name("José  María O'Neil") == ("josé", "maría oneil")
    assert m.split_name("Ana") == ("ana", None)
    assert m.split_name("  ") == (None, None)
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": "Ana Pérez"}, None, None)
    assert ud["fn"] == [h("ana")] and ud["ln"] == [h("pérez")]


def test_pais_en_minusculas_y_cifrado_solo_si_es_alfa2():
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, None, "CO")
    assert ud["country"] == [h("co")]
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, None, "COL")
    assert "country" not in ud


def test_identificadores_del_dispositivo_van_sin_cifrar():
    ident = {"anon_id": "XZabc", "madid": "38400000-8cf0-11bd-b23e-10b96e40000d",
             "client_ip": "2001:db8::1", "user_agent": "QuantFut/1.0 (Android; Flutter)"}
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, ident, None)
    assert ud["anon_id"] == "XZabc"
    assert ud["madid"] == "38400000-8cf0-11bd-b23e-10b96e40000d"
    assert ud["client_ip_address"] == "2001:db8::1"
    assert ud["client_user_agent"] == "QuantFut/1.0 (Android; Flutter)"


def test_sin_madid_no_se_manda_el_campo():
    ident = {"anon_id": "XZabc", "madid": None, "client_ip": None, "user_agent": None}
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, ident, None)
    assert "madid" not in ud and "client_ip_address" not in ud


def test_extinfo_exige_16_posiciones_y_version_de_plataforma():
    ok = ["a2", "com.saptain.quantfut", "1.0.0", "1", "14", "Pixel 8", "es_CO", "COT", "", "1080",
          "2400", "2.75", "8", "", "", "America/Bogota"]
    assert m.valid_extinfo(ok, "android") == ok
    with pytest.raises(ValueError):
        m.valid_extinfo(ok[:15], "android")
    with pytest.raises(ValueError):
        m.valid_extinfo(ok, "ios")              # a2 no es iOS
    with pytest.raises(ValueError):
        m.valid_extinfo(["a2"] + ["x" * 101] * 15, "android")
