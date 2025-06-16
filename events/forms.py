from django import forms
from django.forms import inlineformset_factory
from .models import Event, Category, TicketCategory

class TicketCategoryForm(forms.ModelForm):
    class Meta:
        model = TicketCategory
        fields = ['name', 'category_type', 'price', 'available_tickets', 'description', 
                 'max_tickets_per_purchase', 'sales_start', 'sales_end']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category_type': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'available_tickets': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_tickets_per_purchase': forms.NumberInput(attrs={'class': 'form-control','min': '1','value': '10'}),
            'sales_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'sales_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

TicketCategoryFormSet = inlineformset_factory(
    Event,
    TicketCategory,
    form=TicketCategoryForm,
    extra=4,
    max_num=4,
    can_delete=True
)

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
        fields = ['title', 'description', 'category', 'image', 'date', 'location', 'total_tickets']
        widgets = {
            'date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'total_tickets': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

class TicketPurchaseForm(forms.Form):
    buyer_name = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    buyer_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    buyer_phone = forms.CharField(
        max_length=20, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    ticket_category = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields['ticket_category'].queryset = event.get_available_categories()
        
        # Update quantity field max_value based on selected category
        if 'ticket_category' in self.data:
            try:
                category_id = int(self.data.get('ticket_category'))
                category = TicketCategory.objects.get(id=category_id)
                self.fields['quantity'].max_value = min(
                    category.available_tickets,
                    category.max_tickets_per_purchase
                )
            except (ValueError, TicketCategory.DoesNotExist):
                pass

    def clean(self):
        cleaned_data = super().clean()
        ticket_category = cleaned_data.get('ticket_category')
        quantity = cleaned_data.get('quantity')

        if ticket_category and quantity:
            if quantity > ticket_category.available_tickets:
                raise forms.ValidationError(
                    f"Only {ticket_category.available_tickets} tickets available in this category."
                )
            if quantity > ticket_category.max_tickets_per_purchase:
                raise forms.ValidationError(
                    f"Maximum {ticket_category.max_tickets_per_purchase} tickets allowed per purchase in this category."
                )

        return cleaned_data