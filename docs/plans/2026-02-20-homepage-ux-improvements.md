# Homepage UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve homepage UX by adding GitHub link, explaining available features, clarifying newsletter signup, and enhancing finance data visibility.

**Architecture:** Template-only changes to `templates/pages/home.html`. No backend changes needed. Maintain existing HTMX functionality and responsive design.

**Tech Stack:** Django templates, Tailwind CSS, existing analytics setup

---

## Task 1: Add GitHub Link to Navigation

**Files:**
- Modify: `templates/pages/home.html:8-16`

**Step 1: Locate the navigation section**

Find the navigation `<ul>` element that contains links to "How it works", "Why?", "RSS Feed", etc.

Current location: `templates/pages/home.html:9-16`

**Step 2: Add GitHub link after RSS Feed**

Add the following `<li>` element after the RSS Feed link (after line 12) and before the Mastodon link:

```html
<li><a href="https://github.com/civicband/corkboard" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="github">GitHub</a></li>
```

**Step 3: Test the link**

Run: `just serve`

Visit: `http://localhost:8000`

Expected: GitHub link appears in navigation, opens correct URL, matches style of other nav links

**Step 4: Commit**

```bash
git add templates/pages/home.html
git commit -m "feat: add GitHub link to homepage navigation"
```

---

## Task 2: Add Feature Explanation Section

**Files:**
- Modify: `templates/pages/home.html:19-23`

**Step 1: Locate the description paragraph**

Find the paragraph that starts with "The largest collection of civic meeting data..." (line 22).

**Step 2: Add feature list after the description paragraph**

After the closing `</p>` tag on line 22 and before the newsletter form comment (line 24), add:

```html

      <!-- Feature Explanation -->
      <div class="text-sm text-gray-600 mt-3 space-y-1">
        <p class="font-medium text-gray-700">What you'll find:</p>
        <ul class="list-disc list-inside space-y-0.5 ml-2">
          <li><strong>Meeting minutes & agendas:</strong> Searchable text from council meetings, planning boards, and other municipal bodies</li>
          <li><strong>Campaign finance data:</strong> Contribution and spending records for select municipalities</li>
        </ul>
      </div>
```

**Step 3: Test visual appearance**

Run: `just serve`

Visit: `http://localhost:8000`

Expected: Feature list appears between description and newsletter form, styled consistently, doesn't disrupt layout

**Step 4: Commit**

```bash
git add templates/pages/home.html
git commit -m "feat: add feature explanation to homepage"
```

---

## Task 3: Restructure Newsletter Section with Heading

**Files:**
- Modify: `templates/pages/home.html:24-40`

**Step 1: Locate the newsletter form**

Find the newsletter form comment and form element (lines 24-40).

**Step 2: Replace newsletter form section**

Replace lines 24-40 with:

```html
      <!-- Newsletter Section -->
      <div class="mt-4 pt-3 border-t border-gray-200">
        <h3 class="text-sm font-semibold text-gray-900 mb-1">Stay Updated</h3>
        <p class="text-xs text-gray-600 mb-2">Get updates when we add new municipalities and features</p>
        <form action="https://buttondown.com/api/emails/embed-subscribe/civicband"
              method="post"
              target="popupwindow"
              onsubmit="window.open('https://buttondown.com/civicband', 'popupwindow')"
              class="flex flex-wrap gap-2 items-center">
          <label for="bd-email" class="sr-only">Email address</label>
          <input id="bd-email" name="email" type="email" autocomplete="email" required
                 class="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                 placeholder="Enter your email">
          <button type="submit"
                  class="px-2 py-1 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600 font-medium transition"
                  data-umami-event="homepage_newsletter">Subscribe</button>
          <span class="text-xs text-gray-600">
            We care about your data. Read our <a href="/privacy.html" class="text-indigo-600 hover:text-indigo-800 underline" data-umami-event="homepage_nav" data-umami-event-target="privacy">privacy policy</a>.
          </span>
        </form>
      </div>
```

**Step 3: Test newsletter functionality**

Run: `just serve`

Visit: `http://localhost:8000`

