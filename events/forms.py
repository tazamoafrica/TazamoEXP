from django import forms
from .models import Event,Category

class EventForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date:
            self.fields['date'].widget.attrs['value'] = self.instance.date.strftime('%Y-%m-%dT%H:%M')

    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'image', 'date', 'location', 'ticket_price', 'total_tickets']
        widgets = {
            'date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_tickets': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class TicketPurchaseForm(forms.Form):
    buyer_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    buyer_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    buyer_phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    quantity = forms.IntegerField(min_value=1, max_value=10, widget=forms.NumberInput(attrs={'class': 'form-control'}))