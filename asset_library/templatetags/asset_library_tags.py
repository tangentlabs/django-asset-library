import purl
from django import template

register = template.Library()


@register.simple_tag
def urlencode_form_data(form, **explicit_values):
    """ Encode GET form into a URL

    :param explicit_values: dictionary of values that overwrite the form values
    :return: relative URL containing fields of form """
    data = dict((field.html_name, field.value()) for field in form)
    data.update(explicit_values)
    non_empty_data = dict((key, value) for key, value in data.items() if value)
    url = purl.URL().query_params(non_empty_data)
    # Use only query parts of URL
    return '?' + url.query()
