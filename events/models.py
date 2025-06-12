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
    organizer = models.ForeignKey(User, on_delete=models.CASCADE,related_name='events')
    category = models.ForeignKey(Category, on_delete=models.CASCADE,null=True, related_name='events')
    title = models.CharField(max_length=150)
    description = models.TextField()
    image = models.ImageField(upload_to='event_images/',blank=True,null=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=300)
    ticket_price = models.DecimalField(max_digits=10,decimal_places=2)
    total_tickets = models.PositiveIntegerField()
    available_tickets = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def get_total_revenue(self, tickets_sold):
        return tickets_sold * self.ticket_price

    def get_absolute_url(self):
        return reverse('event_detail',kwargs={'pk': self.pk})

    @property    
    def tickets_sold(self):
        return self.total_tickets - self.available_tickets

    @property
    def is_sold_out(self):
        return self.available_tickets <= 0

    @property
    def is_past_event(self):
        return self.date < timezone.now()

class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    buyer_name = models.CharField(max_length=100)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    ticket_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.buyer_name} - {self.event.title}"

    def save(self,*args,**kwargs):
        if not self.ticket_code:
            import uuid
            self.ticket_code = str(uuid.uuid4())[:8].upper()
        super().save(*args,**kwargs)   

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