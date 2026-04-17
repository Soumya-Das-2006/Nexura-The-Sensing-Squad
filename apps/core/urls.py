# apps/core/urls.py
from django.urls import path
from . import views
from . import translation_views

app_name = 'core'

urlpatterns = [
    path('',              views.HomeView.as_view(),        name='home'),
    path('about/',        views.AboutView.as_view(),       name='about'),
    path('how-it-works/', views.HowItWorksView.as_view(),  name='how_it_works'),
    path('features/',     views.FeaturesView.as_view(),    name='features'),
    path('faq/',          views.FAQView.as_view(),         name='faq'),
    path('blog/',         views.BlogView.as_view(),        name='blog'),
    path('blog/<slug:slug>/', views.BlogPostView.as_view(), name='blog_post'),
    path('contact/',      views.ContactView.as_view(),     name='contact'),
    path('cities/',       views.CitiesView.as_view(),      name='cities'),
    path('privacy/',      views.PrivacyView.as_view(),     name='privacy'),
    path('support/',      views.support_list,              name='support'),
    path('terms/',        views.TermsView.as_view(),       name='terms'),

    # ── Translation API ──────────────────────────────────────────────────────
    path('translate/', translation_views.TranslateView.as_view(), name='translate'),
]