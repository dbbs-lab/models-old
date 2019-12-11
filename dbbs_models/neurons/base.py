import os, sys
from contextlib import contextmanager
from patch import p
from patch.objects import Section
from .exceptions import *
from ..synapses import Synapse
import numpy as np
import glia as g
p.load_file('stdlib.hoc')
p.load_file('import3d.hoc')

def is_sequence(obj):
    t = type(obj)
    return hasattr(t, '__len__') and hasattr(t, '__getitem__')

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
        self.soma = list(map(lambda s: s if isinstance(s, Section) else Section(p, s), self.soma))
        self.dend = list(map(lambda s: s if isinstance(s, Section) else Section(p, s), self.dend))
        self.axon = list(map(lambda s: s if isinstance(s, Section) else Section(p, s), self.axon))
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
                loader = p.Import3d_Neurolucida3()
                with suppress_stdout():
                    loader.input(file)
                imported_morphology = p.Import3d_GUI(loader, 0)
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
        section.cell = self
        # Set the amount of sections to some standard odd amount
        section.nseg = 1 + (2 * int(section.L / 40))
        definition = self.__class__.section_types[section.label]
        self._resolved_mechanisms = {}
        # Insert the mechanisms
        for mechanism in definition["mechanisms"]:
            # Use Glia to resolve the mechanism selection.
            if isinstance(mechanism, tuple):
                # Mechanism defined as: `(mech_name, mech_variant)`
                mechanism_variant = mechanism[1]
                mechanism = mechanism[0]
                mod_name = g.resolve(mechanism, pkg="dbbs_mod_collection", variant=mechanism_variant)
            else:
                # Mechanism defined as string
                mod_name = g.resolve(mechanism, pkg="dbbs_mod_collection")
            # Store a map of mechanisms to full mod_names for the attribute setter
            self._resolved_mechanisms[mechanism] = mod_name
            # Use Glia to insert the resolved mod.
            g.insert(section, mod_name)

        # Set the attributes on this section and its mechanisms
        for attribute, value in definition["attributes"].items():
            if isinstance(attribute, tuple):
                # `attribute` is an attribute of a specific mechanism and defined
                # as `(attribute, mechanism)`. This makes use of the fact that
                # NEURON provides shorthands to a mechanism's attribute as
                # `attribute_mechanism` instead of having to iterate over all
                # the segments and setting `mechanism.attribute` for each
                mechanism = attribute[1]
                if not mechanism in self._resolved_mechanisms:
                    raise MechanismAttributeError("The attribute " + repr(attribute) + " specifies a mechanism '{}' that was not inserted in this section.".format(mechanism))
                mechanism_mod = self._resolved_mechanisms[mechanism]
                attribute_name = attribute[0] + "_" + mechanism_mod
            else:
                # `attribute` is an attribute of the section and is defined as string
                attribute_name = attribute
            # Use setattr to set the obtained attribute information. __dict__
            # does not work as NEURON's Python interface is incomplete.
            setattr(section.__neuron__(), attribute_name, value)

        # Copy the synapse definitions to this section
        if "synapses" in definition:
            section.available_synapse_types = definition["synapses"].copy()

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
        if not hasattr(to_section, "available_synapse_types") or not to_section.available_synapse_types:
            raise ConnectionError("Can't connect to '{}' section without available synapse types.".format(to_section.label))
        section_synapses = to_section.available_synapse_types

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
        synapse_variant = None
        if isinstance(synapse_point_process, tuple):
            synapse_variant = synapse_point_process[1]
            synapse_point_process = synapse_point_process[0]
        synapse = Synapse(self, to_section, synapse_point_process, synapse_attributes, variant=synapse_variant)
        to_section.synapses.append(synapse)
        # # TODO: THE FROM CELL'S OUTPUT CONNECTED TO THIS
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
