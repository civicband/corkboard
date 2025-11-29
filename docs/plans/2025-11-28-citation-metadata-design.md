# Citation Metadata Design

## Problem Statement

Researchers using CivicBand data need an easy way to cite meeting pages in their work. Currently, there's no structured metadata for citation tools like Zotero, and no visible citation guidance for users.

## Solution Overview

Add Dublin Core meta tags for citation tool compatibility and a visible "Cite this" section on meeting row pages.

### Design Decisions

1. **Document type:** Meeting minutes/hearing transcript (not "government document" since CivicBand is an archive, not the original source)
2. **Citation scope:** Meeting-level citations with page as a detail (not individual page citations)
3. **Attribution:** Municipality as author, CivicBand as publisher/archive
4. **Metadata format:** Dublin Core only (simple, broad compatibility, better fit than Highwire Press for non-academic documents)
5. **Visible citation:** Single generic format that researchers can adapt to their required style

## Implementation Details

### 1. Dublin Core Meta Tags

Add to `{% block extra_head %}` in row templates:

```html
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
```

### 2. Visible "Cite This" Section

Add after "View surrounding pages" link, before action menu:

```html
<details class="cite-this">
    <summary>Cite this page</summary>
    <div class="cite-content">
        <p class="citation-text" id="citation-{{ primary_key_values[0] }}">
            {{ site_name }}. "{{ rows[0].meeting }} {{ table|title }}." {{ rows[0].date }}, page {{ rows[0].page }}. CivicBand Archive. Accessed <span class="access-date"></span>. https://{{ subdomain }}.civic.band{{ request.path }}
        </p>
        <button class="copy-citation" onclick="navigator.clipboard.writeText(this.previousElementSibling.textContent.trim())">Copy citation</button>
    </div>
</details>
<script>
document.querySelector('#citation-{{ primary_key_values[0] }} .access-date').textContent =
    new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
</script>
```

### 3. Styling

```css
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
```

## Files to Modify

- `templates/datasette/row-meetings-minutes.html`
- `templates/datasette/row-meetings-agendas.html`

## Example Citation Output

> City of Alameda. "City Council Minutes." 2024-01-15, page 3. CivicBand Archive. Accessed November 28, 2025. https://alameda.ca.civic.band/meetings/minutes/abc123

## Future Enhancements (if requested)

- Additional citation formats (APA, MLA, Chicago)
- BibTeX export
- COinS for additional tool compatibility
