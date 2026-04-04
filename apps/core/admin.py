from django.contrib import admin
from .models import ContactMessage, BlogPost


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_name', 'get_category_display', 'published_at', 'created_at')
    list_filter = ('category', 'published_at', 'created_at')
    search_fields = ('title', 'content', 'author_name')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content')
        }),
        ('Publishing', {
            'fields': ('category', 'author_name', 'published_at'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('cover_image',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
