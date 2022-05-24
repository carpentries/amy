from django import template
from django.apps import apps


register = template.Library()


@register.simple_tag
def get_verbose_field_name_by_instance(instance, field_name):
	"""Return the verbose_name of a model field."""			
	if not hasattr(instance, '_meta'):
		raise TypeError("Invalid model instance.")	

	return instance._meta.get_field(field_name).verbose_name

@register.simple_tag
def get_verbose_field_name_by_model_name(model_name, field_name):
	"""Return the verbose_name of a model field."""	
	model = model_name

	if isinstance(model_name, str):
		for apps_model in apps.get_models():
			if apps_model.__name__ == model_name:
				model = apps_model							
	if not hasattr(model, '_meta'):
		raise TypeError("Invalid model name.")
		
	return model._meta.get_field(field_name).verbose_name

