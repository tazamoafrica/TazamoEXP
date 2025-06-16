from django.utils import timezone
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Category, Event, Ticket, TicketCategory
from .forms import EventForm, TicketCategoryFormSet, TicketPurchaseForm
import stripe
from django.db.models import Q
from PIL import Image, ImageDraw, ImageFont
import io
from django.core.mail import EmailMessage
from django.conf import settings
import os
import json
from twilio.rest import Client

stripe.api_key = settings.STRIPE_SECRET_KEY

def home(request):
    events = Event.objects.filter(
        is_active=True, 
        date__gte=timezone.now()
    ).prefetch_related('ticket_categories').order_by('date')[:6]
    
    return render(request, 'events/home.html', {
        'events': events
    })

def event_list(request):
    events = Event.objects.filter(is_active=True, date__gte=timezone.now())
    categories = Category.objects.all()

    search_query = request.GET.get('search', '')
    category_slug = request.GET.get('category', '')
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    if category_slug:
        events = events.filter(category__slug=category_slug)

    return render(request, 'events/event_list.html', {'events': events, 'categories': categories})

def category_events(request, slug):
    category = get_object_or_404(Category, slug=slug)
    events = Event.objects.filter(category=category)
    return render(request, 'events/category_events.html', {'category': category, 'events': events})

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    selected_category = event.ticket_categories.filter(
        available_tickets__gt=0
    ).first()
    context = {
        'event': event,
        'now': timezone.now(),
        'selected_category': selected_category,
        'now': timezone.now(),
    }
    return render(request, 'events/event_detail.html', context)

@login_required
def dashboard(request):
    events = Event.objects.filter(organizer=request.user)
    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_revenue = sum(ticket.total_amount for event in events for ticket in event.tickets.all())
    
    context = {
        'events': events,
        'total_events': total_events,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
    }
    return render(request, 'events/dashboard.html', context)

@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        ticket_formset = TicketCategoryFormSet(request.POST)
        
        if form.is_valid() and ticket_formset.is_valid():
            try:
                # Create event with initial available_tickets value
                event = form.save(commit=False)
                event.organizer = request.user
                event.available_tickets = 0  # Set initial value
                event.save()
                
                # Save ticket categories
                ticket_formset.instance = event
                categories = ticket_formset.save()
                
                if not categories:
                    messages.error(request, 'Please add at least one ticket category.')
                    event.delete()
                    return render(request, 'events/create_event.html', {
                        'form': form,
                        'ticket_formset': ticket_formset
                    })
                
                # Update available tickets from categories
                total_available = sum(tc.available_tickets for tc in categories)
                event.available_tickets = total_available
                event.total_tickets = total_available
                event.save()
                
                messages.success(request, 'Event created successfully!')
                return redirect('dashboard')
                
            except Exception as e:
                messages.error(request, f'Error creating event: {str(e)}')
                # Clean up if there was an error
                if event.pk:
                    event.delete()
        else:
            if form.errors:
                messages.error(request, 'Please correct the errors in the event form.')
            if ticket_formset.errors:
                messages.error(request, 'Please correct the errors in the ticket categories.')
            print("Form errors:", form.errors)
            print("Formset errors:", ticket_formset.errors)
    else:
        form = EventForm()
        ticket_formset = TicketCategoryFormSet()
    
    return render(request, 'events/create_event.html', {
        'form': form,
        'ticket_formset': ticket_formset
    })

@login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        ticket_formset = TicketCategoryFormSet(request.POST, instance=event)
        
        if form.is_valid() and ticket_formset.is_valid():
            try:
                form.save()
                ticket_formset.save()
                
                # Update available tickets
                event.available_tickets = sum(tc.available_tickets for tc in event.ticket_categories.all())
                event.save()
                
                messages.success(request, 'Event updated successfully!')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Error saving event: {str(e)}')
    else:
        form = EventForm(instance=event)
        ticket_formset = TicketCategoryFormSet(instance=event)
    
    return render(request, 'events/edit_event.html', {
        'form': form,
        'ticket_formset': ticket_formset,
        'event': event
    })
@login_required
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        return redirect('dashboard')
    return render(request, 'events/delete.html', {'event': event})


