# so we patch the operator with the fixed version of `Resources`
def _set_resources(self, resources):
    if not resources:
        return []
    return [PatchedResources(**resources)