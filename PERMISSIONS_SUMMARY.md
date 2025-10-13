# Role-Based Access Control Summary

## Overview
Implemented role-based access control to restrict certain admin features to staff users only.

## User Roles

### Admin/Staff Users (`user.is_staff` = True)
**Full access to all features including:**
- ✅ Home (Pending articles)
- ✅ Approved articles
- ✅ Discarded articles
- ✅ Sectors
- ✅ Vector Search
- ✅ **Embeddings Management** (Admin only)
- ✅ **Scrapers** (Admin only)
- ✅ **Translation Service** (Admin only)
- ✅ **Weekly Summaries** (Admin only)
- ✅ **Email Sending** (Admin only)

### Regular Users (`user.is_staff` = False)
**Limited access to:**
- ✅ Home (Pending articles)
- ✅ Approved articles
- ✅ Discarded articles
- ✅ Sectors
- ✅ Vector Search
- ❌ Embeddings Management (Hidden from menu & blocked)
- ❌ Scrapers (Hidden from menu & blocked)
- ❌ Translation Service (Hidden from menu & blocked)
- ❌ Weekly Summaries (Hidden from menu & blocked)
- ❌ Email Sending (Hidden from menu & blocked)

## Implementation Details

### Custom Mixins and Decorators

**`StaffRequiredMixin`** - For class-based views
- Extends `LoginRequiredMixin` and `UserPassesTestMixin`
- Checks `is_staff()` in `test_func()`
- Shows translated error message in `handle_no_permission()`
- Redirects to home page with error message

**`staff_required`** - Decorator for function-based views
- Wraps `@login_required` functionality
- Checks `is_staff()` before allowing access
- Shows translated error message if unauthorized
- Redirects to home page

### Error Messages
When non-staff users try to access admin-only pages:
- **English**: "This action can only be performed by an administrator"
- **Italian**: "Questa azione richiede un amministratore"

Messages are properly translated using Django's `gettext` system.

### View Protection
All admin-only views are protected with `@staff_required` decorator or `StaffRequiredMixin`:

**Function-based views:**
- `generate_summary()`
- `remove_all_embeddings()`
- `embedding_management()`
- `scrapers_view()`
- `trigger_scraper()`
- `translation_service_view()`
- `trigger_translation()`
- `reset_all_articles_to_pending()`

**Class-based views:**
- `SendArticlesEmailView` - Uses `StaffRequiredMixin`
- `generate_pdf_report()` - Uses `@staff_required` decorator
- `test_tasks()` - Uses `@staff_required` decorator

### Template Updates
**File:** `templates/base.html`

Added `{% if user.is_staff %}` conditionals around admin-only menu items in:
1. **Desktop Navigation** (lines 264-286)
   - Embeddings, Scrapers, Translation (Tools dropdown)
   - Summaries, Email (top-level links)

2. **Mobile Navigation** (lines 394-413)
   - Same restrictions for mobile menu

### Security
- If a non-staff user tries to access an admin-only URL directly, they will be **redirected to home with an error message**
- Error message is displayed in the user's selected language (English/Italian)
- Menu items are hidden from non-staff users (better UX)
- All existing `@login_required` protections remain in place

### Translation Files
**Files Updated:**
- `locale/en/LC_MESSAGES/django.po` - English translation
- `locale/it/LC_MESSAGES/django.po` - Italian translation

After editing, run:
```bash
python manage.py compilemessages
```

## Testing Access Control

### As Admin:
```python
# In Django shell or admin panel, ensure user is staff:
user = User.objects.get(username='admin_username')
user.is_staff = True
user.save()
```

### As Regular User:
```python
# In Django shell or admin panel, make user non-staff:
user = User.objects.get(username='regular_username')
user.is_staff = False
user.save()
```

Then test accessing:
- `/embedding-management/` → Admin: ✅ Regular: ❌
- `/scrapers/` → Admin: ✅ Regular: ❌
- `/translation-service/` → Admin: ✅ Regular: ❌
- `/weekly-summaries/` → Admin: ✅ Regular: ❌
- `/invia-email/` → Admin: ✅ Regular: ❌

## Helper Function
The `is_staff()` helper function in `views.py` checks both:
```python
def is_staff(user):
    return user.is_staff or user.is_superuser
```

This ensures both staff members and superusers have admin access.
