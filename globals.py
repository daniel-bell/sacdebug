# SaC array descriptor variables (shape, size etc)
# If the variable referenced exists and is a pointer
# then these are ignored
sac_array_exclude = {"__sz", "__dim", "__desc", "__shp"}

# Map of SaC types to their overloaded function identifiers
# User defined types are mapped to SACt__NAMESPACE__typename
sac_types = {"int": "i", "float": "f", "double": "d", "bool": "b"}

debugging = True
