from .base import NeuronModel

class GolgiCell(NeuronModel):
    morphologies = ['stellate.ASC']

    synapse_types = {
        "AMPA": {
            "point_process": ('AMPA', 'golgi_cell_deterministic'),
        }
    }

    section_types = {
        "soma": {
            "mechanisms": ['Leak','Nav1_1','Cav3_2','Cav3_3','Kir2_3','Kv1_1','Kv3_4','Kv4_3','Kca1_1','Kca2_2','Cav2_1','HCN1','cdp5StCmod'],
            "attributes": {
              "Ra": 110,
              "cm": 1 ,
              "gmax_Leak": 0.000008 ,
              "e_Leak": -48  ,
              "gbar_Nav1_1": 0.8 ,
              "ena": 60  ,
              "gcabar_Cav3_2": 0.00163912063769  ,
              "pcabar_Cav3_3": 0.00001615552993  ,
              "gkbar_Kir2_3": 0.00001093425575 ,
              "ek": -84,
              "gbar_Kv1_1": 0.00107430134923,
              "gkbar_Kv3_4": 0.008,
              "gkbar_Kv4_3": 0.00404228168138,
              "gbar_Kca1_1": 0.00518036298671,
              "gkbar_Kca2_2": 0.00054166094878,
              "pcabar_Cav2_1": 0.00038,
              "gbar_HCN1": 0.00058451678362,
              "eh": -34 ,
            }
        },
        "dendrites": {
            "mechanisms": [], "attributes": {}
        },
        "basal_dendrites": {
            "synapses": ['AMPA'],
            "mechanisms": ['Leak','Nav1_6','Kv1_1','Kca1_1','Kca2_2','Cav2_2','cdp5'],
            "attributes": {
                "Ra": 122, "cm": 3, "ena": 60, "ek": -80, "eca": 137,
                ("e", "Leak"): -59,
                ("gmax", "Leak"): 0.00003,
                ("gbar", "Nav1_6"): 0.00596389701963,
                ("gbar", "Kv1_1"): 0.00300075070483,
                ("gbar", "Kca1_1"): 0.01992292703235,
                ("gkbar", "Kca2_2"): 0.01067448459892,
                ("gcanbar", "Cav2_2"): 0.00098761689603,
                ("TotalPump", "cdp5"): 0.7e-9,
            }
        },
        "apical_dendrites": {
            "synapses": ['AMPA'],
            "mechanisms": ['Leak', 'Nav1_6', 'Kv1_1', 'Kca1_1', 'Kca2_2', 'Cav2_3', 'Cav3_1', 'cdp5'],
            "attributes":  {
                "Ra": 122, "cm": 3, "ena": 60, "ek": -80, "eca": 137,
                ("e", "Leak"): -59,
                ("gmax", "Leak"): 0.00003,
                ("gbar", "Nav1_6"): 0.0032004946448,
                ("gbar", "Kv1_1"): 0.00366791747215,
                ("gbar", "Kca1_1"): 0.0207352478961,
                ("gkbar", "Kca2_2"): 0.00597385039361,
                ("gcabar", "Cav2_3"): 7.181872437E-05,
                ("pcabar", "Cav3_1"): 7.03521203E-06,
                ("TotalPump", "cdp5"): 2e-9,
            }
        },
        "axon": {
            "mechanisms": ['Leak', 'Kv1_1', 'Nav1_6', 'Kv3_4', 'cdp5'],
            "attributes": {
                "Ra": 122, "cm": 1, "ena": 60, "ek": -80, "eca": 137,
                ("e", "Leak"): -59,
                ("gmax", "Leak"): 0.00001,
                ("gbar", "Kv1_1"): 0.004,
                ("gbar", "Nav1_6"): 9.670147548E-05,
                ("gkbar", "Kv3_4"): 0.00633480317392,
                ("TotalPump", "cdp5"): 1e-9,
            }
        },
        "axon_initial_segment": {
            "mechanisms": ['Leak', 'HCN1', 'HCN2', 'Nav1_6', 'Kv3_4', 'Km', 'cdp5'],
            "attributes": {
                "Ra": 122, "cm": 1, "ena": 60, "ek": -80, "eca": 137,
                ("e", "Leak"): -59,
                ("gmax", "Leak"): 0.00003,
                ("gbar", "HCN1"): 0.00020635332351,
                ("gbar", "HCN2"): 0.0002816526031,
                ("gbar", "Nav1_6"): 0.39006484091705,
                ("gkbar", "Kv3_4"): 0.29455503229075,
                ("gkbar", "Km"): 0.00030327654923,
                ("TotalPump", "cdp5"): 1e-9,
            }
        }
    }

    labels = {
        "basal_dendrites": {
            "from": "dendrites",
            "id": lambda id: id >= 0 and id <= 3 or id >= 16 and id <= 17 or id >= 33 and id <= 41 or id == 84 or id >= 105 and id <= 150
        },
        "apical_dendrites": {
            "from": "dendrites",
            "id": lambda id: id >= 4 and id <= 15 or id >= 18 and id <= 32 or id >= 42 and id <= 83 or id >= 85 and id <= 104
        },
        "axon_initial_segment": {
            "from": "axon",
            "id": lambda id: id == 0
        }
    }
