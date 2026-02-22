# Homepage UX Improvements Design

**Date:** 2026-02-20
**Status:** Approved

## Problem Statement

The current homepage has several UX issues:
- No GitHub link despite being an open-source project
- Newsletter signup form lacks context (doesn't explain it's for newsletter updates)
- Doesn't clearly explain what's available on municipality sites
- Campaign finance data feature isn't prominently visible

## User Priorities

First-time visitors should be able to (in order):
1. Browse/search municipalities
2. Visit a municipality site
3. Learn about the project
4. Sign up for newsletter

## Design Approach

**Selected: Minimal Touch-up**

This approach addresses all concerns while preserving the search-first UX. Changes are strategic additions of context where it's missing, rather than a full redesign.

### 1. Navigation Enhancement

**Location:** Top navigation bar (after RSS Feed, before social links)

**Change:** Add GitHub link
- Text: "GitHub"
- URL: `https://github.com/civicband/corkboard`
- Style: Consistent with other nav links (gray text, hover effects)
- Analytics: `data-umami-event="homepage_nav" data-umami-event-target="github"`

### 2. Feature Explanation

**Location:** Between main description paragraph and newsletter form

**Change:** Add 2-bullet list explaining what's available
- "**Meeting minutes & agendas:** Searchable text from council meetings, planning boards, and other municipal bodies"
- "**Campaign finance data:** Contribution and spending records for select municipalities"

**Style:** Small, concise, visually lightweight using existing Tailwind classes

### 3. Newsletter Section Restructure

**Location:** Current newsletter form area

**Changes:**
- Add heading: "Stay Updated"
- Add description: "Get updates when we add new municipalities and features"
- Keep existing form structure, validation, and privacy policy link
- Increase visual separation from content above

### 4. Finance Data Visibility

**Location:** Municipality table rows

**Change:** Add visual badge for sites with campaign finance data
- Badge text: "Finance data" or icon
- Condition: Show when `site.has_finance_data=True`
- Style: Small, subtle badge next to municipality name
- Enhancement: Consider tooltip explaining what finance data includes

## Implementation Notes

- All changes are in `templates/pages/home.html`
- No backend/view changes needed (data already available)
- Maintain existing analytics tracking patterns
- Preserve HTMX functionality for search/filters
- Keep mobile-responsive design

## Trade-offs

**Pros:**
- Minimal disruption to working search-first UX
- Quick to implement
- Addresses all identified issues
- Low risk

**Cons:**
- Doesn't radically improve information architecture
- Header area still fairly dense
- Could iterate to more substantial redesign later if needed

## Success Criteria

- GitHub link visible and clickable in navigation
- Users understand newsletter signup is for project updates
- First-time visitors understand what data is available (meetings vs. finance)
- Users can identify which municipalities have campaign finance data
