# Citation Metadata Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Dublin Core meta tags and a visible "Cite this" section to meeting row pages so researchers can easily cite CivicBand data.

**Architecture:** Modify the row templates for minutes and agendas to add Dublin Core meta tags in the head block and a collapsible "Cite this" section in the content block. Use JavaScript for the access date and copy-to-clipboard functionality.

**Tech Stack:** Jinja2 templates, HTML meta tags, vanilla JavaScript, CSS

---

## Task 1: Add Dublin Core Meta Tags to Minutes Template

**Files:**
- Modify: `templates/datasette/row-meetings-minutes.html`

**Step 1: Add extra_head block with Dublin Core tags**

The current template extends `default:row.html` but doesn't override `extra_head`. Add the block at the top of the file, after the extends statement.

Open `templates/datasette/row-meetings-minutes.html` and add after line 1 (`{% extends "default:row.html" %}`):

```html
{% block extra_head %}
<!-- Dublin Core metadata for citation tools -->
<meta name="DC.title" content="{{ rows[0].meeting }} {{ table|title }}, {{ rows[0].date }}">
<meta name="DC.creator" content="{{ site_name }}">
<meta name="DC.publisher" content="CivicBand Archive">
<meta name="DC.date" content="{{ rows[0].date }}">
<meta name="DC.type" content="Text">
<meta name="DC.format" content="text/html">
<meta name="DC.identifier" content="https://{{ subdomain }}.civic.band{{ request.path }}">
<meta name="DC.source" content="{{ site_name }}">
<meta name="DC.language" content="en">
{% endblock %}
```

**Step 2: Verify the template still renders**

Run: `just serve`

