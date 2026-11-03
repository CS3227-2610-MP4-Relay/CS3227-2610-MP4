"""Shared checks for native AI form navigation while a fake reply is gated."""

import threading
from unittest import mock

from playwright.sync_api import expect


def assert_pending_submit(page, target, label, pending, reply, result_heading):
    """Check one request, pending accessibility and history/page-show recovery."""
    release = threading.Event()
    snapshots = []

    def capture(snapshot):
        snapshots.append(snapshot)
        release.set()

    def respond(*args):
        assert release.wait(5), "Pending UI was not captured before the reply"
        return reply

    button = page.get_by_role("button", name=label, exact=True)
    form = button.locator("..")
    status = form.locator('[role="status"]')
    # Chromium destroys the old execution context during native navigation.
    # Capture its rendered state in submit, before allowing the fake reply.
    page.expose_function("capturePending", capture)
    form.evaluate("""form => form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      const status = form.querySelector('[role="status"]');
      const duplicate = new SubmitEvent('submit', {cancelable: true, bubbles: true});
      form.dispatchEvent(duplicate);
      window.capturePending({disabled: button.disabled, text: status.textContent,
        visible: status.getBoundingClientRect().height > 0,
        live: status.getAttribute('aria-live'), cancelled: duplicate.defaultPrevented});
    }, {once: true})""")
    with mock.patch(target, side_effect=respond) as complete:
        try:
            button.click()
            assert snapshots == [
                {
                    "disabled": True,
                    "text": pending,
                    "visible": True,
                    "live": "polite",
                    "cancelled": True,
                }
            ], snapshots
        finally:
            release.set()
        expect(
            page.get_by_role("heading", name=result_heading, exact=True)
        ).to_be_visible()
        expect(button).to_be_enabled()
        expect(status).to_be_empty()
        complete.assert_called_once()
        page.go_back()
        expect(button).to_be_enabled()
        expect(status).to_be_empty()
        # Browser cache policy can prevent real BFCache restoration. Exercise its
        # pageshow event explicitly after a cancelled navigation as well.
        form.evaluate("""form => form.addEventListener(
          'submit', event => event.preventDefault(), {once: true})""")
        button.click()
        expect(button).to_be_disabled()
        expect(status).to_have_text(pending)
        page.evaluate(
            "window.dispatchEvent("
            "new PageTransitionEvent('pageshow', {persisted: true}))"
        )
        expect(button).to_be_enabled()
        expect(status).to_be_empty()
        complete.assert_called_once()
