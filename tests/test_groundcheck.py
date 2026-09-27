"""The guardrail must fail closed.

Trap cases for a broken verifier: the model call returns an empty, garbled or
hedged reply instead of the one word it was asked for. Each of these must count
as UNSUPPORTED, so the summary is blocked rather than shown. No network needed:
the model call is replaced with a fixed reply. All text is synthetic.
"""

import unittest
from unittest import mock

from src import groundcheck

SOURCE = (
    "Customer reports being charged twice for their March subscription. "
    "Agent escalated to the payments team. No refund has been processed yet."
)
SUMMARY = "The customer was charged twice and the case went to the payments team."


def fake_model(verify_reply):
    """Model stand-in: a clean claim list for extraction, a fixed reply for verification."""
    def complete(system, user, max_tokens=700):
        if "TASK:EXTRACT_CLAIMS" in system:
            return '["The customer was charged twice.", "The case went to the payments team."]'
        if "TASK:VERIFY" in system:
            return verify_reply
        raise AssertionError("unexpected prompt")
    return complete


class VerifierReplyParsing(unittest.TestCase):
    def test_only_a_reply_starting_with_supported_counts(self):
        for reply in ["SUPPORTED", "supported", "  Supported.\n", "SUPPORTED - paraphrase of line 1"]:
            with self.subTest(reply=reply):
                self.assertTrue(groundcheck.is_supported(reply))

    def test_empty_garbled_or_hedged_replies_fail_closed(self):
        traps = [
            "",                                 # empty reply
            "   \n",                            # whitespace only
            None,                               # no text at all
            "NO",                               # wrong vocabulary
            "Not supported",                    # the old check let this through
            "UNSUPPORTED",
            "unsupported.",
            "I think it is SUPPORTED",          # hedged: does not start with the verdict
            "**SUPPORTED**",                    # formatting noise: blocked, not guessed
            "{\"verdict\": \"SUPPORTED\"}",     # wrong format
            "S#UPP0RTED ???",                   # garbled
        ]
        for reply in traps:
            with self.subTest(reply=reply):
                self.assertFalse(groundcheck.is_supported(reply))


class GroundCheckFailsClosed(unittest.TestCase):
    def check_with(self, verify_reply, summary=SUMMARY):
        with mock.patch.object(groundcheck, "complete", fake_model(verify_reply)):
            return groundcheck.ground_check(SOURCE, summary)

    def test_empty_verifier_reply_blocks_the_summary(self):
        passed, results = self.check_with("")
        self.assertFalse(passed)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(not ok for _, ok in results))

    def test_garbled_verifier_reply_blocks_the_summary(self):
        for reply in ["NO", "Not supported", "lorem ipsum", "S#UPP0RTED"]:
            with self.subTest(reply=reply):
                passed, _ = self.check_with(reply)
                self.assertFalse(passed)

    def test_clean_supported_replies_let_the_summary_through(self):
        passed, results = self.check_with("SUPPORTED")
        self.assertTrue(passed)
        self.assertTrue(all(ok for _, ok in results))

    def test_summary_with_no_claims_is_blocked(self):
        def complete(system, user, max_tokens=700):
            if "TASK:EXTRACT_CLAIMS" in system:
                return "[]"          # nothing to check
            return "SUPPORTED"
        with mock.patch.object(groundcheck, "complete", complete):
            passed, results = groundcheck.ground_check(SOURCE, "")
        self.assertEqual(results, [])
        self.assertFalse(passed)

    def test_bad_extractor_output_falls_back_to_sentences_and_still_checks(self):
        def complete(system, user, max_tokens=700):
            if "TASK:EXTRACT_CLAIMS" in system:
                return "Sorry, I can't produce JSON."   # garbled extractor reply
            return ""                                    # and an empty verifier reply
        with mock.patch.object(groundcheck, "complete", complete):
            passed, results = groundcheck.ground_check(SOURCE, SUMMARY)
        self.assertEqual([c for c, _ in results], [SUMMARY])
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
