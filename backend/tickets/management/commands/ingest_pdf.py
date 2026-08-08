"""
Ingest PDF documents into the RAG index.

    python manage.py ingest_pdf docs/refund-policy.pdf --category billing
    python manage.py ingest_pdf docs/*.pdf
"""
import os

from django.core.management.base import BaseCommand, CommandError

from tickets.models import DocumentChunk, Ticket
from tickets.rag import ingest_pdf

CATEGORIES = [value for value, _ in Ticket.CATEGORY_CHOICES]


class Command(BaseCommand):
    help = "Extract, chunk, embed and index one or more PDFs for KB search."

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='+', help="PDF file paths.")
        parser.add_argument(
            '--category', choices=CATEGORIES,
            help="Tag every chunk with this category for filtered retrieval.")
        parser.add_argument(
            '--name',
            help="Override the stored document name (single file only).")
        parser.add_argument(
            '--clear', action='store_true',
            help="Delete the whole index before ingesting.")

    def handle(self, *args, **options):
        paths = options['paths']
        if options['name'] and len(paths) > 1:
            raise CommandError("--name can only be used with a single PDF.")

        for path in paths:
            if not os.path.isfile(path):
                raise CommandError(f"No such file: {path}")

        if options['clear']:
            deleted, _ = DocumentChunk.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing chunks.")

        total = 0
        for path in paths:
            name = options['name'] or os.path.basename(path)
            self.stdout.write(f"Ingesting {name} ...")
            count = ingest_pdf(path, document_name=name,
                               category=options['category'])
            if not count:
                self.stdout.write(self.style.WARNING(
                    f"  no extractable text in {name} (scanned PDF?)"))
            else:
                self.stdout.write(f"  {count} chunks indexed.")
            total += count

        self.stdout.write(self.style.SUCCESS(f"Done. {total} chunks indexed."))
