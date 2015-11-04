import datetime

from django.core.urlresolvers import reverse

from ..models import Event, TodoItem
from .base import TestBase


class TestTodoItemViews(TestBase):
    """Tests for the TodoItem model."""

    def setUp(self):
        self._setUpNonInstructors()
        self._setUpUsersAndLogin()
        self._setUpEvents()

    def test_adding_many_todos(self):
        """Test if todos_add view really adds multiple standard TODOs to the
        event."""
        event = Event.objects.filter(slug__endswith="-upcoming") \
                             .order_by("-pk")[0]
        event.end = event.start + datetime.timedelta(days=2)
        event.save()

        # check if the event has 0 todos
        assert event.todoitem_set.all().count() == 0

        # add standard todos
        ident = event.get_ident()
        url, form = self._get_initial_form('todos_add', ident)

        # fix: turn Nones into empty strings
        for key, value in form.items():
            if value is None:
                form[key] = ''

        rv = self.client.post(reverse('todos_add', args=[ident]), form)

        # let's check if the form passes
        assert rv.status_code == 302

        # finally let's check there are some new todos
        assert event.todoitem_set.all().count() == 9

    def test_mark_completed(self):
        """Test if TODO is properly being marked as completed."""
        event = Event.objects.all()[0]

        todo = TodoItem.objects.create(
            event=event, completed=False, title="Test TODO1",
            due=datetime.date.today(), additional="",
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
            due=datetime.date.today(), additional="",
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
            due=datetime.date.today(), additional="",
        )

        assert todo in event.todoitem_set.all()

        self.client.get(reverse('todo_delete', args=[todo.pk]))

        assert event.todoitem_set.all().count() == 0

    def test_edited(self):
        """Ensure TODOs can be edited."""
        event = Event.objects.all()[0]

        todo = TodoItem.objects.create(
            event=event, completed=False, title="Test TODO4",
            due=datetime.date.today(), additional="",
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
