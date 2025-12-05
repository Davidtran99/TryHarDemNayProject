"""
Management command for golden dataset operations.
"""
import json
import csv
import unicodedata
import re
from pathlib import Path
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hue_portal.core.models import GoldenQuery
from hue_portal.core.embeddings import get_embedding_model
from hue_portal.chatbot.analytics import get_golden_dataset_stats


class Command(BaseCommand):
    help = "Manage golden dataset: import, verify, update embeddings, stats"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # Import command
        import_parser = subparsers.add_parser('import', help='Import queries from JSON/CSV file')
        import_parser.add_argument('--file', required=True, help='Path to JSON or CSV file')
        import_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='File format')
        import_parser.add_argument('--verify-by', default='manual', help='Verification source (manual, gpt4, claude)')
        import_parser.add_argument('--skip-embeddings', action='store_true', help='Skip embedding generation')
        
        # Verify command
        verify_parser = subparsers.add_parser('verify', help='Verify a golden query')
        verify_parser.add_argument('--query-id', type=int, help='Golden query ID to verify')
        verify_parser.add_argument('--verify-by', default='manual', help='Verification source')
        verify_parser.add_argument('--accuracy', type=float, default=1.0, help='Accuracy score (0.0-1.0)')
        
        # Update embeddings command
        embeddings_parser = subparsers.add_parser('update_embeddings', help='Update embeddings for all queries')
        embeddings_parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
        embeddings_parser.add_argument('--query-id', type=int, help='Update specific query only')
        
        # Stats command
        subparsers.add_parser('stats', help='Show golden dataset statistics')
        
        # Export command
        export_parser = subparsers.add_parser('export', help='Export golden dataset to JSON')
        export_parser.add_argument('--file', help='Output file path (default: golden_queries.json)')
        export_parser.add_argument('--active-only', action='store_true', help='Export only active queries')
        
        # Delete command
        delete_parser = subparsers.add_parser('delete', help='Delete a golden query')
        delete_parser.add_argument('--query-id', type=int, required=True, help='Golden query ID to delete')
        delete_parser.add_argument('--soft', action='store_true', help='Soft delete (deactivate instead of delete)')

    def handle(self, *args, **options):
        action = options.get('action')
        
        if action == 'import':
            self.handle_import(options)
        elif action == 'verify':
            self.handle_verify(options)
        elif action == 'update_embeddings':
            self.handle_update_embeddings(options)
        elif action == 'stats':
            self.handle_stats(options)
        elif action == 'export':
            self.handle_export(options)
        elif action == 'delete':
            self.handle_delete(options)
        else:
            self.stdout.write(self.style.ERROR('Please specify an action: import, verify, update_embeddings, stats, export, delete'))

    def handle_import(self, options):
        """Import queries from JSON or CSV file."""
        file_path = Path(options['file'])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")
        
        file_format = options.get('format', 'json')
        verify_by = options.get('verify_by', 'manual')
        skip_embeddings = options.get('skip_embeddings', False)
        
        self.stdout.write(f"Importing from {file_path}...")
        
        if file_format == 'json':
            queries = self._load_json(file_path)
        else:
            queries = self._load_csv(file_path)
        
        embedding_model = None if skip_embeddings else get_embedding_model()
        
        imported = 0
        skipped = 0
        
        for query_data in queries:
            try:
                query = query_data['query']
                query_normalized = self._normalize_query(query)
                
                # Check if already exists
                if GoldenQuery.objects.filter(query_normalized=query_normalized, is_active=True).exists():
                    self.stdout.write(self.style.WARNING(f"Skipping duplicate: {query[:50]}..."))
                    skipped += 1
                    continue
                
                # Generate embedding if model available
                query_embedding = None
                if embedding_model:
                    try:
                        embedding = embedding_model.encode(query, convert_to_numpy=True)
                        query_embedding = embedding.tolist()
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to generate embedding: {e}"))
                
                # Create golden query
                GoldenQuery.objects.create(
                    query=query,
                    query_normalized=query_normalized,
                    query_embedding=query_embedding,
                    intent=query_data.get('intent', 'general_query'),
                    response_message=query_data.get('response_message', ''),
                    response_data=query_data.get('response_data', {
                        'message': query_data.get('response_message', ''),
                        'intent': query_data.get('intent', 'general_query'),
                        'results': query_data.get('results', []),
                        'count': len(query_data.get('results', []))
                    }),
                    verified_by=query_data.get('verified_by', verify_by),
                    accuracy_score=query_data.get('accuracy_score', 1.0),
                    is_active=True
                )
                
                imported += 1
                if imported % 10 == 0:
                    self.stdout.write(f"Imported {imported} queries...")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error importing query: {e}"))
                continue
        
        self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported} queries, skipped {skipped} duplicates"))

    def handle_verify(self, options):
        """Verify a golden query."""
        query_id = options.get('query_id')
        if not query_id:
            raise CommandError("--query-id is required")
        
        try:
            golden_query = GoldenQuery.objects.get(id=query_id)
        except GoldenQuery.DoesNotExist:
            raise CommandError(f"Golden query {query_id} not found")
        
        verify_by = options.get('verify_by', 'manual')
        accuracy = options.get('accuracy', 1.0)
        
        golden_query.verified_by = verify_by
        golden_query.accuracy_score = accuracy
        golden_query.is_active = True
        golden_query.save()
        
        self.stdout.write(self.style.SUCCESS(f"Verified query {query_id}: {golden_query.query[:50]}..."))

    def handle_update_embeddings(self, options):
        """Update embeddings for golden queries."""
        batch_size = options.get('batch_size', 10)
        query_id = options.get('query_id')
        
        embedding_model = get_embedding_model()
        if not embedding_model:
            raise CommandError("Embedding model not available. Check EMBEDDING_MODEL configuration.")
        
        if query_id:
            queries = GoldenQuery.objects.filter(id=query_id, is_active=True)
        else:
            queries = GoldenQuery.objects.filter(is_active=True, query_embedding__isnull=True)
        
        total = queries.count()
        self.stdout.write(f"Updating embeddings for {total} queries...")
        
        updated = 0
        for i, golden_query in enumerate(queries, 1):
            try:
                embedding = embedding_model.encode(golden_query.query, convert_to_numpy=True)
                golden_query.query_embedding = embedding.tolist()
                golden_query.save(update_fields=['query_embedding'])
                updated += 1
                
                if i % batch_size == 0:
                    self.stdout.write(f"Updated {updated}/{total}...")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating query {golden_query.id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Updated embeddings for {updated} queries"))

    def handle_stats(self, options):
        """Show golden dataset statistics."""
        stats = get_golden_dataset_stats()
        
        self.stdout.write(self.style.SUCCESS("Golden Dataset Statistics:"))
        self.stdout.write(f"  Total queries: {stats['total_queries']}")
        self.stdout.write(f"  Active queries: {stats['active_queries']}")
        self.stdout.write(f"  Total usage: {stats['total_usage']}")
        self.stdout.write(f"  Average accuracy: {stats['avg_accuracy']:.3f}")
        self.stdout.write(f"  With embeddings: {stats['with_embeddings']}")
        self.stdout.write(f"  Embedding coverage: {stats['embedding_coverage']:.1f}%")
        
        if stats['intent_breakdown']:
            self.stdout.write("\nIntent breakdown:")
            for intent, count in sorted(stats['intent_breakdown'].items(), key=lambda x: -x[1]):
                self.stdout.write(f"  {intent}: {count}")

    def handle_export(self, options):
        """Export golden dataset to JSON."""
        output_file = options.get('file') or 'golden_queries.json'
        active_only = options.get('active_only', False)
        
        queryset = GoldenQuery.objects.all()
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        queries = []
        for gq in queryset:
            queries.append({
                'id': gq.id,
                'query': gq.query,
                'intent': gq.intent,
                'response_message': gq.response_message,
                'response_data': gq.response_data,
                'verified_by': gq.verified_by,
                'accuracy_score': gq.accuracy_score,
                'usage_count': gq.usage_count,
                'is_active': gq.is_active,
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(queries, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(self.style.SUCCESS(f"Exported {len(queries)} queries to {output_file}"))

    def handle_delete(self, options):
        """Delete or deactivate a golden query."""
        query_id = options.get('query_id')
        soft = options.get('soft', False)
        
        try:
            golden_query = GoldenQuery.objects.get(id=query_id)
        except GoldenQuery.DoesNotExist:
            raise CommandError(f"Golden query {query_id} not found")
        
        if soft:
            golden_query.is_active = False
            golden_query.save()
            self.stdout.write(self.style.SUCCESS(f"Deactivated query {query_id}"))
        else:
            query_text = golden_query.query[:50]
            golden_query.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted query {query_id}: {query_text}..."))

    def _load_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load queries from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'queries' in data:
            return data['queries']
        else:
            raise CommandError("JSON file must contain a list of queries or a dict with 'queries' key")

    def _load_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load queries from CSV file."""
        queries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Expected columns: query, intent, response_message, response_data (JSON string)
                query_data = {
                    'query': row.get('query', ''),
                    'intent': row.get('intent', 'general_query'),
                    'response_message': row.get('response_message', ''),
                }
                
                # Parse response_data if present
                if 'response_data' in row and row['response_data']:
                    try:
                        query_data['response_data'] = json.loads(row['response_data'])
                    except json.JSONDecodeError:
                        query_data['response_data'] = {
                            'message': row.get('response_message', ''),
                            'intent': row.get('intent', 'general_query'),
                            'results': [],
                            'count': 0
                        }
                else:
                    query_data['response_data'] = {
                        'message': row.get('response_message', ''),
                        'intent': row.get('intent', 'general_query'),
                        'results': [],
                        'count': 0
                    }
                
                queries.append(query_data)
        
        return queries

    def _normalize_query(self, query: str) -> str:
        """Normalize query for matching."""
        normalized = query.lower().strip()
        normalized = unicodedata.normalize("NFD", normalized)
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

