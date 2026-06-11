from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def test_hash():
    password = "what the fuck man!"
    hash_value = password_hasher.hash(password)

    assert password_hasher.verify(password, hash_value)
    assert not password_hasher.verify("wrong_password", hash_value)
