"""Offline tests (no API calls). Run from project root:  python -m unittest tests.test_label_mapping -v"""
import json, sys, types, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.label_mapping import baselines as B, metrics as M, llm_mapper as L


def item(i, lab, src="LinkedIn", conf="High"):
    return {"id": i, "original_label": lab, "canonical_source": src, "confidence": conf, "rationale": "r"}


class Fake:
    """Mimics client.messages.create; replies from a queue of (text, stop_reason) or exceptions."""
    def __init__(self, replies): self.replies, self.calls = list(replies), []
    @property
    def messages(self): return self
    def create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0)
        if isinstance(r, Exception): raise r
        text, stop = r
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=text)], stop_reason=stop,
                                     usage=types.SimpleNamespace(input_tokens=100, output_tokens=50))


class TestValidation(unittest.TestCase):
    sent = {1: "a", 2: "b"}
    def v(self, obj): return L.validate_response(self.sent, obj if isinstance(obj, str) else json.dumps(obj))
    def types_(self, p): return sorted(x["type"] for x in p)
    def test_ok(self):
        valid, p = self.v({"results": [item(1, "a"), item(2, "b", "Unknown", "Low")]}); self.assertEqual((len(valid), p), (2, []))
    def test_malformed(self): self.assertEqual(self.types_(self.v("{not json")[1]), ["malformed_json"])
    def test_bad_schema(self): self.assertEqual(self.types_(self.v({"x": 1})[1]), ["bad_schema"])
    def test_missing_label(self):
        valid, p = self.v({"results": [item(1, "a")]}); self.assertEqual((list(valid), self.types_(p)), ([1], ["missing_label"]))
    def test_duplicate_rejected(self):
        valid, p = self.v({"results": [item(1, "a"), item(1, "a"), item(2, "b")]}); self.assertEqual((list(valid), self.types_(p)), ([2], ["duplicate_id"]))
    def test_unexpected_id(self): self.assertIn("unexpected_id", self.types_(self.v({"results": [item(1, "a"), item(9, "z"), item(2, "b")]})[1]))
    def test_invalid_canonical(self): self.assertIn("invalid_canonical", self.types_(self.v({"results": [item(1, "a", "Glassdoor"), item(2, "b")]})[1]))
    def test_invalid_confidence(self): self.assertIn("invalid_confidence", self.types_(self.v({"results": [item(1, "a", conf="Sure"), item(2, "b")]})[1]))
    def test_extra_field(self):
        x = item(1, "a"); x["note"] = "hi"; self.assertIn("unexpected_field", self.types_(self.v({"results": [x, item(2, "b")]})[1]))
    def test_label_mismatch(self): self.assertIn("label_mismatch", self.types_(self.v({"results": [item(1, "CHANGED"), item(2, "b")]})[1]))
    def test_whitespace_echo_tolerated(self):
        valid, p = L.validate_response({1: "Indeed "}, json.dumps({"results": [item(1, "Indeed", "Indeed")]}))
        self.assertEqual((len(valid), p), (1, [])); self.assertTrue(valid[1]["echo_whitespace_only"])


class TestMapper(unittest.TestCase):
    def test_retry_then_success_and_injection_not_obeyed_by_code(self):
        good = json.dumps({"results": [item(1, "x", "Indeed"), item(2, "y", "Unknown", "Low")]})
        c = Fake([("garbage", "end_turn"), (good, "end_turn")])
        res, meta = L.classify_labels(["x", "y"], c, "m")
        self.assertEqual((meta["retries"], meta["n_failed"]), (1, 0)); self.assertEqual(res["x"]["canonical_source"], "Indeed")
        self.assertNotIn("temperature", c.calls[0])
        sent_user = c.calls[0]["messages"][0]["content"]; self.assertEqual(json.loads(sent_user)["labels"][0], {"id": 1, "label": "x"})
        self.assertNotIn("x", c.calls[0]["system"].split("Allowed")[0])   # labels never in system prompt
    def test_failures_reported_not_dropped(self):
        c = Fake([RuntimeError("boom")] * 3)
        res, meta = L.classify_labels(["x"], c, "m")
        self.assertTrue(res["x"]["failed"]); self.assertEqual((meta["n_failed"], meta["validation_problems"]["api_error"]), (1, 3))
    def test_truncation_counted(self):
        c = Fake([('{"results": [', "max_tokens")] * 3)
        _, meta = L.classify_labels(["x"], c, "m"); self.assertEqual(meta["validation_problems"]["truncated_response"], 3)
    def test_partial_batch_only_missing_resent(self):
        part = json.dumps({"results": [item(1, "x")]}); rest = json.dumps({"results": [item(2, "y")]})
        c = Fake([(part, "end_turn"), (rest, "end_turn")]); res, meta = L.classify_labels(["x", "y"], c, "m")
        self.assertEqual(meta["n_failed"], 0); self.assertEqual(len(json.loads(c.calls[1]["messages"][0]["content"])["labels"]), 1)


