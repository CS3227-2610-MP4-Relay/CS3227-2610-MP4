"""Exercise native disclosures before assertions about their full record content."""


def expand_records(page):
    """Open each closed record with its real summary control."""
    for record in page.locator("details.record").all():
        if record.get_attribute("open") is None:
            record.locator("summary").click()


def result_links(page):
    """Expose the round's result-entry links through native expansion."""
    expand_records(page)
    return page.get_by_role("link", name="Record result", exact=True)
