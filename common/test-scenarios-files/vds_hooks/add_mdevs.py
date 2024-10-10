#!/usr/bin/python3
#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

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
                    "name" : "GRID M10-2B",
                    "available_instances" : 2,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-12" : {
                    "name" : "GRID M10-2C",
                    "available_instances" : 0,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-13" : {
                    "name" : "GRID M10-4B",
                    "available_instances" : 3,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-14" : {
                    "name" : "GRID M10-5C",
                    "available_instances" : 16,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=16"
                },
		"nvidia-21" : {
                    "name" : "GRID C10-2B",
                    "available_instances" : 16,
                    "description" : "num_heads=2, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=16"
                },
		"nvidia-22" : {
                    "name" : "GRID C13-2B",
                    "available_instances" : 2,
                    "description" : "num_heads=1, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                },
		"nvidia-259" : {
                    "name" : "GRID M10-5O",
                    "available_instances" : 1,
                    "description" : "num_heads=4, frl_config=45, framebuffer=2048M, max_resolution=4096x2160, max_instance=4"
                }
            }
        }
    }
    return params

caps = hooking.read_json()
caps['pci_0000_03_00']=createParams()
hooking.write_json(caps)
