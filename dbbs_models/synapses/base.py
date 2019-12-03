import glia as g

class Synapse:

    def __init__(self, cell, section, point_process_name, variant=None, attributes = {}):
        self._cell = cell
        self._section = section
        self._point_process_name = point_process_name
        self._point_process_glia_name = g.resolve_process(point_process_name, pkg="dbbs_mod_collection", variant=variant)
        self._point_process = g.process(section, point_process_name, pkg="dbbs_mod_collection", variant=variant)
        for key, value in attributes.items():
            setattr(self._point_process, key, value)
