from pwdlib import PasswordHash

content = b"what the fuck man!"

password_hasher = PasswordHash().recommended


def test_hash():

    hash1 = password_hasher.hash(content)
    hash2 = password_hasher.hash(content)

    assert hash1 == hash2

    content1 = b"what the fuck mam!"

    hash3 = password_hasher.hash(content1)

    assert hash1 != hash3
