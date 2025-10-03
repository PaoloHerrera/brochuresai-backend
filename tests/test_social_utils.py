from services.common.social import (
    classify_social_type,
    is_social_host,
    is_specific_social_media_link,
)


def test_is_social_host_true_and_false():
    assert is_social_host("twitter.com")
    assert is_social_host("www.linkedin.com")
    assert is_social_host("sub.facebook.com")
    assert not is_social_host("example.com")


def test_classify_social_type_basic_domains():
    assert classify_social_type("twitter.com") == "twitter"
    assert classify_social_type("x.com") == "twitter"
    assert classify_social_type("linkedin.com") == "linkedin"
    assert classify_social_type("github.com") == "github"


def test_is_specific_social_media_link_patterns():
    company_domain = "example.com"

    # Twitter valid handle vs invalid path
    assert is_specific_social_media_link("https://twitter.com/companyx", company_domain)
    assert not is_specific_social_media_link("https://twitter.com/home", company_domain)

    # LinkedIn company page valid vs generic
    assert is_specific_social_media_link(
        "https://www.linkedin.com/company/companyx", company_domain
    )
    assert not is_specific_social_media_link("https://www.linkedin.com/company", company_domain)

    # Discord invite code valid vs invalid path
    assert is_specific_social_media_link("https://discord.gg/ABCDEF", company_domain)
    assert not is_specific_social_media_link("https://discord.gg/download", company_domain)