Test:
- Newsletter section has "Stay Updated" heading
- Description explains purpose
- Form still works (test submission flow)
- Privacy policy link still present and working
- Visual separation from content above

**Step 4: Commit**

```bash
git add templates/pages/home.html
git commit -m "feat: add context and structure to newsletter signup"
```

---

## Task 4: Enhance Finance Data Badge with Tooltip

**Files:**
- Modify: `templates/pages/_sites_table_only.html:50-52`

**Step 1: Locate the finance badge**

Find the existing finance badge in the table (lines 50-52).

**Step 2: Enhance the badge styling and tooltip**

Replace the current badge span (line 51) with:

```html
              <span class="inline-flex items-center px-1.5 py-0.5 ml-2 text-xs font-medium bg-green-100 text-green-800 rounded border border-green-200" title="Campaign finance data available: contribution and spending records">Finance data</span>
```

**Step 3: Test badge appearance**

Run: `just serve`

Visit: `http://localhost:8000`

Test:
- Badge appears for municipalities with finance data
- Badge is styled consistently (green, readable)
- Tooltip appears on hover with explanation
- Badge works on mobile (responsive)
- Badge doesn't break table layout

**Step 4: Commit**

```bash
git add templates/pages/_sites_table_only.html
git commit -m "feat: enhance finance data badge with better styling and tooltip"
```

---

## Task 5: Visual Testing and Polish

**Files:**
- Review: `templates/pages/home.html`, `templates/pages/_sites_table_only.html`

**Step 1: Full visual testing**

Run: `just serve`

Visit: `http://localhost:8000`

Test checklist:
- [ ] GitHub link in navigation, correct URL
- [ ] Feature list displays clearly between description and newsletter
- [ ] Newsletter has "Stay Updated" heading and description
- [ ] Finance badges appear on appropriate municipalities
- [ ] All links work and track analytics
- [ ] Mobile responsive (test at 375px, 768px, 1024px widths)
- [ ] No layout breakage

**Step 2: Test search/filter interactions**

Test:
- [ ] Search municipalities - layout stays intact
- [ ] Filter by state - layout stays intact
- [ ] Filter by finance data - badge still visible
- [ ] HTMX updates don't break anything

**Step 3: Browser testing**

Test in:
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari (if on macOS)

**Step 4: Document any issues found**

If issues found, create new commits to fix them before final commit.

**Step 5: Final commit (if polish changes made)**

```bash
git add .
git commit -m "polish: final visual adjustments for homepage UX"
```

---

## Task 6: Create Pull Request

**Files:**
- N/A (Git operations)

**Step 1: Ensure all changes are committed**

Run: `git status`

Expected: "nothing to commit, working tree clean"

**Step 2: Create feature branch if not already on one**

```bash
git checkout -b homepage-ux-improvements
```

**Step 3: Push branch to remote**

```bash
git push -u origin homepage-ux-improvements
```

**Step 4: Create pull request**

```bash
gh pr create --title "Improve homepage UX: GitHub link, feature explanation, newsletter context" --body "$(cat <<'EOF'
## Summary

Addresses homepage UX issues:
- Adds GitHub link to navigation
- Explains available features (meeting data vs. campaign finance)
- Clarifies newsletter signup with heading and description
- Enhances finance data badge visibility with better styling

## Changes

- Added GitHub link to top navigation
- Added "What you'll find" feature list explaining meeting minutes and campaign finance data
- Restructured newsletter form with "Stay Updated" heading and context
- Enhanced finance data badge with improved styling and tooltip

## Testing

- [x] Visual testing on desktop (Chrome, Firefox, Safari)
- [x] Mobile responsive testing (375px, 768px, 1024px)
- [x] Search/filter functionality still works
- [x] All links functional and tracking analytics
- [x] Newsletter form still submits correctly

## Screenshots

[Add screenshots if desired]

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Step 5: Verify PR created**

Expected: PR URL returned, can view PR on GitHub

---

## Notes

- No backend changes required - all context/data already available in templates
- Finance badge already exists in table, just enhancing styling
- All analytics tracking patterns maintained
- HTMX functionality preserved
- Mobile responsive design maintained throughout