class FakeGroq:
    """Mimics OpenAI-compatible client.chat.completions.create."""
    def __init__(self, replies): self.replies, self.calls = list(replies), []
    @property
    def chat(self): return self
    @property
    def completions(self): return self
    def create(self, **kw):
        self.calls.append(kw); r = self.replies.pop(0)
        if isinstance(r, Exception): raise r
        text, fin = r
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text), finish_reason=fin)],
                                     usage=types.SimpleNamespace(prompt_tokens=120, completion_tokens=60))


class TestGroqBackend(unittest.TestCase):
    def test_groq_request_shape_and_parse(self):
        good = json.dumps({"results": [item(1, "x", "Indeed"), item(2, "y", "Unknown", "Low")]})
        c = FakeGroq([(good, "stop")]); res, meta = L.classify_labels(["x", "y"], c, "openai/gpt-oss-20b", provider="groq")
        kw = c.calls[0]
        self.assertEqual(kw["temperature"], 0); self.assertEqual(kw["response_format"]["type"], "json_schema"); self.assertTrue(kw["response_format"]["json_schema"]["strict"])
        self.assertEqual([m["role"] for m in kw["messages"]], ["system", "user"]); self.assertNotIn("x", kw["messages"][0]["content"].split("Allowed")[0])
        self.assertEqual(json.loads(kw["messages"][1]["content"])["labels"][0], {"id": 1, "label": "x"})
        self.assertEqual((meta["n_failed"], meta["input_tokens"], meta["output_tokens"], meta["temperature"], meta["provider"]), (0, 120, 60, 0, "groq"))
    def test_groq_length_is_truncation(self):
        c = FakeGroq([('{"results": [', "length")] * 3); _, meta = L.classify_labels(["x"], c, "m", provider="groq")
        self.assertEqual(meta["validation_problems"]["truncated_response"], 3)
    def test_groq_json_object_fallback(self):
        good = json.dumps({"results": [item(1, "x", "Indeed")]}); c = FakeGroq([(good, "stop")])
        L.classify_labels(["x"], c, "m", provider="groq", structured=False); self.assertEqual(c.calls[0]["response_format"], {"type": "json_object"})
    def test_key_redaction(self):
        self.assertNotIn("gsk_abcDEF123", L._safe_err(RuntimeError("bad key gsk_abcDEF123"))["message"])
    def test_cost_none_when_price_unverified(self): self.assertIsNone(L.cost_usd(100, 100, None, None))


class TestBaselinesMetrics(unittest.TestCase):
    def test_a_faithful(self):
        r = B.baseline_a(["Indeed ", "LINKEDIN", "Linkdin"]); self.assertEqual(list(r.predicted_source), ["Indeed", "LinkedIn", "Unknown"]); self.assertEqual(list(r.unmapped), [False, False, True])
    def test_b_cutoff(self):
        self.assertEqual(B.baseline_b(["Linkdin"], 0.8).predicted_source[0], "LinkedIn"); self.assertEqual(B.baseline_b(["social media"], 0.8).predicted_source[0], "Unknown")
    def test_wilson(self):
        lo, hi = M.wilson(0, 10); self.assertEqual(lo, 0.0); self.assertAlmostEqual(hi, 0.2775, 3)
        lo, hi = M.wilson(50, 100); self.assertAlmostEqual(lo, 0.4038, 3); self.assertAlmostEqual(hi, 0.5962, 3)


if __name__ == "__main__":
    unittest.main()
