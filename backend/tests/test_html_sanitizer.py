from app.sources.html_sanitizer import sanitize_job_html


def test_preserves_semantic_structure_from_double_encoded_greenhouse_html():
    raw = (
        "&amp;lt;h2&amp;gt;Requirements&amp;lt;/h2&amp;gt;"
        "&amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;Python &amp;amp; SQL&amp;lt;/li&amp;gt;&amp;lt;/ul&amp;gt;"
    )

    assert sanitize_job_html(raw, decode_markup=True) == (
        "<h2>Requirements</h2><ul><li>Python &amp; SQL</li></ul>"
    )


def test_resanitizing_stored_html_is_idempotent_for_encoded_literal_text():
    stored = "<p>Use &lt;Widget&gt; &amp; review the result.</p>"

    assert sanitize_job_html(stored) == stored
    assert sanitize_job_html(sanitize_job_html(stored)) == stored


def test_drops_executable_embedded_and_provider_styling_content():
    raw = (
        '<h2 class="hero" style="color:red" onclick="steal()">Role</h2>'
        '<script>alert("xss")</script><style>body{display:none}</style>'
        '<p><img src="https://tracker.test/pixel">Safe <strong>content</strong></p>'
        '<iframe src="https://evil.test">hidden frame text</iframe>'
    )

    assert sanitize_job_html(raw) == (
        "<h2>Role</h2><p>Safe <strong>content</strong></p>"
    )


def test_keeps_only_explicitly_safe_link_protocols():
    raw = (
        '<a href="https://example.com/job" onclick="steal()">Safe</a>'
        '<a href="javascript:alert(1)">Unsafe</a>'
        '<a href="//evil.test/path">Protocol relative</a>'
    )

    assert sanitize_job_html(raw) == (
        '<a href="https://example.com/job" target="_blank" '
        'rel="noopener noreferrer nofollow">Safe</a>'
        "<a>Unsafe</a><a>Protocol relative</a>"
    )


def test_handles_empty_non_string_and_malformed_values_without_raising():
    assert sanitize_job_html(None) == ""
    assert sanitize_job_html({"html": "<p>no</p>"}) == ""
    assert sanitize_job_html("<h2>Unclosed") == "<h2>Unclosed"


def test_legacy_plain_text_with_comparison_symbols_remains_visible_and_safe():
    assert sanitize_job_html("Use 5 < 10 and 10 > 5") == (
        "Use 5 &lt; 10 and 10 &gt; 5"
    )
