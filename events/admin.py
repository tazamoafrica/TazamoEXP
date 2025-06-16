from datetime import timezone
from django.contrib import admin
from .models import Event, Ticket, Category, TicketCategory

class TicketCategoryInline(admin.TabularInline):
    model = TicketCategory
    extra = 1
    min_num = 1
    fields = ['name', 'category_type', 'price', 'available_tickets', 'sales_start', 'sales_end']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'date', 'lowest_ticket_price', 'tickets_sold', 'is_active']
    list_filter = ['is_active', 'date', 'created_at']
    search_fields = ['title', 'description', 'location']
    list_editable = ['is_active']
    inlines = [TicketCategoryInline]

    def lowest_ticket_price(self, obj):
        return obj.lowest_ticket_price if obj.lowest_ticket_price else "No price set"
    lowest_ticket_price.short_description = "Starting Price"

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_code', 'buyer_name', 'event', 'ticket_category', 'quantity', 'total_amount', 'purchased_at']
    list_filter = ['purchased_at', 'event', 'ticket_category']
    search_fields = ['buyer_name', 'buyer_email', 'ticket_code']
    readonly_fields = ['ticket_code', 'purchased_at', 'unit_price', 'total_amount']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    list_filter = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'event', 'category_type', 'price', 'available_tickets', 'sales_status']
    list_filter = ['category_type', 'event']
    search_fields = ['name', 'event__title']
    readonly_fields = ['sales_status']

    def sales_status(self, obj):
        if not obj.is_available:
            if obj.available_tickets <= 0:
                return "Sold Out"
            elif obj.sales_start > timezone.now():
                return "Not Started"
            elif obj.sales_end < timezone.now():
                return "Ended"
        return "Available"
    sales_status.short_description = "Status"