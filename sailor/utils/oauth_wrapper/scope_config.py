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
    'sap_iot': ['.am.ts.r', '.am.ts.cud', '.r', '.am.map.r', '.export.r']
}
