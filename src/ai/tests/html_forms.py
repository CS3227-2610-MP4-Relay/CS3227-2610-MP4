"""Read forms from rendered pages the way a browser would submit them."""

from html.parser import HTMLParser


class _Forms(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self._textarea = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.forms.append({"action": attrs.get("action"), "fields": []})
        elif tag == "input" and self.forms:
            kind = attrs.get("type", "text")
            if kind == "checkbox" and "checked" not in attrs:
                return
            if kind != "submit" and "name" in attrs:
                self.forms[-1]["fields"].append((attrs["name"], attrs.get("value", "")))
        elif tag == "textarea" and self.forms:
            self._textarea = [attrs["name"], ""]

    def handle_data(self, data):
        if self._textarea is not None:
            self._textarea[1] += data

    def handle_endtag(self, tag):
        if tag == "textarea" and self._textarea is not None:
            name, value = self._textarea
            # HTML drops one newline straight after <textarea>.
            value = value.removeprefix("\n")
            self.forms[-1]["fields"].append((name, value))
            self._textarea = None


def forms(page):
    """Return each form's action and its submitted (name, value) pairs, in order."""
    parser = _Forms()
    parser.feed(page)
    return parser.forms


def browser_post(fields):
    """Turn (name, value) pairs into POST data, with the browser's CR LF breaks."""
    data = {}
    for name, value in fields:
        data.setdefault(name, []).append(value.replace("\n", "\r\n"))
    return data
