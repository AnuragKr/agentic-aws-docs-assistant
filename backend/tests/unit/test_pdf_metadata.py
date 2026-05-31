from ingestion.enrichers.aws_services import detect_aws_services
from ingestion.parsers.pdf_structure import _sections_from_toc


class _FakePage:
    def get_text(self, _mode: str) -> str:
        return "Sample AWS IAM and CloudTrail guidance."


class _FakePdf:
    def __init__(self, page_count: int = 60) -> None:
        self._pages = [_FakePage() for _ in range(page_count)]

    def __len__(self) -> int:
        return len(self._pages)

    def __getitem__(self, index: int) -> _FakePage:
        return self._pages[index]


def test_detect_aws_services_from_text() -> None:
    text = "Use IAM roles with CloudTrail and AWS Organizations for governance."
    services = detect_aws_services(text)
    assert "AWS IAM" in services
    assert "AWS CloudTrail" in services
    assert "AWS Organizations" in services


def test_toc_builds_nested_sections_with_page_ranges() -> None:
    toc = [
        [1, "Security Pillar", 1],
        [2, "Identity and Access Management", 5],
        [3, "IAM Roles", 8],
        [2, "Logging and Monitoring", 20],
        [1, "Appendix", 40],
    ]
    pdf = _FakePdf(page_count=60)
    sections = _sections_from_toc(toc, pdf, total_pages=60)

    assert len(sections) == 2
    assert sections[0].title == "Security Pillar"
    assert len(sections[0].children) == 2

    iam = sections[0].children[0]
    assert iam.title == "Identity and Access Management"
    assert iam.page_start == 5
    assert iam.page_end == 19

    roles = iam.children[0]
    assert roles.title == "IAM Roles"
    assert roles.page_start == 8
    assert roles.page_end == 19
    assert "AWS IAM" in roles.content
