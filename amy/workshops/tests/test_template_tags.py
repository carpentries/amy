from datetime import date

from django.template import Context, Template
from django.test import TestCase

from workshops.models import Event
from workshops.templatetags.verbose_names import (
	get_verbose_field_name_by_instance,	
	get_verbose_field_name_by_model_name,
)


class TestVerboseNamesTemplateTags(TestCase):		
	def test_get_verbose_field_name_by_instance_for_event_host(self):
		event = Event(
			slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
        )
		field_name = 'host'
		expected_out = event._meta.get_field(field_name).verbose_name
		out = Template(
			"{% load verbose_names %}"
			"{% get_verbose_field_name_by_instance event field_name %}"
		).render(Context({'event': event, 'field_name': field_name}))
		self.assertEqual(expected_out, out)

	def test_get_verbose_field_name_by_instance_for_event_sponsor(self):
		event = Event(
			slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
        )
		field_name = 'sponsor'
		expected_out = event._meta.get_field(field_name).verbose_name
		out = Template(
			"{% load verbose_names %}"
			"{% get_verbose_field_name_by_instance event field_name %}"
		).render(Context({'event': event, 'field_name': field_name}))
		self.assertEqual(expected_out, out)

	def test_get_verbose_field_name_by_instance_when_event_is_not_model_instance(self):
		event = 'not model instance'
		with self.assertRaises(TypeError):
			get_verbose_field_name_by_instance(event, 'host')

	def test_get_verbose_field_name_by_model_name_cls_for_event_model_for_host_field(self):
		event = Event(
			slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
        )		
		field_name = 'host'
		expected_out = event._meta.get_field(field_name).verbose_name
		out = Template(
			"{% load verbose_names %}"
			"{% get_verbose_field_name_by_model_name model_name field_name %}"
		).render(Context({'model_name': Event, 'field_name': field_name}))
		self.assertEqual(expected_out, out)

	def test_get_verbose_field_name_by_model_name_str_for_event_model_for_host_field(self):
		event = Event(
			slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
        )		
		field_name = 'host'
		expected_out = event._meta.get_field(field_name).verbose_name
		out = Template(
			"{% load verbose_names %}"
			"{% get_verbose_field_name_by_model_name model_name field_name %}"
		).render(Context({'model_name': 'Event', 'field_name': field_name}))
		self.assertEqual(expected_out, out)

	def test_get_verbose_field_name_by_model_name_for_faulty_model_name(self):
		bad_model_name = 'not model instance'
		with self.assertRaises(TypeError):
			get_verbose_field_name_by_model_name(bad_model_name, 'host')


