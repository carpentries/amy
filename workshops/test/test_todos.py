from datetime import date, timedelta

from django.core.urlresolvers import reverse

from ..models import Event, TodoItem, TodoItemQuerySet
from ..forms import TodoFormSet
from .base import TestBase


class TestTodoItemViews(TestBase):
    """Tests for the TodoItem model."""

    def setUp(self):
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpUsersAndLogin()
        self._setUpEvents()

    def test_adding_many_todos(self):
        """Test if todos_add view really adds multiple standard TODOs to the
        event. To speed things up, the calls to `todos_add` were cut out (since
        there was no way to efficiently get fields from the webpage itself)."""
        event = Event.objects.filter(slug__endswith="-upcoming") \
                             .order_by("-pk").first()

        # check if the event has 0 todos
        assert event.todoitem_set.all().count() == 0

        # add some todos
        data = {
            'form-INITIAL_FORMS': 0,
            'form-TOTAL_FORMS': 3,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000,
            'form-0-id': '',
            'form-0-title': 'Set date with host',
            'form-0-due': '2016-01-24',
            'form-0-additional': '',
            'form-0-event': event.pk,
            'form-0-completed': False,
            'form-1-id': '',
            'form-1-title': 'Set up a workshop website',
            'form-1-due': '2016-01-24',
            'form-1-additional': '',
            'form-1-event': event.pk,
            'form-1-completed': False,
            'form-2-id': '',
            'form-2-title': 'Find first instructor',
            'form-2-due': '2016-01-24',
            'form-2-additional': '',
            'form-2-event': event.pk,
            'form-2-completed': False,
        }
        formset = TodoFormSet(data)

        assert formset.is_valid()
        formset.save()

        # finally let's check there are some new todos
        assert event.todoitem_set.all().count() == 3

    def test_mark_completed(self):
        """Test if TODO is properly being marked as completed."""
        event = Event.objects.all()[0]

        todo = TodoItem.objects.create(
            event=event, completed=False, title="Test TODO1",
            due=date.today(), additional="",
        )

        assert todo.completed is False

        self.client.get(reverse('todo_mark_completed', args=[todo.pk]))
        todo.refresh_from_db()

        assert todo.completed is True

    def test_mark_incompleted(self):
        """Test if TODO is properly being marked as incompleted."""
        event = Event.objects.all()[0]

        todo = TodoItem.objects.create(
            event=event, completed=True, title="Test TODO2",
            due=date.today(), additional="",
        )

        assert todo.completed is True

        self.client.get(reverse('todo_mark_incompleted', args=[todo.pk]))
        todo.refresh_from_db()

        assert todo.completed is False

    def test_deleted(self):
        """Ensure TODOs are deleted."""
        event = Event.objects.all()[0]

        todo = TodoItem.objects.create(
            event=event, completed=False, title="Test TODO3",
            due=date.today(), additional="",
        )

        assert todo in event.todoitem_set.all()

        self.client.get(reverse('todo_delete', args=[todo.pk]))

        assert event.todoitem_set.all().count() == 0

    def test_edited(self):
        """Ensure TODOs can be edited."""
        event = Event.objects.all()[0]

        todo = TodoItem.objects.create(
            event=event, completed=False, title="Test TODO4",
            due=date.today(), additional="",
        )

        url, form = self._get_initial_form('todo_edit', todo.pk)
        form['title'] = "Test TODO4 - new title"
        form['completed'] = True
        form['additional'] = ''

        rv = self.client.post(reverse('todo_edit', args=[todo.pk]), form)
        assert rv.status_code == 302

        todo.refresh_from_db()

        assert todo.title == "Test TODO4 - new title"
        assert todo.completed is True


class TestTodoManager(TestBase):
    """Test for TodoItemQuerySet as a manager."""

    def setUp(self):
        super()._setUpHosts()
        e = Event.objects.create(slug='event-with-todos', host=self.host_alpha)
        self.today = date(2015, 12, 31)
        self.current = TodoItem.objects.create(event=e, title='Current',
                                               due=date(2015, 12, 30))
        self.next = TodoItem.objects.create(event=e, title='Next',
                                            due=date(2016, 1, 5))
        self.outside1 = TodoItem.objects.create(event=e, title='Outside1',
                                                due=date(2015, 12, 27))
        self.outside2 = TodoItem.objects.create(event=e, title='Outside2',
                                                due=date(2016, 1, 11))

    def test_current_week_dates(self):
        """Ensure we calculate start and end of current week correctly."""
        start, end = TodoItemQuerySet.current_week_dates(today=self.today)
        self.assertEqual(start, date(2015, 12, 28))
        self.assertEqual(end, date(2016, 1, 4))

    def test_next_week_dates(self):
        """Ensure we calculate start and end of next week correctly."""
        start, end = TodoItemQuerySet.next_week_dates(today=self.today)
        self.assertEqual(start, date(2016, 1, 4))
        self.assertEqual(end, date(2016, 1, 11))

    def test_todos_current_week(self):
        """Ensure we get todos that are due this week."""
        todos = TodoItem.objects.current_week(today=self.today)
        self.assertEqual(set(todos), set([self.current]))

    def test_todos_next_week(self):
        """Ensure we get todos that are due next week."""
        todos = TodoItem.objects.next_week(today=self.today)
        self.assertEqual(set(todos), set([self.next]))

    def test_todos_current(self):
        """Ensure we get todos that are due this and next week, and aren't
        completed."""
        todos = TodoItem.objects.current(today=self.today)
        self.assertEqual(set(todos), set([self.current, self.next]))
