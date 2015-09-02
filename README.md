# enroll.py
  The purpose of this script is to enroll nodes to ironic. This get the details
from ilo and register the node in ironic.

This will add following properties in ironic.

  number of cpus: Number of cpus in the machine
  Memory: RAM size
  Server serial: Server serial number
  CPU Architecture: This has been determined from the config file, the config
file contain sections for each server model and have a mapping to right cpu
architecture and hardware type.
  Hardware type: Same as above (CPU Architecture)


Here is the sample config file.
```
$ cat /etc/jiocloud/enroll_nodes.ini
[ProLiant SL210t Gen8]
architecture=x86_64.g1.compute
hw_type=g1.compute

[ProLiant SL210t Gen81]
yet=another
architecture=test

[ProLiant SL4540 Gen8]
architecture=x86_64.g1.storage
hw_type=g1.storage
```
