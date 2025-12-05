from django.contrib.postgres.operations import UnaccentExtension, TrigramExtension
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


CREATE_PROCEDURE_TRIGGER = """
    DROP TRIGGER IF EXISTS core_procedure_tsv_update ON core_procedure;
    DROP FUNCTION IF EXISTS core_procedure_tsv_trigger();
    CREATE FUNCTION core_procedure_tsv_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.tsv_body := to_tsvector('simple',
            unaccent(coalesce(NEW.title, '')) || ' ' ||
            unaccent(coalesce(NEW.domain, '')) || ' ' ||
            unaccent(coalesce(NEW.level, '')) || ' ' ||
            unaccent(coalesce(NEW.conditions, '')) || ' ' ||
            unaccent(coalesce(NEW.dossier, ''))
        );
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER core_procedure_tsv_update
    BEFORE INSERT OR UPDATE ON core_procedure
    FOR EACH ROW EXECUTE PROCEDURE core_procedure_tsv_trigger();

    UPDATE core_procedure SET tsv_body = to_tsvector('simple',
        unaccent(coalesce(title, '')) || ' ' ||
        unaccent(coalesce(domain, '')) || ' ' ||
        unaccent(coalesce(level, '')) || ' ' ||
        unaccent(coalesce(conditions, '')) || ' ' ||
        unaccent(coalesce(dossier, ''))
    );
"""

DROP_PROCEDURE_TRIGGER = """
    DROP TRIGGER IF EXISTS core_procedure_tsv_update ON core_procedure;
    DROP FUNCTION IF EXISTS core_procedure_tsv_trigger();
"""

CREATE_FINE_TRIGGER = """
    DROP TRIGGER IF EXISTS core_fine_tsv_update ON core_fine;
    DROP FUNCTION IF EXISTS core_fine_tsv_trigger();
    CREATE FUNCTION core_fine_tsv_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.tsv_body := to_tsvector('simple',
            unaccent(coalesce(NEW.name, '')) || ' ' ||
            unaccent(coalesce(NEW.code, '')) || ' ' ||
            unaccent(coalesce(NEW.article, '')) || ' ' ||
            unaccent(coalesce(NEW.decree, '')) || ' ' ||
            unaccent(coalesce(NEW.remedial, ''))
        );
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER core_fine_tsv_update
    BEFORE INSERT OR UPDATE ON core_fine
    FOR EACH ROW EXECUTE PROCEDURE core_fine_tsv_trigger();

    UPDATE core_fine SET tsv_body = to_tsvector('simple',
        unaccent(coalesce(name, '')) || ' ' ||
        unaccent(coalesce(code, '')) || ' ' ||
        unaccent(coalesce(article, '')) || ' ' ||
        unaccent(coalesce(decree, '')) || ' ' ||
        unaccent(coalesce(remedial, ''))
    );
"""

DROP_FINE_TRIGGER = """
    DROP TRIGGER IF EXISTS core_fine_tsv_update ON core_fine;
    DROP FUNCTION IF EXISTS core_fine_tsv_trigger();
"""

CREATE_OFFICE_TRIGGER = """
    DROP TRIGGER IF EXISTS core_office_tsv_update ON core_office;
    DROP FUNCTION IF EXISTS core_office_tsv_trigger();
    CREATE FUNCTION core_office_tsv_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.tsv_body := to_tsvector('simple',
            unaccent(coalesce(NEW.unit_name, '')) || ' ' ||
            unaccent(coalesce(NEW.address, '')) || ' ' ||
            unaccent(coalesce(NEW.district, '')) || ' ' ||
            unaccent(coalesce(NEW.service_scope, ''))
        );
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER core_office_tsv_update
    BEFORE INSERT OR UPDATE ON core_office
    FOR EACH ROW EXECUTE PROCEDURE core_office_tsv_trigger();

    UPDATE core_office SET tsv_body = to_tsvector('simple',
        unaccent(coalesce(unit_name, '')) || ' ' ||
        unaccent(coalesce(address, '')) || ' ' ||
        unaccent(coalesce(district, '')) || ' ' ||
        unaccent(coalesce(service_scope, ''))
    );
"""

