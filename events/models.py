from django.db import models
from django.contrib.auth.models import User,AbstractUser
from django.urls import reverse
from django.utils import timezone

class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.'
    )
    is_pro = models.BooleanField(default=False)

    @property
    def has_active_subscription(self):
        return hasattr(self, 'subscription') and self.subscription.is_active()

class Category(models.Model):
    name = models.CharField(max_length=100,null=False, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})

class Event(models.Model):
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, related_name='events')
    title = models.CharField(max_length=150)
    description = models.TextField()
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=300)
    total_tickets = models.PositiveIntegerField(default=0)
    available_tickets = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def get_lowest_price(self):
        category = self.ticket_categories.order_by('price').first()
        return category.price if category else 0

    def get_highest_price(self):
        category = self.ticket_categories.order_by('-price').first()
        return category.price if category else 0

    def get_total_revenue(self):
        return sum(category.get_revenue() for category in self.ticket_categories.all())

    def get_total_revenue(self, tickets_sold):
        return tickets_sold * self.ticket_price
    
    def get_available_categories(self):
        now = timezone.now()
        return self.ticket_categories.filter(
            available_tickets__gt=0,
            sales_start__lte=now,
            sales_end__gte=now
        )

    @property
    def tickets_sold(self):
        return self.total_tickets - self.available_tickets

    @property
    def is_sold_out(self):
        return not self.get_available_categories().exists()

    def get_absolute_url(self):
        return reverse('event_detail',kwargs={'pk': self.pk})

    @property
    def tickets_sold(self):
        return sum(
            category.total_tickets - category.available_tickets 
            for category in self.ticket_categories.all()
        )
    @property
    def is_sold_out(self):
        return not self.get_available_categories().exists()

    @property
    def is_past_event(self):
        return self.date < timezone.now()
    
    @property
    def lowest_ticket_price(self):
        category = self.ticket_categories.order_by('price').first()
        return category.price if category else None

    @property
    def highest_ticket_price(self):
        category = self.ticket_categories.order_by('-price').first()
        return category.price if category else None

    def get_available_categories(self):
        return self.ticket_categories.filter(
            available_tickets__gt=0,
            sales_start__lte=timezone.now(),
            sales_end__gte=timezone.now()
        )
    

class TicketCategory(models.Model):
    CATEGORY_TYPES = [
        ('regular', 'Regular'),
        ('vip', 'VIP'),
        ('group', 'Group'),
        ('early_bird', 'Early Bird'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_categories')
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    initial_tickets = models.PositiveIntegerField(
        default=0,
        help_text="Initial number of tickets in this category"
    )
    available_tickets = models.PositiveIntegerField(
        default=0,
        help_text="Current number of tickets available"
    )
    description = models.TextField(blank=True)
    max_tickets_per_purchase = models.PositiveIntegerField(default=10,help_text="Maximum number of tickets one person can buy")
    sales_start = models.DateTimeField()
    sales_end = models.DateTimeField()

    class Meta:
        unique_together = ['event', 'category_type']
        ordering = ['price']

    def __str__(self):
        return f"{self.event.title} - {self.name} (${self.price})"
    
    def save(self, *args, **kwargs):
        if not self.pk and self.available_tickets:
            self.initial_tickets = self.available_tickets
        super().save(*args, **kwargs)

    @property
    def tickets_sold(self):
        if self.initial_tickets is None or self.available_tickets is None:
            return 0
        return max(0, self.initial_tickets - self.available_tickets)

    def get_sales_percentage(self):
        if not self.initial_tickets:
            return 0
        return min(100, (self.tickets_sold * 100) // self.initial_tickets)

    @property
    def is_available(self):
        now = timezone.now()
        return (
            self.available_tickets > 0 and
            self.sales_start <= now and
            self.sales_end >= now
        )

    @property
    def total_tickets(self):
        return self.initial_tickets

    @property
    def is_available(self):
        now = timezone.now()
        return (
            self.available_tickets > 0 and
            self.sales_start <= now and
            self.sales_end >= now
        )

    @property
    def total_tickets(self):
        return self.initial_tickets or self.available_tickets

    def get_revenue(self):
        return sum(ticket.total_amount for ticket in self.tickets.all())

    @property
    def is_available(self):
        now = timezone.now()
        return (self.available_tickets > 0 and 
                self.sales_start <= now <= self.sales_end)

class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    ticket_category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE, null=True, blank=True, related_name='tickets')
    buyer_name = models.CharField(max_length=100)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    ticket_code = models.CharField(max_length=50, unique=True)

    def save(self, *args, **kwargs):
        # Set the unit price from the ticket category if not set
        if not self.unit_price:
            self.unit_price = self.ticket_category.price
        
        # Calculate total amount
        self.total_amount = self.unit_price * self.quantity

        # Generate ticket code if not set
        if not self.ticket_code:
            import uuid
            self.ticket_code = str(uuid.uuid4())[:8].upper()
        
        super().save(*args, **kwargs) 

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=100)
    stripe_subscription_id = models.CharField(max_length=100)
    plan = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_active(self):
        return self.status == 'active' and self.expires_at > timezone.now()