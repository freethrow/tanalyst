# Article Selection & AI Summary Feature

## Overview

This feature allows users to select articles from any list page (inbox, approved, discarded, search results, etc.) and generate AI-powered summaries of their selections in professional Italian.

## Features

### 1. **Article Selection**

- ✅ Checkbox on every card component across all list pages
- ✅ Visual feedback: selected cards highlighted with primary color ring
- ✅ Persistent storage using browser localStorage
- ✅ Selections persist across page navigation
- ✅ Maximum 50 articles can be selected (configurable)
- ✅ Toast notifications for selection actions

### 2. **Floating Selection Panel**

- ✅ Appears when articles are selected
- ✅ Shows count of selected articles
- ✅ Quick actions:
  - **Generate Summary**: Navigate to summary page
  - **Clear All**: Remove all selections with confirmation
- ✅ Fixed position (bottom-right corner)
- ✅ Visible only for authenticated users

### 3. **Selection Summary Page**

- ✅ List of selected articles with titles
- ✅ Custom prompt input for AI instructions
- ✅ Default prompt optimized for business Italian
- ✅ AI summary generation with loading state
- ✅ Copy to clipboard functionality
- ✅ Real-time AJAX submission

### 4. **AI-Powered Summary Generation**

- ✅ Uses same AI infrastructure as weekly summarizer
- ✅ OpenRouter integration with Claude 3.5 Sonnet
- ✅ Articles organized by sector, then chronologically
- ✅ Includes article titles, key points, and URLs
- ✅ Identifies cross-sector trends
- ✅ Highlights opportunities for Italian businesses
- ✅ Professional business Italian output

## Technical Implementation

### Frontend Components

#### 1. Card Component Enhancement

**File**: `templates/partials/card.html`

```html
<!-- Selection Checkbox -->
<label class="flex items-center cursor-pointer group">
  <input
    type="checkbox"
    class="article-selector"
    data-article-id="{{ article.id }}"
    data-article-title="{{ article.title_it }}"
    onchange="window.ArticleSelection?.toggleArticle(this)"
  />
  <span class="ml-2 text-xs">Select</span>
</label>
```

#### 2. JavaScript Selection Manager

**File**: `static/js/article-selection.js`

**Key Features**:

- LocalStorage management for persistent selections
- Automatic checkbox state restoration
- Visual feedback (ring highlighting)
- Toast notifications
- Cross-tab synchronization
- Maximum selection limit enforcement

**Main Methods**:

```javascript
// Toggle article selection
ArticleSelection.toggleArticle(checkbox);

// Get selected article IDs
ArticleSelection.getSelectedIds();

// Get full article data
ArticleSelection.getSelectedArticles();

// Clear all selections
ArticleSelection.clearAllSelections();
```

#### 3. Floating Selection Panel

**File**: `templates/base.html`

- Fixed positioning with z-index 50
- Animated appearance
- Real-time count update
- Primary CTA: "Generate Summary"
- Secondary action: "Clear All"

#### 4. Selection Summary Page

**File**: `templates/selection_summary.html`

**Sections**:

1. Selected articles sidebar (sticky)
2. Summary generation form with custom prompt
3. Loading state with spinner
4. Summary result display with copy button

### Backend Components

#### 1. Views

**File**: `articles/views.py`

##### `selection_summary_view(request)`

- Simple view rendering the summary page template
- Requires authentication

##### `generate_selection_summary(request)`

- POST endpoint for AJAX summary generation
- Parses article IDs from JSON
- Validates selections
- Calls AI generation function
- Returns JSON response with summary

##### `generate_ai_summary_for_selection(articles, custom_prompt)`

- Core AI summary generation logic
- Groups articles by sector
- Sorts chronologically within sectors
- Builds structured prompt
- Calls OpenRouter AI model
- Returns formatted Italian summary

#### 2. URL Routes

**File**: `articles/urls.py`

```python
path("selection-summary/", views.selection_summary_view, name="selection_summary"),
path("generate-selection-summary/", views.generate_selection_summary, name="generate_selection_summary"),
```

## User Flow

### Selecting Articles

1. User navigates to any article list page (inbox, search, approved, etc.)
2. User clicks checkbox on desired article cards
3. Card highlights with primary color ring
4. Floating panel appears showing selection count
5. Selections persist when navigating to other pages

### Generating Summary

1. User clicks "Generate Summary" in floating panel
2. Redirected to `/articles/selection-summary/`
3. Selected articles listed in sidebar
4. User optionally adds custom instructions
5. User clicks "Generate AI Summary"
6. Loading state displayed
7. AI-generated summary appears
8. User can copy summary to clipboard

### Clearing Selections

- Click "Clear All" in floating panel
- Click "Clear All Selections" on summary page
- Confirmation dialog appears
- All selections removed from localStorage
- UI updates immediately

## AI Prompt Structure

### Default Prompt

```
Riassumi questi articoli in italiano professionale e conciso.

Requisiti:
1. Scrivi in italiano business professionale
2. Organizza per settore, poi cronologicamente
3. Per ogni articolo includi:
   - Titolo e sintesi dei punti chiave
   - URL fonte
4. Identifica tendenze trasversali tra i settori
5. Evidenzia opportunità per aziende italiane

Formato:
## [Nome Settore]

### [Titolo Articolo] (Data)
[Sintesi concisa dei punti chiave]
Fonte: [URL]

---

## Tendenze Principali
[Analisi delle tendenze comuni tra gli articoli]

## Opportunità per l'Italia
[Analisi delle opportunità per le aziende italiane]
```

### Article Data Provided

For each article, the AI receives:

- Title (Italian or English)
- Content (first 500 characters)
- Publication date
- Source name
- Full URL
- Sector classification

