from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import views_subscription

urlpatterns = [
    path('', views.home, name='home'),
    path('events/', views.event_list, name='event_list'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('checkout/<int:pk>/', views.checkout, name='checkout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('ticket/<int:ticket_id>/', views.ticket_confirmation, name='ticket_confirmation'),
    
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create-event/', views.create_event, name='create_event'),
    path('edit-event/<int:pk>/', views.edit_event, name='edit_event'),
    path('events/<int:pk>/delete/', views.delete_event, name='delete_event'),

    path('subscribe/<str:plan>/', views_subscription.subscribe, name='subscribe'),
    path('subscription/success/', views_subscription.subscription_success, name='subscription_success'),
    path('subscription/cancel/', views_subscription.subscription_cancel, name='subscription_cancel'),
    path('pro-features/', views_subscription.pro_features, name='pro_features'),
    path('subscription/settings/', views_subscription.subscription_settings, name='subscription_settings'),
]
