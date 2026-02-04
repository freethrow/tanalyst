"""
Test suite for Activities app views.
Uses Django test runner with MongoDB backend.
The test database uses a separate collection that gets cleared after tests.
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from activities.models import Activity, Todo
from bson import ObjectId
import json


User = get_user_model()


class ActivityTestCase(TestCase):
    """Base test case with common setup for activity tests."""

    def setUp(self):
        self.client = Client()
        # Clean up any activities from previous tests
        Activity.objects.all().delete()

        # Create test users - must be created per test due to MongoDB test database isolation
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='adminpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            password='userpass123'
        )
        self.other_user = User.objects.create_user(
            username='other_test',
            email='other@test.com',
            password='otherpass123'
        )

    def tearDown(self):
        # Clean up activities after each test
        Activity.objects.all().delete()
        # Clean up test users
        User.objects.filter(username__in=['admin_test', 'user_test', 'other_test']).delete()

    def create_test_activity(self, responsabili=None, **kwargs):
        """Helper to create a test activity."""
        defaults = {
            'tipo': Activity.TIPO_PROMOZIONALI_LOCO,
            'mese': '01',
            'anno': 2024,
            'nome_iniziativa': 'Test Initiative',
            'citta': 'Belgrade',
            'settore': 'Technology',
            'descrizione': 'Test description',
            'azione': 'Test action',
            'number_persons': 10,
            'ufficio': Activity.OFFICE_BELGRADO,
        }
        defaults.update(kwargs)

        activity = Activity(**defaults)
        if responsabili:
            # Convert user pks to hex string format for MongoDB ObjectId compatibility
            responsabili_ids = []
            for u in responsabili:
                pk = u.pk
                # Handle both ObjectId objects and already-converted strings
                if hasattr(pk, 'binary'):
                    # It's a bson ObjectId
                    responsabili_ids.append(str(pk))
                else:
                    responsabili_ids.append(str(pk))
            activity.responsabili = responsabili_ids
        activity.save()
        return activity


class ActivityListViewTests(ActivityTestCase):
    """Tests for the activity list view."""

    def test_list_view_anonymous_user(self):
        """Anonymous users can view the activity list."""
        self.create_test_activity()
        response = self.client.get(reverse('activities:activity_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/activity_list.html')

    def test_list_view_authenticated_user(self):
        """Authenticated users can view the activity list."""
        self.client.login(username='user_test', password='userpass123')
        self.create_test_activity()
        response = self.client.get(reverse('activities:activity_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_pagination(self):
        """List view paginates activities correctly."""
        # Create 25 activities (more than the 20 per page limit)
        for i in range(25):
            self.create_test_activity(
                nome_iniziativa=f'Initiative {i}',
                slug=f'initiative-{i}-belgrado-2024'
            )

        response = self.client.get(reverse('activities:activity_list'))
        self.assertEqual(response.status_code, 200)
        # Check pagination exists
        self.assertTrue('page_obj' in response.context)
        self.assertEqual(len(response.context['page_obj']), 20)

    def test_list_view_filter_by_year(self):
        """List view filters by year correctly."""
        self.create_test_activity(anno=2024, slug='activity-2024')
        self.create_test_activity(anno=2023, slug='activity-2023')

        response = self.client.get(reverse('activities:activity_list'), {'anno': '2024'})
        self.assertEqual(response.status_code, 200)
        activities = response.context['page_obj']
        for activity in activities:
            self.assertEqual(activity.anno, 2024)

    def test_list_view_filter_by_office(self):
        """List view filters by office correctly."""
        self.create_test_activity(ufficio=Activity.OFFICE_BELGRADO, slug='activity-belgrado')
        self.create_test_activity(ufficio=Activity.OFFICE_PODGORICA, slug='activity-podgorica')

        response = self.client.get(reverse('activities:activity_list'), {'ufficio': 'Belgrado'})
        self.assertEqual(response.status_code, 200)
        activities = response.context['page_obj']
        for activity in activities:
            self.assertEqual(activity.ufficio, Activity.OFFICE_BELGRADO)

    def test_list_view_filter_by_sector(self):
        """List view filters by sector correctly."""
        self.create_test_activity(settore='Technology', slug='activity-tech')
        self.create_test_activity(settore='Agriculture', slug='activity-agri')

        response = self.client.get(reverse('activities:activity_list'), {'settore': 'Tech'})
        self.assertEqual(response.status_code, 200)
        activities = response.context['page_obj']
        for activity in activities:
            self.assertIn('Tech', activity.settore)

    def test_list_view_my_activities_filter(self):
        """List view filters to show only user's activities."""
        self.client.login(username='user_test', password='userpass123')

        # Create an activity where user is responsible
        self.create_test_activity(
            responsabili=[self.regular_user],
            slug='my-activity'
        )
        # Create an activity where user is NOT responsible
        self.create_test_activity(
            responsabili=[self.other_user],
            slug='other-activity'
        )

        response = self.client.get(reverse('activities:activity_list'), {'my_activities': '1'})
        self.assertEqual(response.status_code, 200)
        activities = list(response.context['page_obj'])
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].slug, 'my-activity')


