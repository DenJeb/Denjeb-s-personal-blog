from scripts.export_openapi import build_schema


def test_schema_contains_public_paths():
    schema = build_schema()
    assert "/api/v1/posts" in schema["paths"]
    assert "/api/v1/site" in schema["paths"]
