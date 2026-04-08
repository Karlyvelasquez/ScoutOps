from rag.queries import query_codebase

results = query_codebase("checkout_failure", "users cannot complete payment")
for r in results:
    print(r["plugin_name"], "->", r["file_path"])
