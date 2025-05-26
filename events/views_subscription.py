from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

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
def subscribe(request, plan):
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
    context = {
        'billing_history': [
            
        ]
    }
    if request.user.subscription:
        # Fetch recent invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=request.user.subscription.stripe_customer_id,
            limit=5
        )
        context['billing_history'] = invoices.data

    return render(request, 'subscription/settings.html', context)