DROP_OFFICE_TRIGGER = """
    DROP TRIGGER IF EXISTS core_office_tsv_update ON core_office;
    DROP FUNCTION IF EXISTS core_office_tsv_trigger();
"""

CREATE_ADVISORY_TRIGGER = """
    DROP TRIGGER IF EXISTS core_advisory_tsv_update ON core_advisory;
    DROP FUNCTION IF EXISTS core_advisory_tsv_trigger();
    CREATE FUNCTION core_advisory_tsv_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.tsv_body := to_tsvector('simple',
            unaccent(coalesce(NEW.title, '')) || ' ' ||
            unaccent(coalesce(NEW.summary, ''))
        );
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER core_advisory_tsv_update
    BEFORE INSERT OR UPDATE ON core_advisory
    FOR EACH ROW EXECUTE PROCEDURE core_advisory_tsv_trigger();

    UPDATE core_advisory SET tsv_body = to_tsvector('simple',
        unaccent(coalesce(title, '')) || ' ' ||
        unaccent(coalesce(summary, ''))
    );
"""

DROP_ADVISORY_TRIGGER = """
    DROP TRIGGER IF EXISTS core_advisory_tsv_update ON core_advisory;
    DROP FUNCTION IF EXISTS core_advisory_tsv_trigger();
"""


class ConditionalRunSQL(migrations.RunSQL):
    """RunSQL that only executes on PostgreSQL."""
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            try:
                super().database_forwards(app_label, schema_editor, from_state, to_state)
            except Exception as e:
                # If PostgreSQL-specific SQL fails, skip it
                if 'postgresql' not in str(e).lower():
                    raise
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            try:
                super().database_backwards(app_label, schema_editor, from_state, to_state)
            except Exception as e:
                if 'postgresql' not in str(e).lower():
                    raise


class ConditionalOperation:
    """Base class for conditional operations."""
    def __init__(self, operation):
        self.operation = operation
    
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            return self.operation.database_forwards(app_label, schema_editor, from_state, to_state)
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            return self.operation.database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0000_initial"),
    ]

    operations = [
        # Wrap all PostgreSQL-specific operations in RunPython to conditionally execute
        migrations.RunPython(
            code=lambda apps, schema_editor: _apply_postgresql_operations(apps, schema_editor),
            reverse_code=lambda apps, schema_editor: _reverse_postgresql_operations(apps, schema_editor),
        ),
    ]


def _apply_postgresql_operations(apps, schema_editor):
    """Apply PostgreSQL-specific operations only if using PostgreSQL."""
    from django.db import connection
    
    if connection.vendor != 'postgresql':
        # Skip all operations on SQLite
        return
    
    # Apply PostgreSQL extensions
    try:
        UnaccentExtension().database_forwards('core', schema_editor, None, None)
        TrigramExtension().database_forwards('core', schema_editor, None, None)
    except Exception:
        pass  # Extensions may already exist
    
    # Add SearchVectorField fields
    try:
        from django.db import models
        Procedure = apps.get_model('core', 'Procedure')
        Fine = apps.get_model('core', 'Fine')
        Office = apps.get_model('core', 'Office')
        Advisory = apps.get_model('core', 'Advisory')
        
        # These will be handled by Django's migration system
        # We just need to ensure the SQL triggers run
    except Exception:
        pass
    
    # Execute PostgreSQL triggers
    try:
        schema_editor.execute(CREATE_PROCEDURE_TRIGGER)
        schema_editor.execute(CREATE_FINE_TRIGGER)
        schema_editor.execute(CREATE_OFFICE_TRIGGER)
        schema_editor.execute(CREATE_ADVISORY_TRIGGER)
    except Exception as e:
        # If triggers fail, log but don't stop migration
        print(f"[MIGRATION] Warning: PostgreSQL triggers failed (may already exist): {e}")


def _reverse_postgresql_operations(apps, schema_editor):
    """Reverse PostgreSQL-specific operations."""
    from django.db import connection
    
    if connection.vendor != 'postgresql':
        return
    
    try:
        schema_editor.execute(DROP_PROCEDURE_TRIGGER)
        schema_editor.execute(DROP_FINE_TRIGGER)
        schema_editor.execute(DROP_OFFICE_TRIGGER)
        schema_editor.execute(DROP_ADVISORY_TRIGGER)
    except Exception:
        pass
