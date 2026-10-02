# Django: validate input at the boundary

A small pattern for keeping invalid data out of application logic.

## Model + form

```python
from django import forms

class DeviceForm(forms.Form):
    hostname = forms.CharField(max_length=63)
    enabled = forms.BooleanField(required=False)

    def clean_hostname(self):
        value = self.cleaned_data["hostname"].strip().lower()
        if " " in value:
            raise forms.ValidationError("Hostname cannot contain spaces.")
        return value
```

## View

```python
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def register_device(request):
    form = DeviceForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    return JsonResponse({"hostname": form.cleaned_data["hostname"]}, status=201)
```

Validate at the HTTP boundary, use `cleaned_data` afterwards, and return an explicit 4xx response for invalid client input.
