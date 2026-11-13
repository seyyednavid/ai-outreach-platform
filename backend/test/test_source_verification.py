
from app.services.source_verification import allowed_url


def test_allowed_public_source():
    assert allowed_url(
        "https://www.bizseek.co.uk/marks-spencer"
    )


def test_reject_localhost():
    assert not allowed_url(
        "https://localhost/internal"
    )


def test_reject_private_ip():
    assert not allowed_url(
        "https://127.0.0.1/admin"
    )


def test_reject_http():
    assert not allowed_url(
        "http://www.bizseek.co.uk/marks-spencer"
    )


def test_reject_unapproved_domain():
    assert not allowed_url(
        "https://unapproved.example/profile"
    )


def test_reject_redirect_target_port():
    assert not allowed_url(
        "https://www.bizseek.co.uk:8080/profile"
    )
