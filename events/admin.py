from django.contrib import admin
from .models import Event, Ticket,Category

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'date', 'ticket_price', 'tickets_sold', 'is_active']
    list_filter = ['is_active', 'date', 'created_at']
    search_fields = ['title', 'description', 'location']
    list_editable = ['is_active']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_code', 'buyer_name', 'event', 'quantity', 'total_amount', 'purchased_at']
    list_filter = ['purchased_at', 'event']
    search_fields = ['buyer_name', 'buyer_email', 'ticket_code']
    readonly_fields = ['ticket_code', 'purchased_at']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
        list_display = ['name', 'description']
        search_fields = ['name', 'description']
        list_filter = ['name']
        prepopulated_fields = {'slug': ('name',)}