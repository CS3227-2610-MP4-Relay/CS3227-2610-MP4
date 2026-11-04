"""Shared layout, contrast and action-link checks for browser journeys."""

from playwright.sync_api import expect


def contrast(colors):
    """Return WCAG contrast for computed opaque RGB foreground/background."""

    def luminance(color):
        components = [int(value) / 255 for value in color[4:-1].split(",")]
        linear = [
            v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
            for v in components
        ]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    a, b = sorted(luminance(color) for color in colors)
    return (b + 0.05) / (a + 0.05)


def assert_contrast(locator):
    """Resolve transparent ancestors when checking a rendered text color."""
    colors = locator.evaluate("""el => {
      const foreground = getComputedStyle(el).color;
      while (getComputedStyle(el).backgroundColor === 'rgba(0, 0, 0, 0)')
        el = el.parentElement;
      return [foreground, getComputedStyle(el).backgroundColor];
    }""")
    assert contrast(colors) >= 4.5


def assert_layout(page, width):
    """Check shared shell, real element bounds and readable palette."""
    surface = page.locator("main")
    expect(surface).to_be_visible()
    metrics = surface.evaluate("""el => {
      const s = getComputedStyle(el), b = getComputedStyle(document.body);
      const box = el.getBoundingClientRect();
      return {background: s.backgroundColor, surrounding: b.backgroundColor,
        font: parseFloat(b.fontSize), line: parseFloat(b.lineHeight),
        left: box.left, right: box.right, width: box.width,
        padding: parseFloat(s.paddingLeft),
        overflow: document.documentElement.scrollWidth > innerWidth};
    }""")
    assert metrics["background"] == "rgb(255, 255, 255)"
    assert metrics["surrounding"] not in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)")
    assert metrics["font"] >= 16
    assert metrics["line"] >= metrics["font"] * 1.4
    assert (
        page.locator("h1").evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
        > metrics["font"]
    )
    assert metrics["padding"] >= 12
    assert not metrics["overflow"]
    assert metrics["left"] >= 8 and metrics["right"] <= width - 8
    if width > 1000:
        assert metrics["width"] <= 1100
        assert abs(metrics["left"] - (width - metrics["right"])) <= 1
    for control in page.locator(
        "input:not([type=hidden]), textarea, select, button, fieldset, table"
    ).all():
        box = control.bounding_box()
        assert box and box["x"] >= metrics["left"]
        assert box["x"] + box["width"] <= metrics["right"]
    assert_contrast(surface)
    for locator in page.locator(
        "a, button, h1, h2, h3, h4, label, legend, th, td, textarea, select, "
        "input:not([type=hidden]), .state, .error, [role=status], [role=alert]"
    ).all():
        assert_contrast(locator)
    for link in page.locator("a").all():
        decoration = link.evaluate("el => getComputedStyle(el).textDecorationLine")
        if "action" in (link.get_attribute("class") or "").split():
            assert decoration == "none"
        else:
            assert "underline" in decoration


def assert_action_link_states(page, link):
    """Action labels remain undecorated and readable during native interaction."""
    assert link.evaluate("el => el.tagName") == "A"
    page.mouse.move(0, 0)
    for state in ("rest", "hover", "focus"):
        if state == "hover":
            link.hover()
        elif state == "focus":
            page.mouse.move(0, 0)
            link.focus()
        assert link.evaluate("el => getComputedStyle(el).textDecorationLine") == "none"
        assert_contrast(link)
