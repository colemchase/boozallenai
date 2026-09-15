import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ALLOWED_HOST = "registry.opendata.aws"
DATASET_ALIASES = {
    "the cancer genome atlas": "tcga",
    "cancer genome atlas": "tcga",
    "tcga": "tcga",
    "mimic-iii": "mimiciii",
    "mimic iii": "mimiciii",
    "mimiciii": "mimiciii",
}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip = True

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.parts.append(text)


def lambda_handler(event, context):
    body = _body(event)
    question = body.get("question") or body.get("query") or body.get("input") or ""
    dataset = body.get("dataset") or _infer_dataset(question)
    if not dataset:
        return _ok({"error": "dataset_not_identified"})

    slug = _slug(dataset)
    url = f"https://{ALLOWED_HOST}/{slug}/"
    page_text = _fetch_text(url)
    snippets = _snippets(page_text, question)

    return _ok({
        "dataset": slug,
        "url": url,
        "snippets": snippets,
        "instruction": "Answer the user's question using only these snippets. Return only the requested fact."
    })


def _body(event):
    if isinstance(event, dict) and "body" in event:
        raw = event["body"]
        return json.loads(raw) if isinstance(raw, str) else raw
    return event if isinstance(event, dict) else {}


def _infer_dataset(question):
    q = question.lower()
    for name, slug in DATASET_ALIASES.items():
        if name in q:
            return slug
    return ""


def _slug(dataset):
    text = str(dataset).lower().strip()
    text = DATASET_ALIASES.get(text, text)
    text = re.sub(r"[^a-z0-9-]+", "-", text).strip("-")
    return text


def _fetch_text(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise ValueError("Only registry.opendata.aws HTTPS pages are allowed")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "aws-ai-league-open-data-lookup/1.0"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        html = resp.read(1_500_000).decode("utf-8", errors="replace")

    parser = TextExtractor()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _snippets(text, question):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    terms = _terms(question)
    scored = []
    for i, sentence in enumerate(sentences):
        s = sentence.lower()
        score = sum(1 for term in terms if term in s)
        if score:
            window = " ".join(sentences[max(0, i - 1): i + 2])
            scored.append((score, len(window), window))
    scored.sort(key=lambda item: (-item[0], item[1]))
    snippets = []
    seen = set()
    for _, _, snippet in scored:
        clean = snippet[:1200]
        if clean not in seen:
            seen.add(clean)
            snippets.append(clean)
        if len(snippets) >= 5:
            break
    return snippets or [text[:1200]]



def _terms(question):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", question.lower())
    stop = {
        "using", "registry", "open", "data", "aws", "look", "lookup",
        "dataset", "which", "what", "when", "where", "with", "from",
        "the", "and", "for", "that", "this", "between"
    }
    return [word for word in words if word not in stop]


def _ok(payload):
    return {
        "statusCode": 200,
        "body": json.dumps(payload, separators=(",", ":"))
    }
