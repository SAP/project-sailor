"""Scope configuration for remote OAuth services."""

#
# Format:
#
# SCOPE_CONFIG = {
#     'service_name_1': ['short_scope_name_1_1', 'short_scope_name_1_2', ...],
#     'service_name_2': ['short_scope_name_2_1', 'short_scope_name_2_2', ...],
#     'service_name_3': ['short_scope_name_3_1', 'short_scope_name_3_2', ...],
#     ...
# }
#
SCOPE_CONFIG = {
    'sap_iot': ['t1.am.ts.r', 't1.am.ts.cud', 't1.r', 't1.am.map.r', 't1.export.r']
}