def checkout(request, pk):
    event = get_object_or_404(Event, pk=pk)
    category_id = request.GET.get('category')
    
    if not category_id:
        messages.error(request, 'Please select a ticket category.')
        return redirect('event_detail', pk=event.pk)
    
    try:
        selected_category = TicketCategory.objects.get(
            id=category_id,
            event=event,
            available_tickets__gt=0
        )
    except TicketCategory.DoesNotExist:
        messages.error(request, 'Selected ticket category is not available.')
        return redirect('event_detail', pk=event.pk)
    
    initial_data = {
        'ticket_category': selected_category,
        'quantity': 1
    }
    
    if request.user.is_authenticated:
        initial_data.update({
            'buyer_name': request.user.get_full_name(),
            'buyer_email': request.user.email
        })
    
    form = TicketPurchaseForm(
        event, 
        initial=initial_data
    )
    
    context = {
        'event': event,
        'selected_category': selected_category,
        'form': form,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    
    return render(request, 'events/checkout.html', context)

@csrf_exempt
@require_POST
def payment_success(request):
    try:
        payload = json.loads(request.body)
        payment_intent_id = payload.get('payment_intent_id')
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            event_id = intent.metadata.get('event_id')
            ticket_category_id = intent.metadata.get('ticket_category_id')
            buyer_name = intent.metadata.get('buyer_name')
            buyer_email = intent.metadata.get('buyer_email')
            quantity = int(intent.metadata.get('quantity'))
            
            event = Event.objects.get(id=event_id)
            ticket_category = TicketCategory.objects.get(id=ticket_category_id)
            
            ticket = Ticket.objects.create(
                event=event,
                ticket_category=ticket_category,
                buyer_name=buyer_name,
                buyer_email=buyer_email,
                quantity=quantity,
                unit_price=ticket_category.price,
                total_amount=intent.amount / 100,
                stripe_payment_intent_id=payment_intent_id
            )
            
            # Update available tickets
            ticket_category.available_tickets -= quantity
            ticket_category.save()
            
            event.available_tickets -= quantity
            event.save()
            
            send_ticket_email(ticket)
            
            if hasattr(ticket, 'buyer_phone') and ticket.buyer_phone:
                send_ticket_sms(ticket)
            
            return JsonResponse({'success': True, 'ticket_id': ticket.id})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def generate_ticket_image(ticket):
    """Generate a ticket image with event and buyer details"""
    # Create a new image with white background
    width = 1000
    height = 500
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fallback to default if not found
    try:
        font_large = ImageFont.truetype("arial.ttf", 40)
        font_medium = ImageFont.truetype("arial.ttf", 30)
        font_small = ImageFont.truetype("arial.ttf", 25)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw ticket content
    draw.text((50, 50), ticket.event.title, fill='black', font=font_large)
    draw.text((50, 100), f"Category: {ticket.ticket_category.name}", fill='black', font=font_medium)
    draw.text((50, 150), f"Date: {ticket.event.date.strftime('%B %d, %Y at %I:%M %p')}", fill='black', font=font_medium)
    draw.text((50, 200), f"Location: {ticket.event.location}", fill='black', font=font_medium)
    draw.text((50, 250), f"Attendee: {ticket.buyer_name}", fill='black', font=font_medium)
    draw.text((50, 300), f"Quantity: {ticket.quantity}", fill='black', font=font_medium)
    draw.text((50, 350), f"Price per ticket: ${ticket.unit_price}", fill='black', font=font_medium)
    draw.text((50, 400), f"Ticket Code: {ticket.ticket_code}", fill='black', font=font_large)
    
    # Save image to bytes buffer
    image_buffer = io.BytesIO()
    image.save(image_buffer, format='JPEG', quality=90)
    image_buffer.seek(0)
    
    return image_buffer

def send_ticket_email(ticket):
    """Send email with ticket details and attached ticket image"""
    subject = f'Your Ticket for {ticket.event.title}'
    message = f"""
    Dear {ticket.buyer_name},
    
    Thank you for purchasing tickets for {ticket.event.title}!
    
    Event Details:
    - Event: {ticket.event.title}
    - Category: {ticket.ticket_category.name}
    - Date: {ticket.event.date.strftime('%B %d, %Y at %I:%M %p')}
    - Location: {ticket.event.location}
    - Quantity: {ticket.quantity}
    - Price per ticket: ${ticket.unit_price}
    - Total Paid: ${ticket.total_amount}
    - Ticket Code: {ticket.ticket_code}
    
    
    Please find your ticket attached to this email.
    Present this ticket (either digital or printed) at the event entrance.
    
    Best regards,
    Event Team
    """
    
    # Create EmailMessage object
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [ticket.buyer_email]
    )
    
    ticket_image = generate_ticket_image(ticket)
    email.attach(
        f'ticket_{ticket.ticket_code}.jpg',
        ticket_image.getvalue(),
        'image/jpeg'
    )
    
    email.send(fail_silently=False)

