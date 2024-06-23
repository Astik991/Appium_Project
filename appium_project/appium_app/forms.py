from django import forms

class DeviceForm(forms.Form):
    platform_name = forms.CharField(label='Platform Name', max_length=10)
    platform_version = forms.CharField(label='Platform Version', max_length=10)
    device_name = forms.CharField(label='Device Name', max_length=50)
    profession = forms.CharField(label='Profession', max_length=50)