## Configuration

### Environment Variables

```bash
# AI Model Configuration
LLM_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Constants

```javascript
// In article-selection.js
const STORAGE_KEY = "selected_articles";
const MAX_SELECTIONS = 50;
```

## Data Storage

### LocalStorage Schema

```json
{
  "article_id_1": {
    "id": "article_id_1",
    "title": "Article Title",
    "selectedAt": "2024-12-08T12:00:00.000Z"
  },
  "article_id_2": {
    "id": "article_id_2",
    "title": "Another Article",
    "selectedAt": "2024-12-08T12:05:00.000Z"
  }
}
```

## API Endpoints

### POST `/articles/generate-selection-summary/`

**Request**:

```json
{
  "article_ids": "[\"id1\", \"id2\", \"id3\"]",
  "custom_prompt": "Optional custom instructions"
}
```

**Success Response** (200):

```json
{
  "success": true,
  "summary": "AI-generated summary text...",
  "article_count": 3
}
```

**Error Response** (400/404/500):

```json
{
  "success": false,
  "error": "Error message"
}
```

## UI/UX Features

### Visual Feedback

- ✅ Selected cards: primary color ring (2px)
- ✅ Checkbox hover: subtle scale animation
- ✅ Toast notifications: colored by type (success/error/info)
- ✅ Loading spinner: animated SVG
- ✅ Button states: disabled during loading

### Responsive Design

- ✅ Mobile: Stacked layout
- ✅ Tablet: 2-column grid
- ✅ Desktop: 3-column grid + sidebar
- ✅ Floating panel: Adapts to screen size

### Accessibility

- ✅ Semantic HTML
- ✅ ARIA labels on interactive elements
- ✅ Keyboard navigation support
- ✅ Focus indicators
- ✅ Screen reader compatible

## Error Handling

### Frontend

- No selections: Show empty state message
- Network error: Toast notification
- Loading timeout: Error state with retry option
- Invalid response: User-friendly error message

### Backend

- Missing article IDs: 400 Bad Request
- Invalid JSON: 400 Bad Request
- Articles not found: 404 Not Found
- AI generation failure: 500 Internal Server Error
- Missing API key: Configuration error

## Performance Considerations

### LocalStorage

- Lightweight data structure (ID + title only)
- No heavy article content stored
- Automatic cleanup on clear

### AI Generation

- Articles grouped efficiently by sector
- Content truncated to 500 chars per article
- Single AI call for entire selection
- Async processing with loading state

### UI Updates

- Debounced checkbox events
- Efficient DOM manipulation
- CSS transitions for smooth animations
- Lazy loading of summary content

## Future Enhancements

### Potential Features

- [ ] Export summary as PDF
- [ ] Email summary functionality
- [ ] Save summaries to database
- [ ] Share summaries with team
- [ ] Selection folders/categories
- [ ] Bulk article operations (approve/discard)
- [ ] Summary comparison view
- [ ] Multi-language summary generation
- [ ] Summary style templates
- [ ] Article annotation in summaries

### Technical Improvements

- [ ] IndexedDB for larger selections
- [ ] Service worker for offline support
- [ ] WebSocket for real-time updates
- [ ] Progress indicator for AI generation
- [ ] Batch processing for large selections
- [ ] Caching of generated summaries

## Testing Checklist

### Manual Testing

- [ ] Select/deselect articles on all list pages
- [ ] Verify localStorage persistence
- [ ] Test max selection limit (50 articles)
- [ ] Generate summary with default prompt
- [ ] Generate summary with custom prompt
- [ ] Test copy to clipboard
- [ ] Clear all selections
- [ ] Navigate between pages with selections
- [ ] Test on mobile/tablet/desktop
- [ ] Test with different article counts (1, 10, 50)

### Edge Cases

- [ ] Empty selection state
- [ ] Single article selection
- [ ] Maximum selections (50)
- [ ] Articles with missing data (no date, no sector)
- [ ] Very long article titles
- [ ] Special characters in content
- [ ] Network failure during generation
- [ ] Multiple tabs with selections

## Troubleshooting

### Selection not persisting

**Cause**: LocalStorage disabled or full
**Solution**: Check browser settings, clear old data

### AI summary not generating

**Cause**: Missing API key or invalid configuration
**Solution**: Check `.env` file for `OPENROUTER_API_KEY`

### Checkbox not appearing

**Cause**: JavaScript not loaded
**Solution**: Check browser console, verify `article-selection.js` loaded

### Floating panel not showing

**Cause**: User not authenticated or no selections
**Solution**: Login and select at least one article

## Dependencies

### Python Packages

- `pydantic-ai`: AI agent framework
- `openai`: OpenAI API client (via OpenRouter)
- Django 4.x+

### JavaScript

- Vanilla JavaScript (no frameworks)
- Browser APIs: LocalStorage, Fetch

### CSS

- Tailwind CSS for styling
- Custom animations and transitions

## Files Modified/Created

### Created

- `static/js/article-selection.js` - Selection management
- `templates/selection_summary.html` - Summary page
- `ARTICLE_SELECTION_FEATURE.md` - This documentation

### Modified

- `templates/partials/card.html` - Added checkbox
- `templates/base.html` - Added floating panel + JS include
- `articles/views.py` - Added summary views
- `articles/urls.py` - Added routes
- `CARD_COMPONENT_UNIFICATION.md` - Updated with selection info

## Support & Maintenance

### Monitoring

- Check error logs for AI generation failures
- Monitor localStorage usage across users
- Track API usage and costs
- Review user feedback on summary quality

### Updates

- Keep AI model configuration current
- Update prompt based on user feedback
- Optimize performance as needed
- Add requested features iteratively