def send_ticket_sms(ticket):
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=f'Ticket confirmed for {ticket.event.title} on {ticket.event.date.strftime("%m/%d/%Y")}. Code: {ticket.ticket_code}',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=ticket.buyer_phone
        )
    except Exception as e:
        print(f"SMS sending failed: {e}")

def ticket_confirmation(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return render(request, 'events/ticket_confirmation.html', {'ticket': ticket})


SUBSCRIPTION_PLANS = {
    'daily': {
        'name': 'Daily Plan',
        'price_id': 'price_XXXXX', 
        'amount': 500,  # $5.00
    },
    'monthly': {
        'name': 'Monthly Plan',
        'price_id': 'price_XXXXX',  
        'amount': 4900,  # $49.00
    },
    'yearly': {
        'name': 'Yearly Plan',
        'price_id': 'price_XXXXX',  
        'amount': 39900,  # $399.00
    }
}

@login_required
def subscription(request, plan):
    if plan not in SUBSCRIPTION_PLANS:
        messages.error(request, 'Invalid subscription plan')
        return redirect('dashboard')
    
    plan_data = SUBSCRIPTION_PLANS[plan]
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': plan_data['price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/subscription/success/'),
            cancel_url=request.build_absolute_uri('/subscription/cancel/'),
            client_reference_id=request.user.id,
        )
        return redirect(checkout_session.url)
    except Exception as e:
        messages.error(request, f'Error creating subscription: {str(e)}')
        return redirect('dashboard')

@login_required
def subscription_success(request):
    messages.success(request, 'Successfully subscribed to TazamoXM Pro!')
    return redirect('dashboard')

@login_required
def subscription_cancel(request):
    messages.info(request, 'Subscription cancelled')
    return redirect('dashboard')

@login_required
def pro_features(request):
    return render(request, 'subscription/pro_features.html')

@login_required
def subscription_settings(request):
    return render(request, 'subscription/settings.html')

@login_required
def subscription_settings(request):
    context = {
        'billing_history': [],  # Fetch from Stripe
    }
    if request.user.subscription:
        # Fetch recent invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=request.user.subscription.stripe_customer_id,
            limit=5
        )
        context['billing_history'] = invoices.data
    
    return render(request, 'subscription/settings.html', context)

@require_POST
def create_payment_intent(request, pk):
    try:
        event = get_object_or_404(Event, pk=pk)
        category_id = request.POST.get('category_id')
        quantity = int(request.POST.get('quantity', 1))
        
        category = get_object_or_404(TicketCategory, 
            id=category_id,
            event=event,
            available_tickets__gt=0
        )
        
        # Calculate amount in cents
        amount = int(category.price * quantity * 100)
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='kes',  # Kenyan Shilling
            metadata={
                'event_id': event.id,
                'category_id': category.id,
                'quantity': quantity,
                'buyer_name': request.POST.get('buyer_name'),
                'buyer_email': request.POST.get('buyer_email'),
                'buyer_phone': request.POST.get('buyer_phone', ''),
            }
        )
        
        return JsonResponse({
            'client_secret': intent.client_secret
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)
    
def ticket_confirmation(request, payment_intent):
    try:
        # Retrieve the payment intent from Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent)
        
        # Get or create the ticket
        ticket = get_object_or_404(Ticket, stripe_payment_intent_id=payment_intent)
        
        return render(request, 'events/ticket_confirmation.html', {
            'ticket': ticket,
            'payment': intent
        })
    except Exception as e:
        messages.error(request, 'Error retrieving ticket information.')
        return redirect('dashboard')