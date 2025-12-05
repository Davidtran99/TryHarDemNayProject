"""
Management command to populate tsv_body (SearchVector) for LegalSection.
This is required for BM25 search to work.
"""
from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from hue_portal.core.models import LegalSection


class Command(BaseCommand):
    help = "Populate tsv_body (SearchVector) for all LegalSection instances"

    def handle(self, *args, **options):
        self.stdout.write("Populating tsv_body for LegalSection...")
        
        # Update all LegalSection instances with SearchVector
        updated = LegalSection.objects.update(
            tsv_body=SearchVector(
                'section_title',
                weight='A',
                config='simple'
            ) + SearchVector(
                'section_code',
                weight='A',
                config='simple'
            ) + SearchVector(
                'content',
                weight='B',
                config='simple'
            ) + SearchVector(
                'excerpt',
                weight='C',
                config='simple'
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully populated tsv_body for {updated} LegalSection instances"
            )
        )

