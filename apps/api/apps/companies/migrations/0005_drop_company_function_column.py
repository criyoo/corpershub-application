from django.db import migrations


def drop_company_function_column(apps, schema_editor):
    table_name = "companies_companyprofile"
    column_name = "company_function"

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, table_name)
        }

    if column_name not in existing_columns:
        return

    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(f'ALTER TABLE "{table_name}" DROP COLUMN "{column_name}"')


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0004_companyprofile_accommodation_provided_and_more"),
    ]

    operations = [
        migrations.RunPython(drop_company_function_column, migrations.RunPython.noop),
    ]
