#!/usr/bin/python

import hooking

def createParams():
    params = {
        "params" : {
            "capability" : "pci",
            'parent': 'computer',
            'iommu_group': 30,
            "vendor" : 'NVIDIA Corporation',
            "vendor_id" : "0x10de",
            "product" : "GP104GL [Tesla P4]",
            "product_id" : "0x13ba",
            "mdev" : {
                "nvidia-11" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-12" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-13" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-14" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-21" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-22" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-23" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-24" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-25" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-257" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-258" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-259" : {
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                }
            }
        }
    }
    return params

caps = hooking.read_json()
caps['pci_0000_03_00']=createParams()
hooking.write_json(caps)

