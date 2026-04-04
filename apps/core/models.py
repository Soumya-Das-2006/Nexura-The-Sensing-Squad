from django.db import models
from django.templatetags.static import static
from django.utils import timezone


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f"{self.name} - {self.subject}"


class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('education', 'Education'),
        ('case-study', 'Case Study'),
        ('product', 'Product'),
        ('news', 'News'),
        ('general', 'General'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True, max_length=500)
    cover_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    author_name = models.CharField(max_length=100, default='Nexura Team')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name_plural = 'Blog Posts'

    def __str__(self):
        return self.title

    @property
    def cover_image_url(self):
        # Keep image rendering resilient if the stored file reference is missing/broken.
        if self.cover_image and getattr(self.cover_image, 'name', ''):
            try:
                return self.cover_image.url
            except (ValueError, OSError):
                pass
        return static('img/blog-1.png')

    @property
    def get_category_display(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)


class SupportTicket(models.Model):
    CATEGORY_CHOICES = [
        ('claim_issue', 'Claim Issue'),
        ('payout_delay', 'Payout Delay'),
        ('kyc_problem', 'KYC Problem'),
        ('premium_query', 'Premium Query'),
        ('technical', 'Technical Issue'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    worker = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.pk} {self.subject} ({self.get_status_display()})"
