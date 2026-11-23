import unittest
from listing_safety import escape_table_cell, safe_application_url


class MarkdownSafetyTests(unittest.TestCase):
    def test_escape_pipe_and_html(self):
        self.assertEqual(escape_table_cell('Data | <script>alert(1)</script>'), 'Data \\| &lt;script&gt;alert(1)&lt;/script&gt;')

    def test_multiline_stays_in_one_cell(self):
        self.assertEqual(escape_table_cell('Toronto\nRemote\tHybrid'), 'Toronto Remote Hybrid')

    def test_backslashes_are_escaped(self):
        self.assertEqual(escape_table_cell(r'A\\|B'), r'A\\\\\\|B')

    def test_null_field(self):
        self.assertEqual(escape_table_cell(None), '')

    def test_valid_job_link(self):
        self.assertEqual(safe_application_url('https://jobs.example.com/apply?gh_jid=42&utm_source=feed'), 'https://jobs.example.com/apply?gh_jid=42&utm_source=feed')

    def test_markdown_delimiters_in_url_are_encoded(self):
        self.assertEqual(safe_application_url('https://jobs.example.com/apply(1)'), 'https://jobs.example.com/apply%281%29')

    def test_reject_javascript_url(self):
        self.assertIsNone(safe_application_url('javascript:alert(1)'))

    def test_reject_relative_url(self):
        self.assertIsNone(safe_application_url('/apply/123'))

    def test_reject_credentials(self):
        self.assertIsNone(safe_application_url('https://user:pass@jobs.example.com/'))

    def test_reject_newline_in_url(self):
        self.assertIsNone(safe_application_url('https://jobs.example.com/\n[bad](https://evil.example)'))

    def test_reject_bad_port(self):
        self.assertIsNone(safe_application_url('https://jobs.example.com:99999/'))

    def test_reject_empty(self):
        self.assertIsNone(safe_application_url(''))

    def test_reject_fake_url_with_space(self):
        self.assertIsNone(safe_application_url('https://jobs.example.com/apply bad'))


if __name__ == '__main__':
    unittest.main()
