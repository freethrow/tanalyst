# User Management Guide

## Overview

The application now requires authentication. All routes are protected and require users to log in.

## User Roles

1. **Regular Users**: Can view and edit articles, access all standard features
2. **Admin Users (Staff)**: Have access to additional admin-only features:
   - Embedding management
   - Weekly summary generation
   - Background task triggers
   - Reset articles to pending

## Creating Users

### Using Django Management Command

We've created a custom management command to easily create users:

#### Create a Regular User
```bash
python manage.py createuser <username> <password>
```

Example:
```bash
python manage.py createuser john mypassword123
```

#### Create an Admin User
```bash
python manage.py createuser <username> <password> --admin
```

Example:
```bash
python manage.py createuser admin admin123 --admin
```

#### Create User with Email
```bash
python manage.py createuser john mypassword123 --email john@example.com
```

### Using Django Admin

Alternatively, you can use Django's built-in admin interface:

```bash
python manage.py createsuperuser
```

Then access `/admin/` and log in to create additional users.

## Protected Routes

### All Users (Login Required)
- **Home page** (`/`): View pending articles
- **Approved** (`/approved/`): View approved articles
- **Discarded** (`/discarded/`): View discarded articles
- **Article detail** (`/article/<id>/`): View article details
- **Article edit** (`/article/<id>/edit/`): Edit articles
- **Sectors** (`/settori/`): View all sectors
- **Sector detail** (`/settori/<sector>/`): View sector articles
- **Vector Search** (`/vector-search/`): Search articles
- **Weekly Summaries** (`/weekly-summaries/`): View summaries
- **Send Email** (`/invia-email/`): Send article emails
- **Validate/Discard/Restore** articles (HTMX actions)

### Admin Only (Staff Required)
- **Embedding Management** (`/embedding-management/`): Manage vector embeddings
- **Remove Embeddings** (`/remove-embeddings/`): Clear all embeddings
- **Generate Summary** (`/generate-summary/`): Trigger weekly summary
- **Test Tasks** (`/test-tasks/`): Trigger background tasks
- **Reset Pending** (`/reset-pending/`): Reset all articles to pending

## Login Page

Access the login page at: `/login/`

The login page features:
- Modern, clean design
- Error messages for invalid credentials
- Redirect to original destination after login
- "Remember me" functionality

## Logout

Users can log out by:
1. Clicking their username in the top-right navigation
2. Selecting "Sign Out" from the dropdown menu

## Security Features

1. **Authentication Required**: All routes require login except `/login/`
2. **Role-Based Access**: Admin features restricted to staff users
3. **Automatic Redirects**: Unauthenticated users redirected to login
4. **Session Management**: Secure session handling
5. **CSRF Protection**: All forms protected against CSRF attacks

## User Interface

### Navigation Bar
- Shows username with "Admin" badge for staff users
- User menu dropdown with sign-out option
- Language switcher
- Mobile responsive

### Admin Features
Admin users see additional menu items and can access:
- Background task management
- Embedding operations
- System configuration

## Example User Creation Workflow

```bash
# 1. Create an admin user for yourself
python manage.py createuser admin MySecurePassword123 --admin --email admin@example.com

# 2. Create regular users for team members
python manage.py createuser editor1 Password123 --email editor1@example.com
python manage.py createuser editor2 Password456 --email editor2@example.com

# 3. Test login at http://localhost:8000/login/
```

## Troubleshooting

### Can't Access Any Pages
- Make sure you're logged in at `/login/`
- Check that user account exists and is active

### Can't Access Admin Features
- Only staff/superuser accounts can access admin features
- Create user with `--admin` flag or set `is_staff=True` in Django admin

### Forgotten Password
Currently, password reset is not implemented. Admins can reset passwords via:
```bash
python manage.py changepassword <username>
```

## Next Steps

Consider implementing:
- Password reset functionality
- Email verification
- Two-factor authentication
- User profile pages
- Activity logging