class ActivityDetailViewTests(ActivityTestCase):
    """Tests for the activity detail view."""

    def test_detail_view_anonymous_user(self):
        """Anonymous users can view activity details."""
        activity = self.create_test_activity()
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/activity_detail.html')

    def test_detail_view_authenticated_user(self):
        """Authenticated users can view activity details."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity()
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_nonexistent_activity(self):
        """Viewing a non-existent activity returns 404."""
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': 'nonexistent-slug'})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_view_shows_responsabili(self):
        """Detail view shows responsible users."""
        activity = self.create_test_activity(responsabili=[self.regular_user])
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('responsabili_users' in response.context)

    def test_detail_view_can_edit_for_responsabile(self):
        """Responsabile user has edit permission shown."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_edit'])

    def test_detail_view_can_edit_for_admin(self):
        """Admin user has edit permission shown."""
        self.client.login(username='admin_test', password='adminpass123')
        activity = self.create_test_activity(responsabili=[self.other_user])
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_edit'])

    def test_detail_view_cannot_edit_for_non_responsabile(self):
        """Non-responsabile user does not have edit permission."""
        self.client.login(username='other_test', password='otherpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])
        response = self.client.get(
            reverse('activities:activity_detail', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_edit'])


class ActivityCreateViewTests(ActivityTestCase):
    """Tests for the activity create view."""

    def test_create_view_requires_login(self):
        """Create view redirects anonymous users to login."""
        response = self.client.get(reverse('activities:activity_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_create_view_get_authenticated(self):
        """Authenticated user can access create form."""
        self.client.login(username='user_test', password='userpass123')
        response = self.client.get(reverse('activities:activity_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/activity_form.html')

    def test_create_activity_success(self):
        """Authenticated user can create an activity."""
        self.client.login(username='user_test', password='userpass123')

        data = {
            'tipo': Activity.TIPO_PROMOZIONALI_LOCO,
            'mese': '02',
            'anno': 2024,
            'nome_iniziativa': 'New Test Initiative',
            'citta': 'Milan',
            'settore': 'Fashion',
            'descrizione': 'A new test activity',
            'azione': 'Some actions',
            'number_persons': 5,
            'ufficio': Activity.OFFICE_BELGRADO,
            'responsabili': [self.regular_user.pk],
        }

        response = self.client.post(reverse('activities:activity_create'), data)

        # Should redirect to detail page on success
        self.assertEqual(response.status_code, 302)

        # Check activity was created
        activity = Activity.objects.filter(nome_iniziativa='New Test Initiative').first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.citta, 'Milan')

    def test_create_activity_adds_current_user_as_responsabile(self):
        """Creating activity automatically adds current user as responsabile."""
        self.client.login(username='user_test', password='userpass123')

        data = {
            'tipo': Activity.TIPO_PROMOZIONALI_LOCO,
            'mese': '03',
            'anno': 2024,
            'nome_iniziativa': 'User Responsabile Test',
            'citta': 'Rome',
            'ufficio': Activity.OFFICE_BELGRADO,
            'responsabili': [],  # Empty responsabili
        }

        response = self.client.post(reverse('activities:activity_create'), data)
        self.assertEqual(response.status_code, 302)

        activity = Activity.objects.filter(nome_iniziativa='User Responsabile Test').first()
        self.assertIsNotNone(activity)
        self.assertIn(str(self.regular_user.pk), activity.responsabili)

    def test_create_activity_with_invalid_type(self):
        """Creating activity with invalid choice shows form errors."""
        self.client.login(username='user_test', password='userpass123')

        # Use an invalid tipo choice
        data = {
            'tipo': 'Invalid Choice That Does Not Exist',
            'mese': '13',  # Invalid month
            'anno': 'not_a_number',  # Invalid year
            'nome_iniziativa': 'Test',
            'ufficio': 'Invalid Office',
        }

        response = self.client.post(reverse('activities:activity_create'), data)
        # Form should re-display with errors due to invalid choices
        self.assertEqual(response.status_code, 200)


class ActivityUpdateViewTests(ActivityTestCase):
    """Tests for the activity update view."""

    def test_update_view_requires_login(self):
        """Update view redirects anonymous users to login."""
        activity = self.create_test_activity()
        response = self.client.get(
            reverse('activities:activity_update', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_update_view_get_as_responsabile(self):
        """Responsabile can access update form."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.get(
            reverse('activities:activity_update', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/activity_form.html')

    def test_update_view_get_as_admin(self):
        """Admin can access update form for any activity."""
        self.client.login(username='admin_test', password='adminpass123')
        activity = self.create_test_activity(responsabili=[self.other_user])

        response = self.client.get(
            reverse('activities:activity_update', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_denied_for_non_responsabile(self):
        """Non-responsabile user is redirected when trying to update."""
        self.client.login(username='other_test', password='otherpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.get(
            reverse('activities:activity_update', kwargs={'slug': activity.slug})
        )
        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

    def test_update_activity_success(self):
        """Responsabile can update an activity."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        data = {
            'tipo': Activity.TIPO_PROMOZIONALI_LOCO,
            'mese': '04',
            'anno': 2024,
            'nome_iniziativa': 'Updated Initiative',
            'citta': 'Updated City',
            'settore': 'Updated Sector',
            'descrizione': 'Updated description',
            'azione': 'Updated action',
            'number_persons': 20,
            'ufficio': Activity.OFFICE_PODGORICA,
            'responsabili': [self.regular_user.pk],
        }

        response = self.client.post(
            reverse('activities:activity_update', kwargs={'slug': activity.slug}),
            data
        )

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)

        # Refresh from database
        activity.refresh_from_db()
        self.assertEqual(activity.nome_iniziativa, 'Updated Initiative')
        self.assertEqual(activity.citta, 'Updated City')


class ActivityDeleteViewTests(ActivityTestCase):
    """Tests for the activity delete view."""

    def test_delete_view_requires_login(self):
        """Delete view redirects anonymous users to login."""
        activity = self.create_test_activity()
        response = self.client.get(
            reverse('activities:activity_delete', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_delete_view_get_as_responsabile(self):
        """Responsabile can access delete confirmation page."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.get(
            reverse('activities:activity_delete', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activities/activity_confirm_delete.html')

    def test_delete_view_denied_for_non_responsabile(self):
        """Non-responsabile user is redirected when trying to delete."""
        self.client.login(username='other_test', password='otherpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.get(
            reverse('activities:activity_delete', kwargs={'slug': activity.slug})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_activity_success(self):
        """Responsabile can delete an activity."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])
        activity_slug = activity.slug

        response = self.client.post(
            reverse('activities:activity_delete', kwargs={'slug': activity.slug})
        )

        # Should redirect to list page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('activities:activity_list'))

        # Activity should be deleted
        self.assertFalse(Activity.objects.filter(slug=activity_slug).exists())

    def test_delete_activity_as_admin(self):
        """Admin can delete any activity."""
        self.client.login(username='admin_test', password='adminpass123')
        activity = self.create_test_activity(responsabili=[self.other_user])
        activity_slug = activity.slug

        response = self.client.post(
            reverse('activities:activity_delete', kwargs={'slug': activity.slug})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Activity.objects.filter(slug=activity_slug).exists())


class TodoOperationsViewTests(ActivityTestCase):
    """Tests for todo HTMX operations."""

    def test_add_todo_requires_login(self):
        """Add todo requires login."""
        activity = self.create_test_activity()
        response = self.client.post(
            reverse('activities:add_todo', kwargs={'slug': activity.slug}),
            {'name': 'New Todo'}
        )
        self.assertEqual(response.status_code, 302)

    def test_add_todo_as_responsabile(self):
        """Responsabile can add a todo."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.post(
            reverse('activities:add_todo', kwargs={'slug': activity.slug}),
            {'name': 'New Todo Item', 'description': 'Todo description'}
        )

        self.assertEqual(response.status_code, 200)

        # Refresh and check todo was added
        activity.refresh_from_db()
        self.assertIsNotNone(activity.todos)
        self.assertEqual(len(activity.todos), 1)
        self.assertEqual(activity.todos[0].name, 'New Todo Item')

    def test_add_todo_denied_for_non_responsabile(self):
        """Non-responsabile cannot add a todo."""
        self.client.login(username='other_test', password='otherpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.post(
            reverse('activities:add_todo', kwargs={'slug': activity.slug}),
            {'name': 'New Todo Item'}
        )

        self.assertEqual(response.status_code, 403)

    def test_add_todo_requires_name(self):
        """Add todo requires a name."""
        self.client.login(username='user_test', password='userpass123')
        activity = self.create_test_activity(responsabili=[self.regular_user])

        response = self.client.post(
            reverse('activities:add_todo', kwargs={'slug': activity.slug}),
            {'name': '', 'description': 'No name provided'}
        )

        self.assertEqual(response.status_code, 400)

    def test_toggle_todo(self):
        """Responsabile can toggle a todo's done status."""
        self.client.login(username='user_test', password='userpass123')

        # Create activity with a todo
        activity = self.create_test_activity(responsabili=[self.regular_user])
        activity.todos = [Todo(name='Test Todo', done=False)]
        activity.save()

        response = self.client.post(
            reverse('activities:toggle_todo', kwargs={'slug': activity.slug, 'todo_index': 0})
        )

        self.assertEqual(response.status_code, 200)

        # Refresh and check todo was toggled
        activity.refresh_from_db()
        self.assertTrue(activity.todos[0].done)

    def test_remove_todo(self):
        """Responsabile can remove a todo."""
        self.client.login(username='user_test', password='userpass123')

        # Create activity with todos
        activity = self.create_test_activity(responsabili=[self.regular_user])
        activity.todos = [
            Todo(name='Todo 1', done=False),
            Todo(name='Todo 2', done=False),
        ]
        activity.save()

        response = self.client.post(
            reverse('activities:remove_todo', kwargs={'slug': activity.slug, 'todo_index': 0})
        )

        self.assertEqual(response.status_code, 200)

        # Refresh and check todo was removed
        activity.refresh_from_db()
        self.assertEqual(len(activity.todos), 1)
        self.assertEqual(activity.todos[0].name, 'Todo 2')


class ActivityModelTests(ActivityTestCase):
    """Tests for the Activity model methods."""

    def test_generate_slug(self):
        """Slug is generated from nome_iniziativa, ufficio, and anno."""
        activity = Activity(
            nome_iniziativa='Test Initiative',
            ufficio=Activity.OFFICE_BELGRADO,
            anno=2024
        )
        slug = activity.generate_slug()
        self.assertIn('test-initiative', slug)
        self.assertIn('belgrado', slug)
        self.assertIn('2024', slug)

    def test_generate_unique_slug(self):
        """Unique slugs are generated when duplicates exist."""
        # Create first activity
        activity1 = self.create_test_activity(
            nome_iniziativa='Same Name',
            ufficio=Activity.OFFICE_BELGRADO,
            anno=2024
        )

        # Create second activity with same name/office/year
        activity2 = Activity(
            nome_iniziativa='Same Name',
            ufficio=Activity.OFFICE_BELGRADO,
            anno=2024
        )
        slug2 = activity2.generate_slug()

        # Should have a counter suffix
        self.assertNotEqual(activity1.slug, slug2)
        self.assertIn('-1', slug2)

    def test_str_representation(self):
        """Activity string representation is correct."""
        activity = self.create_test_activity(
            nome_iniziativa='Test Initiative',
            citta='Belgrade',
            mese='01',
            anno=2024
        )
        expected = 'Test Initiative - Belgrade (01/2024)'
        self.assertEqual(str(activity), expected)

    def test_get_period_display_both_dates(self):
        """Period display shows both dates when available."""
        from datetime import date
        activity = self.create_test_activity(
            data_inizio=date(2024, 1, 15),
            data_fine=date(2024, 1, 20)
        )
        period = activity.get_period_display()
        self.assertEqual(period, '15/01/2024 - 20/01/2024')

    def test_get_period_display_start_only(self):
        """Period display shows only start date when end date is missing."""
        from datetime import date
        activity = self.create_test_activity(
            data_inizio=date(2024, 1, 15),
            data_fine=None
        )
        period = activity.get_period_display()
        self.assertEqual(period, '15/01/2024')

    def test_get_period_display_no_dates(self):
        """Period display returns N/A when no dates are set."""
        activity = self.create_test_activity(
            data_inizio=None,
            data_fine=None
        )
        period = activity.get_period_display()
        self.assertEqual(period, 'N/A')

    def test_is_user_responsabile(self):
        """is_user_responsabile returns correct result."""
        activity = self.create_test_activity(responsabili=[self.regular_user])

        self.assertTrue(activity.is_user_responsabile(self.regular_user))
        self.assertFalse(activity.is_user_responsabile(self.other_user))

    def test_can_user_edit_responsabile(self):
        """Responsabile can edit activity."""
        activity = self.create_test_activity(responsabili=[self.regular_user])

        self.assertTrue(activity.can_user_edit(self.regular_user))
        self.assertFalse(activity.can_user_edit(self.other_user))

    def test_can_user_edit_admin(self):
        """Admin can edit any activity."""
        activity = self.create_test_activity(responsabili=[self.other_user])

        self.assertTrue(activity.can_user_edit(self.admin_user))


class ReportGenerationTests(ActivityTestCase):
    """Tests for Excel and PDF report generation."""

    def test_excel_report_no_selection(self):
        """Excel report with no activities shows error."""
        response = self.client.post(
            reverse('activities:generate_excel_report'),
            {'activity_ids': '[]'}
        )
        # Should redirect back to list
        self.assertEqual(response.status_code, 302)

    def test_excel_report_generation(self):
        """Excel report can be generated for selected activities."""
        activity = self.create_test_activity()

        response = self.client.post(
            reverse('activities:generate_excel_report'),
            {'activity_ids': json.dumps([str(activity.id)])}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_pdf_report_no_selection(self):
        """PDF report with no activities shows error."""
        response = self.client.post(
            reverse('activities:generate_pdf_report'),
            {'activity_ids': '[]'}
        )
        # Should redirect back to list
        self.assertEqual(response.status_code, 302)

    def test_pdf_report_generation(self):
        """PDF report can be generated for selected activities."""
        activity = self.create_test_activity()

        response = self.client.post(
            reverse('activities:generate_pdf_report'),
            {'activity_ids': json.dumps([str(activity.id)])}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
