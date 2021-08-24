# QA Tools
Quality assurance dags that runs periodically.

### Explorer products count alignment
Use case: Having inaccurate explorer product dataset count displayed is misleading, this dag runs weekly to ensure counts are correct.

Scope: SQL count, then force explorer to update if out of sync.