Visit a minutes row page (e.g., http://localhost:8001/meetings/minutes/some-id) and view page source to confirm Dublin Core tags are present.

**Step 3: Commit**

```bash
git add templates/datasette/row-meetings-minutes.html
git commit -m "feat: add Dublin Core meta tags to minutes row template"
```

---

## Task 2: Add Dublin Core Meta Tags to Agendas Template

**Files:**
- Modify: `templates/datasette/row-meetings-agendas.html`

**Step 1: Add extra_head block with Dublin Core tags**

Open `templates/datasette/row-meetings-agendas.html` and add after line 1 (`{% extends "default:row.html" %}`):

```html
{% block extra_head %}
<!-- Dublin Core metadata for citation tools -->
<meta name="DC.title" content="{{ rows[0].meeting }} {{ table|title }}, {{ rows[0].date }}">
<meta name="DC.creator" content="{{ site_name }}">
<meta name="DC.publisher" content="CivicBand Archive">
<meta name="DC.date" content="{{ rows[0].date }}">
<meta name="DC.type" content="Text">
<meta name="DC.format" content="text/html">
<meta name="DC.identifier" content="https://{{ subdomain }}.civic.band{{ request.path }}">
<meta name="DC.source" content="{{ site_name }}">
<meta name="DC.language" content="en">
{% endblock %}
```

**Step 2: Verify the template still renders**

Run: `just serve`

Visit an agendas row page and view page source to confirm Dublin Core tags are present.

**Step 3: Commit**

```bash
git add templates/datasette/row-meetings-agendas.html
git commit -m "feat: add Dublin Core meta tags to agendas row template"
```

---

## Task 3: Add "Cite This" Section to Minutes Template

**Files:**
- Modify: `templates/datasette/row-meetings-minutes.html`

**Step 1: Add the cite-this section**

In `templates/datasette/row-meetings-minutes.html`, find the section after the "View surrounding pages" link (around line 12, after `{% endif %}`). Add the following before the action menu line (`{% set action_links, action_title = row_actions, "Row actions" %}`):

```html
{% if rows and rows[0].meeting and rows[0].date %}
<details class="cite-this">
    <summary>Cite this page</summary>
    <div class="cite-content">
        <p class="citation-text" id="citation-minutes-{{ primary_key_values[0] }}">
            {{ site_name }}. "{{ rows[0].meeting }} {{ table|title }}." {{ rows[0].date }}, page {{ rows[0].page }}. CivicBand Archive. Accessed <span class="access-date"></span>. https://{{ subdomain }}.civic.band{{ request.path }}
        </p>
        <button class="copy-citation" onclick="navigator.clipboard.writeText(document.getElementById('citation-minutes-{{ primary_key_values[0] }}').textContent.trim()).then(() => { this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy citation', 2000); })">Copy citation</button>
    </div>
</details>
<script>
document.querySelector('#citation-minutes-{{ primary_key_values[0] }} .access-date').textContent =
    new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
</script>
{% endif %}
```

**Step 2: Add the CSS styling**

Add a style block at the end of the file, before `{% endblock %}`:

```html
<style>
.cite-this {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    margin: 0.75rem 0;
    font-size: 0.9rem;
}

.cite-this summary {
    cursor: pointer;
    font-weight: 500;
    color: #495057;
}

.cite-this[open] summary {
    margin-bottom: 0.5rem;
}

.cite-content {
    padding: 0.5rem 0;
}

.citation-text {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 0.75rem;
    margin: 0 0 0.5rem 0;
    font-family: Georgia, serif;
    line-height: 1.5;
}

.copy-citation {
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
    cursor: pointer;
}

.copy-citation:hover {
    background: #0056b3;
}
</style>
```

**Step 3: Verify the cite section renders and works**

Run: `just serve`

Visit a minutes row page:
1. Confirm "Cite this page" appears as a collapsed section
2. Click to expand and verify the citation text includes the meeting name, date, page, and today's date
3. Click "Copy citation" and paste to verify it copied correctly

**Step 4: Commit**

```bash
git add templates/datasette/row-meetings-minutes.html
git commit -m "feat: add visible 'Cite this' section to minutes row template"
```

---

## Task 4: Add "Cite This" Section to Agendas Template

**Files:**
- Modify: `templates/datasette/row-meetings-agendas.html`

**Step 1: Add the cite-this section**

In `templates/datasette/row-meetings-agendas.html`, find the section after the "View surrounding pages" link. Add the following before the action menu line:

```html
{% if rows and rows[0].meeting and rows[0].date %}
<details class="cite-this">
    <summary>Cite this page</summary>
    <div class="cite-content">
        <p class="citation-text" id="citation-agendas-{{ primary_key_values[0] }}">
            {{ site_name }}. "{{ rows[0].meeting }} {{ table|title }}." {{ rows[0].date }}, page {{ rows[0].page }}. CivicBand Archive. Accessed <span class="access-date"></span>. https://{{ subdomain }}.civic.band{{ request.path }}
        </p>
        <button class="copy-citation" onclick="navigator.clipboard.writeText(document.getElementById('citation-agendas-{{ primary_key_values[0] }}').textContent.trim()).then(() => { this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy citation', 2000); })">Copy citation</button>
    </div>
</details>
<script>
document.querySelector('#citation-agendas-{{ primary_key_values[0] }} .access-date').textContent =
    new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
</script>
{% endif %}
```

**Step 2: Add the CSS styling**

Add the same style block at the end of the file, before `{% endblock %}`:

```html
<style>
.cite-this {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    margin: 0.75rem 0;
    font-size: 0.9rem;
}

.cite-this summary {
    cursor: pointer;
    font-weight: 500;
    color: #495057;
}

.cite-this[open] summary {
    margin-bottom: 0.5rem;
}

.cite-content {
    padding: 0.5rem 0;
}

.citation-text {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 0.75rem;
    margin: 0 0 0.5rem 0;
    font-family: Georgia, serif;
    line-height: 1.5;
}

.copy-citation {
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
    cursor: pointer;
}

.copy-citation:hover {
    background: #0056b3;
}
</style>
```

**Step 3: Verify the cite section renders and works**

Run: `just serve`

Visit an agendas row page and verify the same functionality as minutes.

**Step 4: Commit**

```bash
git add templates/datasette/row-meetings-agendas.html
git commit -m "feat: add visible 'Cite this' section to agendas row template"
```

---

## Task 5: Final Verification

**Files:**
- Review: All modified templates

**Step 1: Run linting**

Run: `just lint`
Expected: No linting errors (templates aren't linted, but check for any Python issues)

**Step 2: Run tests**

Run: `just test`
Expected: All tests pass (no regressions)

**Step 3: Manual verification checklist**

Run: `just serve`

Verify on a minutes row page:
- [ ] Dublin Core meta tags present in page source
- [ ] "Cite this page" section visible
- [ ] Citation text includes correct meeting name, date, page number
- [ ] "Accessed" date shows today's date
- [ ] "Copy citation" button works and shows "Copied!" feedback

Verify on an agendas row page:
- [ ] Same functionality as minutes

**Step 4: Commit any cleanup if needed**

If any fixes were required:
```bash
git add -A
git commit -m "chore: citation metadata cleanup"
```

---

## Summary

After completing all tasks, you will have:

1. **`templates/datasette/row-meetings-minutes.html`** - Modified to include:
   - Dublin Core meta tags in `extra_head` block
   - Collapsible "Cite this" section with copy button
   - CSS styling for the citation section

2. **`templates/datasette/row-meetings-agendas.html`** - Modified with same changes

**Example citation output:**
> City of Alameda. "City Council Minutes." 2024-01-15, page 3. CivicBand Archive. Accessed November 28, 2025. https://alameda.ca.civic.band/meetings/minutes/abc123
