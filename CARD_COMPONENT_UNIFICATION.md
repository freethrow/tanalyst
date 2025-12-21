# Card Component Unification - Implementation Summary

## Overview

Successfully unified all article list displays across the application to use a single, flexible card component (`partials/card.html`).

## Changes Made

### 1. Enhanced Card Component (`templates/partials/card.html`)

The card component now supports two display modes:

#### **Regular Mode** (Default)

- Shows article status badges (Pending, Approved, Discarded, Sent)
- Displays full action buttons (Approve, Discard, Restore, Edit, Read)
- Shows score and rank when available
- Includes status-based border colors (left border)

#### **Search Mode** (`search_mode=True`)

- Shows search type badges (Hybrid, Semantic, Keyword) instead of status badges
- Displays rank and relevance score prominently
- Shows hybrid metadata (vector_rank, text_rank) for hybrid search results
- Simplified action section with only "View Article" button
- No approve/discard/edit actions

### 2. Updated Search Results (`templates/partials/hybrid_search_results.html`)

- **Before**: Custom card markup (~100 lines of duplicate code)
- **After**: Single line include of card component with `search_mode=True`
- Maintains all search-specific features (badges, ranks, hybrid metadata)
- Consistent styling with other list pages

### 3. Verified Pages Using Card Component

All article list pages now use the unified card component:

| Page           | Route                | Template                     | Status                |
| -------------- | -------------------- | ---------------------------- | --------------------- |
| Home/Inbox     | `/`                  | `index.html`                 | ✅ Already using card |
| Approved       | `/approved/`         | `index.html`                 | ✅ Already using card |
| Discarded      | `/discarded/`        | `index.html`                 | ✅ Already using card |
| Sent           | `/sent/`             | `index.html`                 | ✅ Already using card |
| All Articles   | `/all/`              | `index.html`                 | ✅ Already using card |
| Sector Detail  | `/settori/<sector>/` | `sector_detail.html`         | ✅ Already using card |
| Search Results | `/hybrid-search/`    | `hybrid_search_results.html` | ✅ **Now using card** |

## Card Component Features

### Common Features (Both Modes)

- ✅ Title with link to article detail
- ✅ Content preview (first 200 characters)
- ✅ Metadata display (date, sector, source, URL)
- ✅ Responsive grid layout (1 col mobile, 2 cols tablet, 3 cols desktop)
- ✅ Hover effects and transitions
- ✅ Clean, modern design with Tailwind CSS

### Search Mode Specific

- ✅ Search type badge (Hybrid/Semantic/Keyword) with distinct colors
  - **Purple** for Hybrid
  - **Blue** for Semantic
  - **Green** for Keyword
- ✅ Search rank display (#1, #2, etc.)
- ✅ Relevance score percentage
- ✅ Hybrid metadata showing individual search ranks:
  - Semantic rank (from vector search)
  - Keyword rank (from text search)
- ✅ Streamlined actions (View Article only)

### Regular Mode Specific

- ✅ Status badges (Pending/Approved/Discarded/Sent)
- ✅ Status-based left border colors
- ✅ Full action buttons based on status:
  - **Pending**: Approve, Discard, Edit, Read
  - **Approved**: Edit, Read
  - **Discarded**: Restore, Edit, Read
  - **Sent**: Restore as Pending, Edit, Read
- ✅ HTMX-powered actions with smooth animations

## Usage Examples

### Regular Article List

```django
{% for article in articles %}
  {% include "partials/card.html" with article=article %}
{% endfor %}
```

### Search Results

```django
{% for result in results %}
  {% include "partials/card.html" with article=result search_mode=True %}
{% endfor %}
```

## Benefits

1. **DRY Principle**: Eliminated ~100 lines of duplicate card markup
2. **Consistency**: All article cards look and behave the same way
3. **Maintainability**: Single source of truth for card design
4. **Flexibility**: Easy to add new features to all cards at once
5. **Search Integration**: Seamless integration of search-specific features
6. **Performance**: Cleaner HTML, less code to parse

## Technical Details

### Key Template Variables

- `article`: The article object to display
- `search_mode`: Boolean flag to enable search mode (default: False)
- `article.search_type`: Type of search used ('hybrid', 'vector', 'text')
- `article.rank`: Search result rank
- `article.score`: Relevance score (0-100)
- `article.vector_rank`: Semantic search rank (hybrid only)
- `article.text_rank`: Keyword search rank (hybrid only)
- `article.status`: Article status ('PENDING', 'APPROVED', 'DISCARDED', 'SENT')

### Conditional Logic

The card component uses Django template conditionals to:

- Show/hide elements based on mode
- Display appropriate badges
- Adjust button layout
- Show hybrid metadata when relevant

## Testing Recommendations

1. **Visual Testing**: Verify cards display correctly on:

   - Home page (pending articles)
   - Approved articles page
   - Discarded articles page
   - Sent articles page
   - All articles page
   - Sector detail pages
   - Search results page (all 3 modes: hybrid, semantic, keyword)

2. **Functional Testing**:

   - Article actions (approve, discard, restore)
   - Edit and read links
   - HTMX card removal animations
   - Search type badges display correctly
   - Hybrid metadata shows for hybrid results only

3. **Responsive Testing**: Test on:
   - Mobile (1 column)
   - Tablet (2 columns)
   - Desktop (3 columns)

## Future Enhancements

Potential improvements to consider:

- Add filtering options in card header
- Include article thumbnail/image support
- Add bulk selection mode
- Implement card flip animation for more details
- Add export/share options per card
