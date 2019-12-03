import os, sys
from contextlib import contextmanager
from neuron import h
from .exceptions import *
from ..synapses import Synapse
import numpy as np
import glia as g
h.load_file('stdlib.hoc')
h.load_file('import3d.hoc')

def is_sequence(obj):
    t = type(obj)
    return hasattr(t, '__len__') and hasattr(t, '__getitem__')

class Section:

    def __init__(self, section):
        self.__dict__["neuron_section"] = section

    def __getattr__(self, attr):
        return getattr(self.neuron_section, attr)

    def __setattr__(self, attr, value):
        try:
            setattr(self.neuron_section, attr, value)
        except AttributeError as _:
            self.__dict__[attr] = value

    def __call__(self):
        return self.neuron_section

    @classmethod
    def create(cls, *args, **kwargs):
        s = h.Section(*args, **kwargs)
        return cls(s)

    def set_dimensions(self, length, diameter):
        self.L = length
        self.diam = diameter

    def set_segments(self, segments):
        self.nseg = segments

    def add_3d(self, points, diameters=None):
        points = np.array(points)
        if diameters is None:
            diameters = [self.diam for _ in range(points.shape[0])]
        if not is_sequence(diameters):
            diameters = [diameter for _ in range(points.shape[0])]
        self.neuron_section.push()
        for point, diameter in zip(points, diameters):
            h.pt3dadd(*point, diameter)
        h.pop_section()

    def connect(self, target, *args, **kwargs):
        if isinstance(target, Section):
            target = target()
        self().connect(target, *args, **kwargs)

class Builder:
    def __init__(self, builder):
        self.builder = builder

    def instantiate(self, model, *args, **kwargs):
        self.builder(model, *args, **kwargs)


class NeuronModel:

    def __init__(self, position=None, morphology_id=0):
        # Check if morphologies were specified
        if not hasattr(self.__class__, "morphologies") or len(self.__class__.morphologies) == 0:
            raise ModelClassError("All NeuronModel classes should specify a non-empty array of morphologies")
        # Import the morphologies if they haven't been imported yet
        if not hasattr(self.__class__, "imported_morphologies"):
            self.__class__._import_morphologies()

        # Initialize variables
        self.position = np.array(position if not position is None else [0., 0., 0.])

        morphology_loader = self.__class__.imported_morphologies[morphology_id]
        # Use the Import3D/Builder to instantiate this cell.
        morphology_loader.instantiate(self)

        # Wrap the neuron sections in our own Section, if not done by the Builder
        self.soma = list(map(lambda s: s if isinstance(s, Section) else Section(s), self.soma))
        self.dend = list(map(lambda s: s if isinstance(s, Section) else Section(s), self.dend))
        self.axon = list(map(lambda s: s if isinstance(s, Section) else Section(s), self.axon))
        self.sections = self.soma + self.dend + self.axon
        self.dendrites = self.dend

        # Do labelling of sections into special sections
        self._apply_labels()

        # Initialize the labelled sections
        for section in self.sections:
            self._init_section(section)

        # Call boot method so that child classes can easily do stuff after init.
        self.boot()

    @classmethod
    def _import_morphologies(cls):
        cls.imported_morphologies = []
        for morphology in cls.morphologies:
            if callable(morphology):
                # If a function is given as morphology, treat it as a builder function
                cls.imported_morphologies.append(Builder(morphology))
            elif isinstance(morphology, staticmethod):
                # If a static method is given as morphology, treat it as a builder function
                cls.imported_morphologies.append(Builder(morphology.__func__))
            else:
                # If a string is given, treat it as a path for Import3d
                file = os.path.join(os.path.dirname(__file__), "../morphologies", morphology)
                loader = h.Import3d_Neurolucida3()
                with suppress_stdout():
                    loader.input(file)
                imported_morphology = h.Import3d_GUI(loader, 0)
                cls.imported_morphologies.append(imported_morphology)

    def _apply_labels(self):
        self.soma[0].label = "soma"
        for section in self.dendrites:
            if not hasattr(section, "label"):
                section.label = "dendrites"
        for section in self.axon:
            if not hasattr(section, "label"):
                section.label = "axon"
        # Apply special labels
        if hasattr(self.__class__, "labels"):
            for label, category in self.__class__.labels.items():
                targets = self.__dict__[category["from"]]
                for id, target in enumerate(targets):
                    if category["id"](id):
                        target.label = label

    def _init_section(self, section):
        section.nseg = 1 + (2 * int(section.L / 40))
        definition = self.__class__.section_types[section.label]
        for mechanism in definition["mechanisms"]:
            if isinstance(mechanism, tuple):
                mechanism_name = mechanism[0]
                mechanism_variant = mechanism[1]
                g.insert(section, mechanism_name, pkg="dbbs_mod_collection", variant=mechanism_variant)
            else:
                g.insert(section, mechanism, pkg="dbbs_mod_collection")
        for attribute, value in definition["attributes"].items():
            section.neuron_section.__dict__[attribute] = value
        if "synapses" in definition:
            section.synapses = definition["synapses"]

    def boot(self):
        pass

    def set_reference_id(self, id):
        '''
            Add an id that can be used as reference for outside software.
        '''
        self.ref_id = id

    def connect(self, from_cell, from_section, to_section, synapse_type=None):
        '''
            Connect this cell as the postsynaptic cell in a connection with
            `from_cell` between the `from_section` and `to_section`.
            Additionally a `synapse_type` can be specified if there's multiple
            synapse types present on the postsynaptic section.

            :param from_cell: The presynaptic cell.
            :type from_cell: :class:`.NeuronModel`
            :param from_section: The presynaptic section.
            :type from_section: :class:`.Section`
            :param to_section: The postsynaptic section.
            :type to_section: :class:`.Section`
            :param synapse_type: The name of the synapse type.
            :type synapse_type: string
        '''
        label = to_section.label
        if not hasattr(self.__class__, "synapse_types"):
            raise ModelClassError("Can't connect to a NeuronModel that does not specify any `synapse_types` on its class.")
        synapse_types = self.__class__.synapse_types
        if not hasattr(to_section, "synapses") or not to_section.synapses:
            raise ConnectionError("Can't connect to a section without synapses.")
        section_synapses = to_section.synapses

        if synapse_type is None:
            if len(section_synapses) != 1:
                raise AmbiguousSynapseError("Too many possible synapse types: " + ", ".join(section_synapses) + ". Specify a `synapse_type` for the connection.")
            else:
                synapse_definition = synapse_types[section_synapses[0]]
        else:
            if not synapse_type in section_synapses:
                raise SynapseNotPresentError("The synapse type '{}' is not present on '{}'".format(synapse_type, to_section.label))
            elif not synapse_type in synapse_types:
                raise SynapseNotDefinedError("The synapse type '{}' is used on '{}' but not defined in the model.".format(synapse_type, to_section.label))
            else:
                synapse_definition = synapse_types[synapse_type]

        synapse_attributes = synapse_definition["attributes"] if "attributes" in synapse_definition else {}
        synapse_point_process = synapse_definition["point_process"]
        synapse = Synapse(self, to_section, synapse_point_process, synapse_attributes)
        return synapse


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
