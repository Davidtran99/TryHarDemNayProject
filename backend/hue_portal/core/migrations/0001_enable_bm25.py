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


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0000_initial"),
    ]

    operations = [
        UnaccentExtension(),
        TrigramExtension(),
        migrations.AddField(
            model_name="procedure",
            name="tsv_body",
            field=SearchVectorField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="fine",
            name="tsv_body",
            field=SearchVectorField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="office",
            name="tsv_body",
            field=SearchVectorField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="advisory",
            name="tsv_body",
            field=SearchVectorField(null=True, editable=False),
        ),
        migrations.AddIndex(
            model_name="procedure",
            index=GinIndex(fields=["tsv_body"], name="procedure_tsv_idx"),
        ),
        migrations.AddIndex(
            model_name="fine",
            index=GinIndex(fields=["tsv_body"], name="fine_tsv_idx"),
        ),
        migrations.AddIndex(
            model_name="office",
            index=GinIndex(fields=["tsv_body"], name="office_tsv_idx"),
        ),
        migrations.AddIndex(
            model_name="advisory",
            index=GinIndex(fields=["tsv_body"], name="advisory_tsv_idx"),
        ),
        migrations.RunSQL(sql=CREATE_PROCEDURE_TRIGGER, reverse_sql=DROP_PROCEDURE_TRIGGER),
        migrations.RunSQL(sql=CREATE_FINE_TRIGGER, reverse_sql=DROP_FINE_TRIGGER),
        migrations.RunSQL(sql=CREATE_OFFICE_TRIGGER, reverse_sql=DROP_OFFICE_TRIGGER),
        migrations.RunSQL(sql=CREATE_ADVISORY_TRIGGER, reverse_sql=DROP_ADVISORY_TRIGGER),
    ]
